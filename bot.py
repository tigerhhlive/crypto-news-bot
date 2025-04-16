from flask import Flask
import threading
import time
import logging
import requests
import telegram
import json
import os
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import TELEGRAM_TOKEN, CHAT_ID, NEWS_API_KEY, SENSITIVE_KEYWORDS, TRUSTED_SOURCES

# -------------------------
# راه‌اندازی پورت برای Render
# -------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Crypto News Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# -------------------------
# تنظیمات و ابزارها
# -------------------------
logging.basicConfig(level=logging.INFO)
analyzer = SentimentIntensityAnalyzer()
bot = telegram.Bot(token=TELEGRAM_TOKEN)
MAX_MESSAGES_PER_SYMBOL = 2
CACHE_FILE = "news_cache.json"

crypto_symbols = [
    'Bitcoin', 'Ethereum', 'Dogecoin', 'XRP', 'Litecoin',
    'Cardano', 'Solana', 'Polkadot', 'BinanceCoin', 'Shiba Inu',
    'Avalanche', 'Polygon', 'Chainlink', 'Uniswap', 'Terra',
    'Ethereum Classic', 'VeChain', 'Stellar', 'Aptos', 'Arbitrum'
]

# -------------------------
# مدیریت Cache
# -------------------------
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, 'r') as f:
        return set(json.load(f))

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(list(cache), f)

cache = load_cache()

# -------------------------
# ارسال پیام به تلگرام
# -------------------------
def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"❌ Telegram Error: {e}")
        time.sleep(10)

# -------------------------
# دریافت اخبار
# -------------------------
def get_crypto_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        return data.get("articles", [])
    except Exception as e:
        logging.error(f"Error fetching news for {symbol}: {e}")
        return []

# -------------------------
# سیستم امتیازدهی + کش + احساسات
# -------------------------
def analyze_news_and_send(articles, symbol):
    important_news = []

    for article in articles:
        title = article.get('title', '')
        desc = article.get('description', '')
        url = article.get('url', '')
        source = article.get('source', {}).get('name', '')
        content_id = url or title

        # کش: بررسی تکراری بودن
        if content_id in cache:
            continue

        # منبع معتبر؟
        score = 0
        if any(trusted in source for trusted in TRUSTED_SOURCES):
            score += 1

        # حذف تیترهای سوالی/شایعه
        if '?' in title or any(word in title.lower() for word in ['might', 'could', 'may']):
            continue
        else:
            score += 1

        # تعداد کلمات کلیدی حساس
        combined = f"{title} {desc}".lower()
        keyword_hits = [kw for kw in SENSITIVE_KEYWORDS if kw in combined]
        score += len(keyword_hits)

        # تحلیل احساسات
        sentiment = analyzer.polarity_scores(combined)
        if sentiment['compound'] >= 0.5 or sentiment['compound'] <= -0.5:
            score += 2  # احساس قوی مثبت یا منفی

        # تمرکز روی BTC و ETH
        if symbol.lower() in ['bitcoin', 'ethereum']:
            score += 1

        # ارسال اگر امتیاز بالا بود
        if score >= 5:
            important_news.append((title, desc, url, score))
            cache.add(content_id)
            if len(important_news) >= MAX_MESSAGES_PER_SYMBOL:
                break

    if important_news:
        message = f"🚨 *High-Impact News on {symbol}*\n\n"
        for i, (title, desc, url, score) in enumerate(important_news, 1):
            message += f"*{i}. {title}*\n{desc}\n🔗 {url}\n🧠 Score: `{score}`\n\n"
        send_telegram_message(message)
        logging.info(f"📨 {len(important_news)} trusted alerts sent for {symbol}")
        time.sleep(2)

        save_cache(cache)

# -------------------------
# مانیتور اخبار
# -------------------------
def monitor():
    while True:
        now = datetime.now()
        hour = now.hour
        if 8 <= hour < 24:
            for symbol in crypto_symbols:
                logging.info(f"🔍 Checking news for {symbol}")
                articles = get_crypto_news(symbol)
                if articles:
                    analyze_news_and_send(articles, symbol)
                time.sleep(3)
        else:
            logging.info("😴 Sleeping hours... no checking")
        time.sleep(60 * 15)

monitor_thread = threading.Thread(target=monitor)
monitor_thread.start()
