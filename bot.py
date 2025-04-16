from flask import Flask
import threading
import time
import logging
import requests
import telegram
from datetime import datetime
from config import TELEGRAM_TOKEN, CHAT_ID, NEWS_API_KEY, SENSITIVE_KEYWORDS

# فلَسک برای فریب Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto News Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# -----------------------------
# کد ربات اصلی
# -----------------------------

logging.basicConfig(level=logging.INFO)

crypto_symbols = [
    'Bitcoin', 'Ethereum', 'Dogecoin', 'XRP', 'Litecoin',
    'Cardano', 'Solana', 'Polkadot', 'BinanceCoin', 'Shiba Inu',
    'Avalanche', 'Polygon', 'Chainlink', 'Uniswap', 'Terra',
    'Ethereum Classic', 'VeChain', 'Stellar', 'Aptos', 'Arbitrum'
]

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"❌ Telegram Error: {e}")

def get_crypto_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        return data.get("articles", [])
    except Exception as e:
        logging.error(f"Error fetching news for {symbol}: {e}")
        return []

def analyze_news_and_send(articles, symbol):
    for article in articles:
        title = article.get('title', '')
        desc = article.get('description', '')
        url = article.get('url', '')

        combined = f"{title} {desc}".lower()
        if any(kw in combined for kw in SENSITIVE_KEYWORDS):
            msg = f"🚨 *Important News on {symbol}*\n\n*Title:* {title}\n\n*Description:* {desc}\n\n🔗 {url}"
            send_telegram_message(msg)
            logging.info(f"📨 Alert Sent for {symbol}")

def monitor():
    while True:
        now = datetime.now()
        hour = now.hour
        if 8 <= hour < 24:  # فقط از 8 صبح تا 12 شب
            for symbol in crypto_symbols:
                logging.info(f"🔍 Checking news for {symbol}")
                articles = get_crypto_news(symbol)
                if articles:
                    analyze_news_and_send(articles, symbol)
                time.sleep(3)  # برای حفظ سهمیه API
        else:
            logging.info("😴 Sleeping... no news checking right now.")
        time.sleep(60 * 15)  # هر ۱۵ دقیقه بررسی

monitor_thread = threading.Thread(target=monitor)
monitor_thread.start()
