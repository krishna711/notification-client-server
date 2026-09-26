export type NotificationPriority = 'low' | 'normal' | 'high' | 'critical';

export interface NotificationParams {
  title: string;
  message: string;
  priority?: NotificationPriority;
  category?: string;
  targetDevice?: string;
  source?: string;
  data?: Record<string, any>;
}

export interface NotificationResponse {
  success: boolean;
  notification_id: string;
  status: string;
  created_at: string;
  target_device: string;
}

export interface NotifierOptions {
  endpoint?: string;
  apiKey?: string;
  defaultSource?: string;
  timeout?: number;
}

export class Notifier {
  constructor(options?: NotifierOptions);
  send(params: NotificationParams): Promise<NotificationResponse>;
  tradeAlert(title: string, message: string, priority?: NotificationPriority, data?: Record<string, any>): Promise<NotificationResponse>;
  serverAlert(title: string, message: string, priority?: NotificationPriority, data?: Record<string, any>): Promise<NotificationResponse>;
  info(title: string, message: string, data?: Record<string, any>): Promise<NotificationResponse>;
}
