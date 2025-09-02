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
CHAT_ID = os.getenv("CHAT_ID")  # keep as string; p-t-b can take str
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_IMAGE = os.path.join(SCRIPT_DIR, "frog.png")

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("Missing BOT_TOKEN or CHAT_ID env vars. Set them in Railway → Variables.")

# ---------- Telegram Bot ----------
bot = telegram.Bot(token=BOT_TOKEN)

# ---------- Fonts ----------
def load_font(size=70):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    log.warning("Could not load TTF font; using default bitmap font.")
    return ImageFont.load_default()

FONT = load_font(70)

# ---------- HTTP Helpers ----------
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "frog-bot/1.0 (+https://t.me/)"})

DEFAULT_TIMEOUT = 10

def http_get_json(url, **kwargs):
    for attempt in range(3):
        try:
            resp = SESSION.get(url, timeout=kwargs.get("timeout", DEFAULT_TIMEOUT))
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "3"))
                log.warning("Rate limited (%s). Sleeping %ss…", url, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            wait = 2 ** attempt
            log.warning("HTTP error on %s: %s (retry in %ss)", url, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"Failed to GET {url} after retries")

# ---------- Price Sources ----------
def get_prices_coingecko():
    j = http_get_json(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    )
    btc = float(j["bitcoin"]["usd"])
    eth = float(j["ethereum"]["usd"])
    return btc, eth, "CoinGecko"

def get_prices_binance():
    b = http_get_json("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    e = http_get_json("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT")
    btc = float(b["price"])
    eth = float(e["price"])
    return btc, eth, "Binance"

def get_prices():
    try:
        return get_prices_coingecko()
    except Exception as e:
        log.warning("CoinGecko failed: %s. Falling back to Binance…", e)
    return get_prices_binance()

# ---------- Image ----------
def format_price(n):
    if n >= 1000:
        return f"${n:,.0f}"
    return f"${n:,.2f}"

def generate_image(btc, eth):
    if not os.path.exists(BASE_IMAGE):
        raise FileNotFoundError(f"frog.png not found at: {BASE_IMAGE}")

    img = Image.open(BASE_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    text = f"BTC: {format_price(btc)}\nETH: {format_price(eth)}"
    try:
        bbox = draw.multiline_textbbox((0, 0), text, font=FONT, align="center", spacing=10)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except Exception:
        text_w, text_h = draw.textsize(text, font=FONT)

    x = (img.width - text_w) // 2
    y = img.height // 2

    outline = 4
    for dx in (-outline, outline):
        for dy in (-outline, outline):
            draw.multiline_text((x + dx, y + dy), text, font=FONT, fill="black", align="center", spacing=10)

    draw.multiline_text((x, y), text, font=FONT, fill="yellow", align="center", spacing=10)

    out = BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out

# ---------- Send ----------
def send_update():
    try:
        btc, eth, src = get_prices()
        image = generate_image(btc, eth)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        caption = f"BTC/ETH update • {src} • {ts}"
        bot.send_photo(chat_id=CHAT_ID, photo=image, filename="frog.png", caption=caption)
        log.info("Sent update: BTC=%s ETH=%s via %s", btc, eth, src)
    except RetryAfter as e:
        wait = math.ceil(getattr(e, "retry_after", 5))
        log.warning("Telegram rate limit. Waiting %ss…", wait)
        time.sleep(wait)
    except (TimedOut, NetworkError) as e:
        log.warning("Telegram network issue: %s (retry next run)", e)
    except Exception as e:
        log.exception("send_update failed: %s", e)

# ---------- Scheduler ----------
def schedule_loop():
    log.info("Sending initial update…")
    send_update()

    schedule.every(30).minutes.do(send_update)
    log.info("Scheduler started (every 30 minutes).")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            log.exception("Scheduler loop error: %s", e)
            time.sleep(3)

# ---------- Commands ----------
def cmd_price(update, context):
    try:
        btc, eth, src = get_prices()
        image = generate_image(btc, eth)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        caption = f"BTC/ETH • {src} • {ts}"
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=image, filename="frog.png", caption=caption)
        log.info("/price served to chat %s", update.effective_chat.id)
    except Exception as e:
        log.exception("/price failed: %s", e)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I hit an error fetching prices 🙈")

def start_polling():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("price", cmd_price))
    log.info("Starting Telegram polling…")
    updater.start_polling(clean=True, timeout=30, read_latency=10)
    updater.idle()

# ---------- Main ----------
if __name__ == "__main__":
    log.info("Frog bot starting… (CHAT_ID=%s)", CHAT_ID)
    threading.Thread(target=schedule_loop, daemon=True).start()
    start_polling()
