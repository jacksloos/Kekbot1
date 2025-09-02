import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import schedule
import time
import telegram
from telegram.ext import Updater, CommandHandler
import os
import threading

# ==== CONFIG ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_IMAGE = "frog.png"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# ================

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing BOT_TOKEN or CHAT_ID environment variables.")

bot = telegram.Bot(token=BOT_TOKEN)

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    response = requests.get(url).json()
    btc = response["bitcoin"]["usd"]
    eth = response["ethereum"]["usd"]
    return btc, eth

def generate_image(btc, eth):
    img = Image.open(BASE_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(FONT_PATH, 70)

    text = f"BTC: ${btc:,.0f}\nETH: ${eth:,.0f}"
    text_w, text_h = draw.textsize(text, font=font)

    x = (img.width - text_w) // 2
    y = img.height // 2

    outline = 4
    for dx in [-outline, outline]:
        for dy in [-outline, outline]:
            draw.text((x+dx, y+dy), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="yellow")

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

def send_update():
    btc, eth = get_prices()
    image = generate_image(btc, eth)
    bot.send_photo(chat_id=CHAT_ID, photo=image)

def job():
    send_update()

def price_command(update, context):
    btc, eth = get_prices()
    image = generate_image(btc, eth)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=image)

def start_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("price", price_command))
    updater.start_polling()
    updater.idle()

def run_schedule():
    schedule.every(30).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_schedule, daemon=True).start()
    start_bot()
