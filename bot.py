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
from config import TELEGRAM_TOKEN, CHAT_ID, NEWS_API_KEY, SENSITIVE_KEYWORDS, TRUSTED_SOURCES, CRITICAL_NAMES

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Crypto News Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

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

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, 'r') as f:
        return set(json.load(f))

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(list(cache), f)

cache = load_cache()

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

def score_news(title, desc, source, symbol=None):
    score = 0
    combined = f"{title} {desc}".lower()

    if any(trusted in source for trusted in TRUSTED_SOURCES):
        score += 1
    if '?' not in title and not any(w in title.lower() for w in ['might', 'could', 'may']):
        score += 1
    score += len([kw for kw in SENSITIVE_KEYWORDS if kw in combined])
    sentiment = analyzer.polarity_scores(combined)
    if sentiment['compound'] >= 0.5 or sentiment['compound'] <= -0.5:
        score += 2
    if symbol and symbol.lower() in ['bitcoin', 'ethereum', 'bnb']:
        score += 1
    if any(name.lower() in combined for name in CRITICAL_NAMES):
        score += 3

    tags = [kw for kw in CRITICAL_NAMES if kw.lower() in combined]
    return score, tags, sentiment['compound']

def analyze_and_send(articles, symbol=None):
    important = []
    for a in articles:
        title = a.get('title', '')
        desc = a.get('description', '')
        url = a.get('url', '')
        source = a.get('source', {}).get('name', '')
        content_id = url or title
        if content_id in cache:
            continue
        score, tags, sentiment = score_news(title, desc, source, symbol)
        if score >= 5:
            important.append((title, desc, url, source, tags, score, sentiment))
            cache.add(content_id)
        if len(important) >= MAX_MESSAGES_PER_SYMBOL:
            break

    if important:
        msg = f"🚨 *High-Impact News {'on ' + symbol if symbol else '[Global]'}*

"
        for i, (title, desc, url, source, tags, score, sentiment) in enumerate(important, 1):
            msg += f"*{i}. {title}*
{desc}
🔗 {url}
📡 Source: `{source}`
🏷 Tags: `{', '.join(tags)}`
🧠 Score: `{score}` | Sentiment: `{sentiment:.2f}`

"
        send_telegram_message(msg)
        logging.info(f"📨 Sent {len(important)} important news.")
        save_cache(cache)

def monitor_symbols():
    while True:
        now = datetime.now()
        hour = now.hour
        if 8 <= hour < 24:
            for symbol in crypto_symbols:
                logging.info(f"🔍 Checking symbol news for {symbol}")
                articles = get_news(symbol)
                analyze_and_send(articles, symbol)
                time.sleep(3)
        else:
            logging.info("😴 Symbol monitoring paused (night hours).")
        time.sleep(900)

def monitor_general():
    while True:
        logging.info("🌍 Checking general crypto news")
        articles = get_news("cryptocurrency OR bitcoin OR crypto")
        analyze_and_send(articles, None)
        time.sleep(600)

threading.Thread(target=monitor_symbols).start()
threading.Thread(target=monitor_general).start()
