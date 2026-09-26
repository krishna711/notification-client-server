import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from notifier_sdk import Notifier

def main():
    print("=" * 60)
    print("Simulating Multiple Independent Applications Firing Alerts")
    print("=" * 60)

    # App 1: Trading strategy on Server A
    app1 = Notifier(api_key="dev-secret-api-key", default_source="app1-algo-strategy")
    # App 2: Infrastructure monitor on Server B
    app2 = Notifier(api_key="dev-secret-api-key", default_source="app2-infra-monitor")
    # App 3: Webhook / Payment service on Server C
    app3 = Notifier(api_key="dev-secret-api-key", default_source="app3-cashfree-webhook")

    print("\n1. App 1 sending entry signal...")
    r1 = app1.trade_alert("Long Entry Triggered", "BANKNIFTY 54800 PE crossed VWAP with volume surge.", "high")
    print("-> App 1 delivered with ID:", r1.get("notification_id"))
    time.sleep(1)

    print("\n2. App 3 sending payment notification...")
    r3 = app3.send(
        title="Payment Success",
        message="Received INR 4,999 from user #9842 (Order #CF-881273)",
        priority="normal",
        category="payment"
    )
    print("-> App 3 delivered with ID:", r3.get("notification_id"))
    time.sleep(1)

    print("\n3. App 2 sending CPU warning...")
    r2 = app2.server_alert("CPU Spike", "Load average 15.2 exceeds 8.0 threshold on prod-worker-2", "critical")
    print("-> App 2 delivered with ID:", r2.get("notification_id"))

    print("\nAll 3 apps successfully sent alerts to the central gateway!")

if __name__ == "__main__":
    main()
