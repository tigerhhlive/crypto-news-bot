from flask import Flask
import threading
import time
import logging
import requests
import telegram
from datetime import datetime
from config import TELEGRAM_TOKEN, CHAT_ID, NEWS_API_KEY, SENSITIVE_KEYWORDS, TRUSTED_SOURCES

# راه‌اندازی Flask برای باز کردن پورت جهت Render
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Crypto News Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# -----------------------------
# تنظیمات اصلی ربات
# -----------------------------

logging.basicConfig(level=logging.INFO)

MAX_MESSAGES_PER_SYMBOL = 2  # حداکثر تعداد پیام برای هر ارز در هر نوبت

crypto_symbols = [
    'Bitcoin', 'Ethereum', 'Dogecoin', 'XRP', 'Litecoin',
    'Cardano', 'Solana', 'Polkadot', 'BinanceCoin', 'Shiba Inu',
    'Avalanche', 'Polygon', 'Chainlink', 'Uniswap', 'Terra',
    'Ethereum Classic', 'VeChain', 'Stellar', 'Aptos', 'Arbitrum'
]

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"❌ Telegram Error: {e}")
        time.sleep(10)

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
    important_news = []

    for article in articles:
        title = article.get('title', '')
        desc = article.get('description', '')
        url = article.get('url', '')
        source = article.get('source', {}).get('name', '')

        # فیلتر منبع غیر معتبر
        if not any(trusted in source for trusted in TRUSTED_SOURCES):
            continue

        # حذف تیترهای سوالی یا شایعه‌دار
        if '?' in title or any(word in title.lower() for word in ['might', 'could', 'may']):
            continue

        # بررسی وجود حداقل ۲ کلمه حساس
        combined = f"{title} {desc}".lower()
        match_keywords = [kw for kw in SENSITIVE_KEYWORDS if kw in combined]
        if len(match_keywords) >= 2:
            important_news.append((title, desc, url))

        if len(important_news) >= MAX_MESSAGES_PER_SYMBOL:
            break

    if important_news:
        message = f"🚨 *High-Priority News on {symbol}*\n\n"
        for i, (title, desc, url) in enumerate(important_news, 1):
            message += f"*{i}. {title}*\n{desc}\n🔗 {url}\n\n"
        send_telegram_message(message)
        logging.info(f"📨 {len(important_news)} trusted alerts sent for {symbol}")
        time.sleep(2)

def monitor():
    while True:
        now = datetime.now()
        hour = now.hour
        if 8 <= hour < 24:  # فقط از 8 صبح تا 12 شب فعال
            for symbol in crypto_symbols:
                logging.info(f"🔍 Checking news for {symbol}")
                articles = get_crypto_news(symbol)
                if articles:
                    analyze_news_and_send(articles, symbol)
                time.sleep(3)  # فاصله بین ارزها برای حفظ سهمیه
        else:
            logging.info("😴 Sleeping... no news checking right now.")
        time.sleep(60 * 15)  # بررسی هر 15 دقیقه

monitor_thread = threading.Thread(target=monitor)
monitor_thread.start()
