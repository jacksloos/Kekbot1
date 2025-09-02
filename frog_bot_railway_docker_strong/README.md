# Frog Bot — Railway (Docker, reliable)

This package uses a Dockerfile so Railway doesn't have to guess the runtime.

## Deploy (GitHub → Railway)
1) Create a GitHub repo and upload all these files.
2) In Railway: New Project → Deploy from GitHub → select your repo.
3) Variables tab:
   - BOT_TOKEN = your token
   - CHAT_ID = -123456789 (your group id)
4) Deploy. Logs should show the bot starting.

No Start Command needed — Dockerfile defines it.
