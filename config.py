# config.py

import os

# توکن تلگرام
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# شناسه چت تلگرام
CHAT_ID = os.environ.get('CHAT_ID')

# کلید API NewsAPI
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')

# کلمات کلیدی حساس برای شناسایی اخبار مهم
SENSITIVE_KEYWORDS = ['pump', 'surge', 'spike', 'skyrocketing', 'dump', 'fall', 'crash', 'drop']
