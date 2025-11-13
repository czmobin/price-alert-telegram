"""
تنظیمات ربات تلگرام
"""
import os
from dotenv import load_dotenv

load_dotenv()

# تنظیمات تلگرام
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# تنظیمات پایگاه داده
DATABASE_PATH = 'bot_database.db'

# API endpoints
COINGECKO_API = 'https://api.coingecko.com/api/v3'
TGJU_API = 'https://api.tgju.org/v1'

# ارزهای دیجیتال پیش‌فرض
DEFAULT_CRYPTOS = ['bitcoin', 'ethereum', 'binancecoin', 'cardano', 'ripple', 'solana', 'polkadot', 'dogecoin']

# نمادهای نمایشی
CRYPTO_SYMBOLS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'binancecoin': 'BNB',
    'cardano': 'ADA',
    'ripple': 'XRP',
    'solana': 'SOL',
    'polkadot': 'DOT',
    'dogecoin': 'DOGE',
    'tether': 'USDT',
    'usd-coin': 'USDC',
    'litecoin': 'LTC',
    'chainlink': 'LINK',
    'avalanche-2': 'AVAX',
    'tron': 'TRX',
    'stellar': 'XLM'
}

# منابع قیمت دیگر
OTHER_ASSETS = ['gold', 'silver', 'usd_irr']

# تنظیمات زمانی
DEFAULT_NOTIFICATION_TIME = '09:00'
TIMEZONE = 'Asia/Tehran'
