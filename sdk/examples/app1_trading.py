import sys
import os

# Add sdk/python to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from notifier_sdk import Notifier

def main():
    notifier = Notifier(
        endpoint="http://localhost:8000",
        api_key="dev-secret-api-key",
        default_source="app1-trading-bot"
    )

    print("Firing App 1: Trading Alert...")
    res = notifier.trade_alert(
        title="NIFTY Target 1 Hit",
        message="Order #ORD-9821: 25000 CE hit target @ 158.40 (+32 pts). Trail SL to cost.",
        priority="high",
        data={"symbol": "NIFTY25000CE", "pnl": "+3200", "status": "PARTIAL_EXIT"}
    )
    print("Gateway response:", res)

if __name__ == "__main__":
    main()
