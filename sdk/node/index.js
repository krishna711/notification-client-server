const https = require('https');
const http = require('http');
const { URL } = require('url');

/**
 * Lightweight, zero-dependency Node.js SDK for sending alerts to the Central Notification Gateway.
 * Compatible with Node.js 16, 18, 20, 22+.
 */
class Notifier {
  /**
   * @param {Object} options
   * @param {string} [options.endpoint] - Gateway URL (e.g. 'https://notify.yotek.net')
   * @param {string} [options.apiKey]   - API Bearer key
   * @param {string} [options.defaultSource] - Default app identifier (e.g. 'trading-service')
   * @param {number} [options.timeout]  - Request timeout in milliseconds (default: 8000)
   */
  constructor(options = {}) {
    this.endpoint = (options.endpoint || process.env.NOTIFIER_SERVER_URL || 'http://localhost:8000').replace(/\/+$/, '');
    this.apiKey = options.apiKey || process.env.NOTIFIER_API_KEY || 'dev-secret-api-key';
    this.defaultSource = options.defaultSource || 'node-app';
    this.timeout = options.timeout || 8000;
  }

  /**
   * Send a notification to the gateway.
   * 
   * @param {Object} params
   * @param {string} params.title - Notification title
   * @param {string} params.message - Main message content
   * @param {'low'|'normal'|'high'|'critical'} [params.priority='normal'] - Priority level
   * @param {string} [params.category='general'] - Classification (trade, server, payment, etc.)
   * @param {string} [params.targetDevice='all'] - Specific device_id or 'all'
   * @param {string} [params.source] - Override source app name
   * @param {Object} [params.data] - Custom metadata key-values
   * @returns {Promise<Object>} Gateway response object
   */
  async send(params) {
    if (!params || !params.title || !params.message) {
      throw new Error('Notifier.send requires both "title" and "message" in parameters.');
    }

    const payload = {
      source: params.source || this.defaultSource,
      title: params.title,
      message: params.message,
      priority: params.priority || 'normal',
      category: params.category || 'general',
      target_device: params.targetDevice || 'all',
      data: params.data || {}
    };

    const urlStr = `${this.endpoint}/api/v1/notify`;

    // 1. Prefer native fetch if available (Node 18+)
    if (typeof fetch === 'function') {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(urlStr, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.apiKey}`,
            'User-Agent': `Mozilla/5.0 (compatible; NotifierSDK-Node/1.1; +${payload.source})`
          },
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        clearTimeout(timer);

        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Notification Gateway returned HTTP ${response.status}: ${errText}`);
        }

        return await response.json();
      } catch (err) {
        if (err.name === 'AbortError') {
          throw new Error(`Notification request timed out after ${this.timeout}ms`);
        }
        throw err;
      }
    }

    // 2. Fallback to native https/http module (Node 14/16)
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(urlStr);
      const isHttps = parsedUrl.protocol === 'https:';
      const client = isHttps ? https : http;

      const postData = JSON.stringify(payload);

      const reqOptions = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
          'User-Agent': `Mozilla/5.0 (compatible; NotifierSDK-Node/1.1; +${payload.source})`,
          'Content-Length': Buffer.byteLength(postData)
        },
        timeout: this.timeout
      };

      const req = client.request(reqOptions, (res) => {
        let rawData = '';
        res.on('data', (chunk) => { rawData += chunk; });
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(JSON.parse(rawData));
            } catch (e) {
              resolve({ raw: rawData });
            }
          } else {
            reject(new Error(`Notification Gateway returned HTTP ${res.statusCode}: ${rawData}`));
          }
        });
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error(`Notification request timed out after ${this.timeout}ms`));
      });

      req.on('error', (err) => {
        reject(new Error(`Failed to connect to Notification Gateway: ${err.message}`));
      });

      req.write(postData);
      req.end();
    });
  }

  /**
   * Convenience shortcut for trading signals / order alerts.
   */
  async tradeAlert(title, message, priority = 'high', data = {}) {
    return this.send({ title, message, priority, category: 'trade', data });
  }

  /**
   * Convenience shortcut for critical infrastructure / server alerts.
   */
  async serverAlert(title, message, priority = 'critical', data = {}) {
    return this.send({ title, message, priority, category: 'server_health', data });
  }

  /**
   * Convenience shortcut for general informational alerts.
   */
  async info(title, message, data = {}) {
    return this.send({ title, message, priority: 'normal', category: 'info', data });
  }
}

module.exports = { Notifier };
