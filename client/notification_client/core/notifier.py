import sys
import subprocess
import logging
import json
from typing import Optional, Dict, Any
from ..config import config
from ..ui.center_popup import CenterScreenAlert

logger = logging.getLogger("notification_client.notifier")

class DualNotificationEngine:
    def __init__(self):
        self._has_windows_toasts = False
        
        # Check if third-party windows_toasts is installed
        try:
            from windows_toasts import WindowsToaster
            self._toaster = WindowsToaster("Notification Gateway")
            self._has_windows_toasts = True
            logger.info("Using windows-toasts library for toast popups.")
        except Exception:
            self._has_windows_toasts = False
            logger.info("Using native Windows WinRT PowerShell engine for toast popups.")

    def notify(
        self, 
        title: str, 
        message: str, 
        priority: str = "normal", 
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
        override_style: Optional[str] = None
    ):
        """
        Dispatches notification based on configured style:
        - 'center': Focused high-visibility popup centered on screen
        - 'toast':  Windows Action Center toast in bottom-right corner
        - 'both':   Displays both center popup and windows toast
        """
        style = (override_style or config.notification_style).lower()

        # 1. Play Audio Cue
        if config.enable_sound and sys.platform == "win32":
            self._play_audio(priority)

        # 2. Center Screen Alert
        if style in ("center", "both"):
            CenterScreenAlert.show(
                title=title,
                message=message,
                priority=priority,
                source=source,
                data=data,
                duration=config.duration_seconds
            )

        # 3. Windows Action Center Toast (Bottom-Right)
        if style in ("toast", "both"):
            self._dispatch_toast(title, message, priority, source)

    def _play_audio(self, priority: str):
        try:
            import winsound
            if priority == "critical":
                winsound.MessageBeep(winsound.MB_ICONHAND)
            elif priority == "high":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception as e:
            logger.debug(f"Audio playback skipped: {e}")

    def _dispatch_toast(self, title: str, message: str, priority: str, source: str):
        if self._has_windows_toasts:
            try:
                from windows_toasts import Toast
                toast = Toast()
                header = f"[{source.upper()}] {title}" if source else title
                toast.text_fields = [header, message]
                self._toaster.show_toast(toast)
                return
            except Exception as e:
                logger.warning(f"windows-toasts failed: {e}. Falling back to native WinRT.")

        # Fallback: Native PowerShell WinRT Toast
        self._show_powershell_toast(title, message, priority, source)

    def _show_powershell_toast(self, title: str, message: str, priority: str, source: str):
        try:
            header = f"[{source.upper()}] {title}" if source else title
            def xml_esc(s):
                return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
            
            clean_title = xml_esc(header)
            clean_body = xml_esc(message)
            
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $TextNodes = $Template.GetElementsByTagName("text")
            $TextNodes.Item(0).AppendChild($Template.CreateTextNode("{clean_title}")) > $null
            $TextNodes.Item(1).AppendChild($Template.CreateTextNode("{clean_body}")) > $null
            $Notification = [Windows.UI.Notifications.ToastNotification]::new($Template)
            $AppId = 'Notification.Gateway'
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($Notification)
            """
            
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
        except Exception as e:
            logger.error(f"Failed to display PowerShell toast: {e}")

notifier = DualNotificationEngine()
