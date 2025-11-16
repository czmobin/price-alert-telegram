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

# نقشه crypto ID به symbol بایننس
BINANCE_SYMBOLS = {
    'bitcoin': 'BTCUSDT',
    'ethereum': 'ETHUSDT',
    'binancecoin': 'BNBUSDT',
    'cardano': 'ADAUSDT',
    'ripple': 'XRPUSDT',
    'solana': 'SOLUSDT',
    'polkadot': 'DOTUSDT',
    'dogecoin': 'DOGEUSDT',
    'tether': 'USDTUSD',
    'usd-coin': 'USDCUSDT',
    'litecoin': 'LTCUSDT',
    'chainlink': 'LINKUSDT',
    'avalanche-2': 'AVAXUSDT',
    'tron': 'TRXUSDT',
    'stellar': 'XLMUSDT',
    'the-open-network': 'TONUSDT',
    'uniswap': 'UNIUSDT',
    'matic-network': 'MATICUSDT',
    'shiba-inu': 'SHIBUSDT',
    'cosmos': 'ATOMUSDT'
}

# منابع قیمت دیگر
OTHER_ASSETS = ['gold', 'silver', 'usd_irr']

# ارزهای فیات (از bonbast)
FIAT_CURRENCIES = {
    'usd': {'name': 'دلار آمریکا', 'symbol': '💵', 'flag': '🇺🇸'},
    'eur': {'name': 'یورو', 'symbol': '💶', 'flag': '🇪🇺'},
    'gbp': {'name': 'پوند انگلیس', 'symbol': '💷', 'flag': '🇬🇧'},
    'chf': {'name': 'فرانک سوئیس', 'symbol': 'CHF', 'flag': '🇨🇭'},
    'cad': {'name': 'دلار کانادا', 'symbol': 'CAD', 'flag': '🇨🇦'},
    'aud': {'name': 'دلار استرالیا', 'symbol': 'AUD', 'flag': '🇦🇺'},
    'jpy': {'name': 'ین ژاپن', 'symbol': 'JPY', 'flag': '🇯🇵'},
    'cny': {'name': 'یوان چین', 'symbol': 'CNY', 'flag': '🇨🇳'},
    'try': {'name': 'لیر ترکیه', 'symbol': 'TRY', 'flag': '🇹🇷'},
    'rub': {'name': 'روبل روسیه', 'symbol': 'RUB', 'flag': '🇷🇺'},
    'aed': {'name': 'درهم امارات', 'symbol': 'AED', 'flag': '🇦🇪'},
    'kwd': {'name': 'دینار کویت', 'symbol': 'KWD', 'flag': '🇰🇼'},
}

# ارزهای فیات پیش‌فرض
DEFAULT_FIAT_CURRENCIES = ['usd', 'eur', 'gbp']

# سکه‌های طلا (از bonbast)
GOLD_COINS = {
    'azadi1': {'name': 'سکه بهار آزادی', 'symbol': '🪙'},
    'azadi1_2': {'name': 'نیم سکه', 'symbol': '🪙'},
    'azadi1_4': {'name': 'ربع سکه', 'symbol': '🪙'},
    'azadi1g': {'name': 'یک گرمی', 'symbol': '🪙'},
    'emami1': {'name': 'سکه امامی', 'symbol': '🪙'}
}

# آیتم‌های طلا (از bonbast)
GOLD_ITEMS = {
    'gol18': {'name': 'طلای ۱۸ عیار (گرم)', 'symbol': '✨'},
    'mithqal': {'name': 'مثقال طلا', 'symbol': '⚖️'},
    'ounce': {'name': 'اونس طلا', 'symbol': '🥇'}
}

# سکه‌های پیش‌فرض
DEFAULT_COINS = ['azadi1', 'azadi1_2']

# طلاهای پیش‌فرض
DEFAULT_GOLD_ITEMS = ['gol18']

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
