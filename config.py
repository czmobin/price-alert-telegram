"""
تنظیمات ربات تلگرام
"""
import os
from dotenv import load_dotenv

load_dotenv()

# تنظیمات تلگرام
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@your_channel_id')  # آیدی کانال برای چک عضویت

# تنظیمات پایگاه داده
DATABASE_PATH = 'bot_database.db'

# API endpoints
COINGECKO_API = 'https://api.coingecko.com/api/v3'
TGJU_API = 'https://api.tgju.org/v1'

# ارزهای دیجیتال پیش‌فرض (5 ارز برتر بازار)
TOP_5_CRYPTOS = ['bitcoin', 'ethereum', 'tether', 'binancecoin', 'solana']

# 10 ارز منتخب بازار
TOP_10_CRYPTOS = [
    'bitcoin', 'ethereum', 'tether', 'binancecoin', 'solana',
    'ripple', 'dogecoin', 'the-open-network', 'cardano', 'tron'
]

# ارزهای پیش‌فرض برای کاربر
DEFAULT_CRYPTOS = TOP_5_CRYPTOS

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
    'stellar': 'XLM',
    'the-open-network': 'TON',
    'uniswap': 'UNI',
    'matic-network': 'MATIC',
    'shiba-inu': 'SHIB',
    'cosmos': 'ATOM'
}

# منابع قیمت دیگر
OTHER_ASSETS = ['gold', 'silver', 'usd_irr']

# تنظیمات زمانی
DEFAULT_NOTIFICATION_TIME = '09:00'
TIMEZONE = 'Asia/Tehran'

# ساعت‌های پیش‌فرض برای زمان‌بندی
PRESET_TIMES = [
    '08:00',
    '10:00',
    '12:00',
    '15:00',
    '18:00',
    '21:00'
]
