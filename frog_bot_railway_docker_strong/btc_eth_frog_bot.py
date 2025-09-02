import os
import time
import math
import logging
from io import BytesIO
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw, ImageFont

import telegram
from telegram.error import RetryAfter, TimedOut, NetworkError
from telegram.ext import Updater, CommandHandler
import schedule
import threading

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("frogbot")

# ---------- Config ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # keep as string
BASE_IMAGE = os.path.join(os.path.dirname(__file__), "frog.png")

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("Missing BOT_TOKEN or CHAT_ID env vars. Set them in Railway → Variables.")

bot = telegram.Bot(token=BOT_TOKEN)

def load_font(size=70):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

FONT = load_font(70)

import requests
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "frog-bot/1.0"})
DEFAULT_TIMEOUT = 10

def http_get_json(url):
    for attempt in range(3):
        try:
            r = SESSION.get(url, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "3"))
                time.sleep(wait); continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}")

def get_prices():
    try:
        j = http_get_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd")
        return float(j["bitcoin"]["usd"]), float(j["ethereum"]["usd"]), "CoinGecko"
    except Exception:
        b = http_get_json("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        e = http_get_json("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT")
        return float(b["price"]), float(e["price"]), "Binance"

def fmt(n):
    return f"${n:,.0f}" if n >= 1000 else f"${n:,.2f}"

def generate_image(btc, eth):
    if not os.path.exists(BASE_IMAGE):
        raise FileNotFoundError("frog.png not found")
    img = Image.open(BASE_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(img)
    text = f"BTC: {fmt(btc)}\nETH: {fmt(eth)}"
    try:
        bbox = draw.multiline_textbbox((0,0), text, font=FONT, align="center", spacing=10)
        w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
    except Exception:
        w, h = draw.textsize(text, font=FONT)
    x = (img.width - w)//2; y = img.height//2
    for dx in (-4,4):
        for dy in (-4,4):
            draw.multiline_text((x+dx, y+dy), text, font=FONT, fill="black", align="center", spacing=10)
    draw.multiline_text((x, y), text, font=FONT, fill="yellow", align="center", spacing=10)
    out = BytesIO(); img.save(out, format="PNG"); out.seek(0)
    return out

def send_update():
    try:
        btc, eth, src = get_prices()
        image = generate_image(btc, eth)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        bot.send_photo(chat_id=CHAT_ID, photo=image, filename="frog.png", caption=f"BTC/ETH • {src} • {ts}")
        log.info("Sent update")
    except RetryAfter as e:
        time.sleep(getattr(e, "retry_after", 5))
    except (TimedOut, NetworkError) as e:
        log.warning("Telegram network issue: %s", e)
    except Exception as e:
        log.exception("send_update failed: %s", e)

def schedule_loop():
    log.info("Initial send…"); send_update()
    schedule.every(30).minutes.do(send_update)
    while True:
        try:
            schedule.run_pending(); time.sleep(1)
        except Exception as e:
            log.exception("Scheduler error: %s", e); time.sleep(3)

def cmd_price(update, context):
    try:
        btc, eth, src = get_prices()
        image = generate_image(btc, eth)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=image, filename="frog.png", caption=f"BTC/ETH • {src} • {ts}")
    except Exception as e:
        log.exception("/price failed: %s", e)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Error fetching prices.")

def start_polling():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("price", cmd_price))
    updater.start_polling(clean=True, timeout=30, read_latency=10)
    updater.idle()

if __name__ == "__main__":
    log.info("Frog bot starting…")
    threading.Thread(target=schedule_loop, daemon=True).start()
    start_polling()
