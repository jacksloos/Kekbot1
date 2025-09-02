# 🐸 Frog BTC/ETH Bot (Railway with runtime.txt)

- Runs 24/7 on Railway
- Posts frog image with BTC & ETH every 30 minutes
- Responds to `/price` instantly
- Robust: retries, logging, Binance fallback, font fallback

## Deploy
1) Upload all files in this folder to your GitHub repo.
2) In Railway → New Project → Deploy from GitHub → select your repo.
3) In Railway → Variables:
   - `BOT_TOKEN` = your BotFather token
   - `CHAT_ID` = your group id (negative for groups, e.g. -123456789)
4) Ensure Start Command is: `python btc_eth_frog_bot.py` (Procfile already included).
5) Redeploy. Check Logs for success.
