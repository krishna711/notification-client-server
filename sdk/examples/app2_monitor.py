import sys
import os

# Add sdk/python to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from notifier_sdk import Notifier

def main():
    notifier = Notifier(
        endpoint="http://localhost:8000",
        api_key="dev-secret-api-key",
        default_source="app2-server-monitor"
    )

    print("Firing App 2: Critical Server Alert...")
    res = notifier.server_alert(
        title="Server Disk Usage Warning",
        message="Primary SSD /dev/nvme0n1p1 at 91% capacity (5.2 GB remaining).",
        priority="critical",
        data={"host": "prod-vps-01", "disk": "/dev/nvme0n1p1", "usage_pct": 91}
    )
    print("Gateway response:", res)

if __name__ == "__main__":
    main()
