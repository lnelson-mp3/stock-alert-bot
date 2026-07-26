# Stock Alert Bot

A Python bot that checks a stock ticker's price against its previous trading-day
close and posts a Discord alert when the move is significant. Price data comes
from [`yfinance`](https://pypi.org/project/yfinance/), so no financial API key
is required. Built to run manually or on a schedule (e.g. every 30 minutes via
GitHub Actions).

## What it does

On every run, the bot:

1. Fetches recent daily price data for the configured ticker (default `AAPL`) with `yfinance`.
2. Takes the most recent closing price as the "current price" and the closing price
   from the trading day before that as the "previous close."
3. Calculates the percentage change (see formula below).
4. If the absolute value of that change is at or above the alert threshold
   (default `2.0`%), it posts a message to a Discord channel via a webhook.
5. Prints a one-line summary (ticker, current price, previous close, percent
   change, whether an alert was sent) to the terminal every time it runs.

Because the price history comes from actual trading days, weekends and market
holidays are handled automatically — the "previous close" is always the last
day the market was actually open, not just "yesterday."

## Percentage change formula

```
percent_change = ((current_price - previous_close) / previous_close) * 100
```

A positive value means the stock is UP; a negative value means it's DOWN. The
bot alerts when `abs(percent_change) >= ALERT_THRESHOLD`.

## Alert format

Alerts use a green up-chart emoji (📈) for upward moves and a red down-chart
emoji (📉) for downward moves:

```
📈 Stock Alert: AAPL is UP 2.35%
Current price: $215.40
Previous close: $210.46
Checked: 2026-07-26 14:32:10 UTC
```

## 1. Install dependencies

Create and activate a virtual environment, then install the requirements:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure your local `.env` file

Copy the example file and fill in your real Discord webhook URL:

```bash
cp .env.example .env
```

Then edit `.env` and set:

```
DISCORD_WEBHOOK_URL=<your real Discord webhook URL>
STOCK_TICKER=AAPL
ALERT_THRESHOLD=2.0
```

`STOCK_TICKER` and `ALERT_THRESHOLD` are optional — if omitted, the bot
defaults to `AAPL` and `2.0`. `.env` is listed in `.gitignore` and must never
be committed.

## 3. Send a test alert

Use `--test-alert` to confirm the Discord webhook is wired up correctly. This
sends a clearly labeled test message and does **not** require the stock to
have actually moved 2%:

```bash
python stock_alert.py --test-alert
```

## 4. Run a normal check

```bash
python stock_alert.py
```

This prints a summary line to the terminal and only posts to Discord if the
price move meets or exceeds the threshold.

## Changing the ticker or threshold

Override the defaults with environment variables, either in `.env` (for local
runs) or as repository secrets/variables (for GitHub Actions):

```bash
STOCK_TICKER=TSLA ALERT_THRESHOLD=3.5 python stock_alert.py
```

## Running on a schedule with GitHub Actions

Store `DISCORD_WEBHOOK_URL` (and optionally `STOCK_TICKER` / `ALERT_THRESHOLD`)
as **repository secrets** (Settings → Secrets and variables → Actions), then
reference them in a workflow step as environment variables, e.g.:

```yaml
env:
  DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

Never put the webhook value directly in the workflow file.

## Why the webhook must never be committed to GitHub

The Discord webhook URL is a bearer credential — anyone who has it can post
messages to your channel (or, on some setups, spam/flood it) with no further
authentication. If it's committed to a public (or even private-but-shared)
repository, it ends up in git history forever, even if you delete it in a
later commit, and it can be scraped by bots that scan GitHub for leaked
secrets within minutes. That's why this project:

- Reads the webhook only from the `DISCORD_WEBHOOK_URL` environment variable,
  never hardcodes it.
- Never prints or logs the webhook value.
- Ships only a placeholder in `.env.example`, with the real `.env` excluded
  via `.gitignore`.
- Expects the real value to live in a local `.env` file or, for automation, in
  GitHub Actions repository secrets.

## Error handling

The bot is designed to fail gracefully and always print a status line rather
than crash silently:

- **Missing/invalid ticker or no data**: prints an error and exits without
  attempting a Discord call.
- **Weekends/market holidays**: handled naturally since only actual trading
  days are considered.
- **Network errors** (fetching prices or posting to Discord): caught and
  reported by exception type only, never with sensitive detail.
- **Missing `DISCORD_WEBHOOK_URL`**: the bot still prints the price check
  result but skips sending to Discord.
- **Invalid `ALERT_THRESHOLD`**: falls back to the default (`2.0`) with a
  warning.
