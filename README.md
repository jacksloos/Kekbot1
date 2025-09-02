# 🐸 Frog BTC/ETH Bot (Fixed Version)

- Posts frog image with BTC & ETH every 30 minutes
- Responds to `/price` instantly in your group
- Now with logging, retries, Binance fallback, and error handling

## Railway Deployment
- Add Variables:
  - `BOT_TOKEN` = your bot token
  - `CHAT_ID` = your group id (negative number for groups)
- Make sure Start Command is:
  ```
  python btc_eth_frog_bot.py
  ```
