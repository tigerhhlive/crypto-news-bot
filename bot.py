from flask import Flask
import threading
import time
import logging
import requests
import telegram
import json
import os
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import TELEGRAM_TOKEN, CHAT_ID, NEWS_API_KEY, SENSITIVE_KEYWORDS, TRUSTED_SOURCES, CRITICAL_NAMES
from dateutil import parser

# ========== Flask App for Render ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Crypto News Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# ========== Logging & Setup ==========
logging.basicConfig(level=logging.INFO)
analyzer = SentimentIntensityAnalyzer()
bot = telegram.Bot(token=TELEGRAM_TOKEN)
CACHE_FILE = "news_cache.json"
MAX_MESSAGES_PER_SYMBOL = 2

crypto_symbols = [
    'Bitcoin', 'Ethereum', 'Dogecoin', 'XRP',
    'Cardano', 'Solana', 'Polkadot', 'BinanceCoin', 
    'Avalanche', 'Polygon', 'Chainlink', 'Uniswap', 
    'Stellar', 'Aptos', 'Arbitrum', 'AAVE'
]

# ========== Cache ==========
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, 'r') as f:
        return set(json.load(f))

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(list(cache), f)

cache = load_cache()

# ========== Helpers ==========
def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"❌ Telegram Error: {e}")
        time.sleep(10)

def get_news(query):
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        return data.get("articles", [])
    except Exception as e:
        logging.error(f"Error fetching news for query: {query} => {e}")
        return []

def is_recent(published_at, max_minutes=120):
    try:
        pub_time = parser.parse(published_at)
        now = datetime.now(timezone.utc)
        diff = (now - pub_time).total_seconds() / 60
        return diff <= max_minutes
    except Exception as e:
        logging.warning(f"Time parse failed: {e}")
        return False

def score_news(title, desc, source, combined, sentiment, symbol=None):
    score = 0
    if any(trusted in source for trusted in TRUSTED_SOURCES):
        score += 1
    if '?' not in title and not any(w in title.lower() for w in ['might', 'could', 'may']):
        score += 1
    score += len([kw for kw in SENSITIVE_KEYWORDS if kw in combined])
    if abs(sentiment['compound']) >= 0.7:
        score += 2
    if symbol and symbol.lower() in ['bitcoin', 'ethereum', 'bnb']:
        score += 1
    if any(name.lower() in combined for name in CRITICAL_NAMES):
        score += 3
    return score

# ========== تحلیل خبر و ارسال ==========
def analyze_and_send(articles, symbol=None):
    important = []
    for a in articles:
        title = a.get('title', '')
        desc = a.get('description', '')
        url = a.get('url', '')
        source = a.get('source', {}).get('name', '')
        published_at = a.get('publishedAt', '')
        content_id = url or title

        if content_id in cache:
            continue

        if not is_recent(published_at):
            continue

        combined = f"{title} {desc}".lower()
        sentiment = analyzer.polarity_scores(combined)
        score = score_news(title, desc, source, combined, sentiment, symbol)
        tags = [kw for kw in CRITICAL_NAMES if kw.lower() in combined]

        if score >= 6:
            important.append((title, desc, url, source, tags, score, sentiment['compound']))
            cache.add(content_id)

        if len(important) >= MAX_MESSAGES_PER_SYMBOL:
            break

    if important:
        header = f"🚨 *High-Impact News on {symbol}*\n\n" if symbol else "🚨 *High-Impact News [Global]*\n\n"
        msg = header
        for i, (title, desc, url, source, tags, score, sent) in enumerate(important, 1):
            msg += f"*{i}. {title}*\n{desc}\n🔗 {url}\n📡 Source: `{source}`\n🏷 Tags: `{', '.join(tags)}`\n🧠 Score: `{score}` | Sentiment: `{sent:.2f}`\n\n"
        send_telegram_message(msg)
        logging.info(f"📨 Sent {len(important)} important news.")
        save_cache(cache)

# ========== مانیتور رمز ارزها (بدون محدودیت زمانی) ==========
def monitor_symbols():
    while True:
        for symbol in crypto_symbols:
            logging.info(f"🔍 Checking symbol news for {symbol}")
            articles = get_news(symbol)
            analyze_and_send(articles, symbol)
            time.sleep(3)      # فاصله بین هر کوئری برای حفظ سهمیه API
        time.sleep(900)       # هر 15 دقیقه یک دور کامل


# ========== مانیتور اخبار عمومی بازار ==========
def monitor_general():
    while True:
        logging.info("🌍 Checking general crypto news")
        articles = get_news("cryptocurrency OR bitcoin OR crypto")
        analyze_and_send(articles, None)
        time.sleep(600)

# ========== اجرای موازی ==========
threading.Thread(target=monitor_symbols).start()
threading.Thread(target=monitor_general).start()
