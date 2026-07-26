#!/usr/bin/env python3
"""Monitors a stock ticker with yfinance and sends a Discord alert on significant moves."""

import argparse
import os
import sys
from datetime import datetime, timezone

import requests
import yfinance as yf

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_TICKER = "AAPL"
DEFAULT_THRESHOLD = 2.0


def get_config():
    ticker = os.environ.get("STOCK_TICKER", DEFAULT_TICKER).strip().upper() or DEFAULT_TICKER

    threshold_raw = os.environ.get("ALERT_THRESHOLD", str(DEFAULT_THRESHOLD))
    try:
        threshold = float(threshold_raw)
    except ValueError:
        print(f"WARNING: ALERT_THRESHOLD='{threshold_raw}' is not a valid number. Using default {DEFAULT_THRESHOLD}.")
        threshold = DEFAULT_THRESHOLD

    return ticker, threshold


def get_webhook_url():
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable is not set.")
        return None
    return url


def fetch_prices(ticker):
    """Return (current_price, previous_close) for the ticker, or (None, None) on failure."""
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="10d", interval="1d")
    except Exception as exc:
        print(f"ERROR: Failed to fetch data for '{ticker}' ({type(exc).__name__}). Check your network connection and the ticker symbol.")
        return None, None

    if history is None or history.empty:
        print(f"ERROR: No price data returned for ticker '{ticker}'. It may be invalid, delisted, or market data may be temporarily unavailable.")
        return None, None

    closes = history["Close"].dropna()
    if len(closes) < 2:
        print(f"ERROR: Not enough trading-day data for '{ticker}' to compute a change (found {len(closes)} closing price(s), need at least 2).")
        return None, None

    current_price = float(closes.iloc[-1])
    previous_close = float(closes.iloc[-2])
    return current_price, previous_close


def compute_change(current_price, previous_close):
    if previous_close == 0:
        return None
    return ((current_price - previous_close) / previous_close) * 100


def send_discord_message(webhook_url, content):
    try:
        response = requests.post(webhook_url, json={"content": content}, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        print(f"ERROR: Failed to send Discord message ({type(exc).__name__}). Verify the webhook is valid and reachable.")
        return False


def build_alert_message(ticker, current_price, previous_close, pct_change):
    direction = "UP" if pct_change >= 0 else "DOWN"
    emoji = "📈" if pct_change >= 0 else "📉"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"{emoji} Stock Alert: {ticker} is {direction} {abs(pct_change):.2f}%\n"
        f"Current price: ${current_price:.2f}\n"
        f"Previous close: ${previous_close:.2f}\n"
        f"Checked: {timestamp}"
    )


def build_test_message(ticker):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        "🧪 TEST ALERT — Stock Alert Bot\n"
        f"This is a test message for ticker {ticker}. If you can see this, Discord alerts are working correctly.\n"
        f"Checked: {timestamp}"
    )


def main():
    parser = argparse.ArgumentParser(description="Monitor a stock ticker and send a Discord alert on significant price moves.")
    parser.add_argument(
        "--test-alert",
        action="store_true",
        help="Send a clearly labeled test Discord message and exit, without requiring a real 2%% move.",
    )
    args = parser.parse_args()

    ticker, threshold = get_config()
    webhook_url = get_webhook_url()

    if args.test_alert:
        print(f"Running in test-alert mode for ticker '{ticker}'...")
        if webhook_url is None:
            print("Cannot send test alert: DISCORD_WEBHOOK_URL is missing.")
            sys.exit(1)
        message = build_test_message(ticker)
        sent = send_discord_message(webhook_url, message)
        print(f"Test alert sent: {sent}")
        sys.exit(0 if sent else 1)

    current_price, previous_close = fetch_prices(ticker)
    if current_price is None or previous_close is None:
        print(f"Ticker: {ticker} | Current: N/A | Previous close: N/A | Change: N/A | Alert sent: False")
        sys.exit(1)

    pct_change = compute_change(current_price, previous_close)
    if pct_change is None:
        print(f"ERROR: Previous close for '{ticker}' is zero; cannot compute a percentage change.")
        print(
            f"Ticker: {ticker} | Current: ${current_price:.2f} | Previous close: ${previous_close:.2f} | "
            f"Change: N/A | Alert sent: False"
        )
        sys.exit(1)

    alert_sent = False
    if abs(pct_change) >= threshold:
        if webhook_url is None:
            print("Alert threshold met, but DISCORD_WEBHOOK_URL is missing; cannot send Discord alert.")
        else:
            message = build_alert_message(ticker, current_price, previous_close, pct_change)
            alert_sent = send_discord_message(webhook_url, message)

    direction = "UP" if pct_change >= 0 else "DOWN"
    print(
        f"Ticker: {ticker} | Current: ${current_price:.2f} | Previous close: ${previous_close:.2f} | "
        f"Change: {pct_change:+.2f}% ({direction}) | Threshold: {threshold}% | Alert sent: {alert_sent}"
    )


if __name__ == "__main__":
    main()
