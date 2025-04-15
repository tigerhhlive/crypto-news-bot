from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Crypto News Bot is running.'

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# اجرای Flask در یک نخ جداگانه
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

import os
import requests
import logging
import telegram
import time
from datetime import datetime
import schedule
from config import TELEGRAM_TOKEN, CHAT_ID, NEWS_API_KEY, SENSITIVE_KEYWORDS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ارسال پیام به تلگرام
def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=message)

# دریافت اخبار از API
def get_crypto_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200 and 'articles' in data:
            return data['articles']
        else:
            logging.error(f"Error fetching news for {symbol}: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        logging.error(f"Error fetching news for {symbol}: {str(e)}")
        return []

# تحلیل و ارسال اخبار مهم به تلگرام
def analyze_news_and_send(articles, symbol):
    for article in articles:
        title = article.get('title', 'No Title')
        description = article.get('description', 'No Description')
        url = article.get('url', 'No URL')

        # بررسی وجود کلمات حساس در عنوان یا توضیحات
        if any(keyword.lower() in (title + description).lower() for keyword in SENSITIVE_KEYWORDS):
            message = f"🚨 *Important News about {symbol}*\n\n*Title:* {title}\n*Description:* {description}\n*Link:* {url}"
            send_telegram_message(message)
            logging.info(f"Sent alert for {symbol}: {title}")

# بررسی اخبار برای رمز ارزهای مختلف
def check_news_for_symbols(symbols):
    for symbol in symbols:
        articles = get_crypto_news(symbol)
        if articles:
            analyze_news_and_send(articles, symbol)

# تنظیم زمان‌بندی برای اجرا
def schedule_news_check(symbols):
    # فعال بودن ربات فقط از 8 صبح تا 12 شب
    current_hour = datetime.now().hour
    if 8 <= current_hour < 24:
        check_news_for_symbols(symbols)

    # در حالت خواب بین ساعت 12 شب تا 8 صبح هیچ کاری انجام نده
    if current_hour >= 24 or current_hour < 8:
        logging.info("Sleeping hours, no news checking.")

# لیست رمز ارزها برای بررسی اخبار
crypto_symbols = ['Bitcoin', 'Ethereum', 'Dogecoin', 'XRP', 'Litecoin', 'Cardano', 'Solana', 'Polkadot', 'BinanceCoin', 'Shiba Inu', 
                  'Avalanche', 'Polygon', 'Chainlink', 'Uniswap', 'Terra', 'Dogecoin', 'BinanceCoin', 'Ethereum Classic', 'VeChain', 'Litecoin']

# برنامه‌ریزی برای چک کردن اخبار هر ساعت
schedule.every().hour.do(schedule_news_check, symbols=crypto_symbols)

# اجرای برنامه
def run_bot():
    while True:
        schedule.run_pending()
        time.sleep(60)  # هر دقیقه یک بار چک کردن زمان‌بندی

if __name__ == '__main__':
    run_bot()
