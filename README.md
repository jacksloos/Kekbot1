# 🐸 Frog BTC/ETH Price Bot

This Telegram bot posts an updated frog image with **BTC & ETH prices every 30 minutes**  
and responds instantly to `/price` in your group.

## 🚀 Deploy to Railway (GitHub Method)

1. Create a new **GitHub repository** (e.g. `frog-bot`).
2. Upload all files from this folder (`btc_eth_frog_bot.py`, `frog.png`, `requirements.txt`, etc.).
3. Go to [Railway](https://railway.app/) → **New Project** → **Deploy from GitHub** → choose your repo.
4. After deploy, set your environment variables in Railway → Variables tab:
   - `BOT_TOKEN` = your Telegram bot token (from BotFather)
   - `CHAT_ID` = your group chat id (e.g. `-123456789`)
5. Railway will install dependencies and run the bot 24/7.

## ✅ Bot Features
- Posts frog image with BTC + ETH every 30 minutes.
- Responds to `/price` in your group instantly.
