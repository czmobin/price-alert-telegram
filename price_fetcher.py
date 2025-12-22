"""
دریافت قیمت‌های ارزهای دیجیتال، طلا، نقره و دلار
"""
import requests
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from config import (
    COINGECKO_API, CRYPTO_SYMBOLS, BINANCE_SYMBOLS,
    FIAT_CURRENCIES, GOLD_COINS, GOLD_ITEMS
)
from bonbast_monitor import BonbastScraper
from jdatetime import datetime as jalalidatetime
from constants import BotConstants


class PriceFetcher:
    """کلاس دریافت قیمت‌ها از APIهای مختلف"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.bonbast_scraper = BonbastScraper()
        self._bonbast_cache = None
        self._bonbast_cache_time = None
        self._use_tgju = True  # فعال‌سازی استفاده از API tgju

    def _fetch_tgju_price(self, symbol: str, timeout: int = 5) -> Optional[Dict]:
        """
        دریافت قیمت از API tgju (سریع و بدون نیاز به مرورگر)

        Args:
            symbol: نماد مورد نظر (مثل PRICE_DOLLAR_RL, GERAM24, SILVER)
            timeout: timeout برای درخواست

        Returns:
            dict: {'price': قیمت, 'change_24h': درصد تغییرات} یا None در صورت خطا
        """
        if not self._use_tgju:
            return None

        try:
            url = f'https://platform.tgju.org/fa/tvdata/history?symbol={symbol}'
            response = self.session.get(url, timeout=timeout)

            if response.status_code == 200:
                data = response.json()

                # بررسی وجود داده
                if 'c' in data and len(data['c']) > 0:
                    current_price = data['c'][-1]  # آخرین قیمت (Close)

                    # محاسبه تغییرات 24 ساعته (اگر داده کافی داشتیم)
                    change_24h = 0.0
                    if len(data['c']) >= 2 and data['c'][-2] > 0:
                        prev_price = data['c'][-2]
                        change_24h = ((current_price - prev_price) / prev_price) * 100

                    return {
                        'price': current_price,
                        'change_24h': change_24h
                    }

            return None

        except Exception as e:
            # در صورت خطا، بدون log کردن (تا کاربر متوجه نشود) None برمی‌گردانیم
            # و سیستم به‌طور خودکار به fallback می‌رود
            return None

    def safe_float(self, value, default: float = 0.0) -> float:
        """تبدیل امن به float با مدیریت None و مقادیر نامعتبر"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def format_number(self, number: float) -> str:
        """فرمت کردن اعداد به صورت خوانا"""
        if number >= 1:
            return f"{number:,.2f}"
        elif number >= 0.01:
            return f"{number:.4f}"
        else:
            return f"{number:.8f}"

    def format_number_no_decimal(self, number: float) -> str:
        """فرمت کردن اعداد بدون اعشار (برای تومان، سکه، ارزهای فیات)"""
        return f"{int(number):,}"

    def format_percentage(self, percentage: float) -> str:
        """فرمت کردن درصد تغییرات"""
        if percentage > 0:
            return f"📈 +{percentage:.2f}%"
        elif percentage < 0:
            return f"📉 {percentage:.2f}%"
        else:
            return f"➡️ {percentage:.2f}%"

    def format_percentage_compact(self, percentage: float) -> str:
        """فرمت کردن درصد تغییرات (فرمت فشرده)"""
        if percentage > 0:
            return f"↑{percentage:.1f}%"
        elif percentage < 0:
            return f"↓{abs(percentage):.1f}%"
        else:
            return f"→{percentage:.1f}%"

    def get_trend_emoji(self, percentage: float) -> str:
        """ایموجی روند بر اساس درصد تغییر"""
        if percentage > 0:
            return "🟢"
        elif percentage < 0:
            return "🔴"
        else:
            return "🟡"

    def get_crypto_prices(self, crypto_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت ارزهای دیجیتال از Binance API (با fallback به CoinGecko)

        Returns:
            dict: {'bitcoin': {'price': 45000, 'change_24h': 5.2, 'symbol': 'BTC'}, ...}
        """
        try:
            result = {}

            # ساخت لیست symbols مورد نیاز
            symbols_list = []
            crypto_to_symbol = {}  # برای mapping برعکس

            for crypto_id in crypto_ids:
                binance_symbol = BINANCE_SYMBOLS.get(crypto_id)
                if binance_symbol:
                    symbols_list.append(binance_symbol)
                    crypto_to_symbol[binance_symbol] = crypto_id

            if not symbols_list:
                return {}

            # دریافت قیمت‌ها از Binance
            url = "https://api.binance.com/api/v3/ticker/24hr"

            # برای لیست کوچک، یکی یکی بگیریم (سریعتر و مطمئن‌تر)
            for binance_symbol in symbols_list:
                try:
                    params = {'symbol': binance_symbol}
                    response = self.session.get(url, params=params, timeout=5)

                    if response.status_code == 200:
                        data = response.json()
                        crypto_id = crypto_to_symbol[binance_symbol]

                        price = self.safe_float(data.get('lastPrice'), 0)
                        change_24h = self.safe_float(data.get('priceChangePercent'), 0)

                        result[crypto_id] = {
                            'price': price,
                            'change_24h': change_24h,
                            'change_7d': 0,  # Binance API تغییرات 7 روزه نداره
                            'symbol': CRYPTO_SYMBOLS.get(crypto_id, crypto_id.upper())
                        }
                except Exception as e:
                    # اگر یک symbol مشکل داشت، ادامه بده
                    print(f"خطا در دریافت {binance_symbol}: {e}")
                    continue

            # اگر نتونستیم از Binance بگیریم، از CoinGecko استفاده کن
            if not result:
                print("Binance ناموفق، استفاده از CoinGecko...")
                return self._get_crypto_prices_coingecko(crypto_ids)

            return result

        except Exception as e:
            print(f"خطا کلی در دریافت قیمت کریپتو: {e}")
            # fallback به روش قدیمی با CoinGecko
            return self._get_crypto_prices_coingecko(crypto_ids)

    def _get_crypto_prices_coingecko(self, crypto_ids: List[str]) -> Dict[str, Dict]:
        """روش بک‌آپ: دریافت قیمت از CoinGecko"""
        try:
            ids_string = ','.join(crypto_ids)

            url = f"{COINGECKO_API}/simple/price"
            params = {
                'ids': ids_string,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = {}
            for crypto_id in crypto_ids:
                if crypto_id in data:
                    crypto_data = data[crypto_id]
                    result[crypto_id] = {
                        'price': self.safe_float(crypto_data.get('usd'), 0),
                        'change_24h': self.safe_float(crypto_data.get('usd_24h_change'), 0),
                        'change_7d': 0,
                        'symbol': CRYPTO_SYMBOLS.get(crypto_id, crypto_id.upper())
                    }

            return result
        except Exception as e:
            print(f"خطا در دریافت قیمت از CoinGecko: {e}")
            return {}

    async def get_crypto_toman_prices(self, crypto_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت تومانی ارزهای دیجیتال از Bitpin

        Returns:
            dict: {'bitcoin': {'price': 1100000000, 'change_24h': -2.4}, ...}
        """
        # Mapping از crypto ID به symbol Bitpin
        bitpin_symbols = {
            'bitcoin': 'BTC_IRT',
            'ethereum': 'ETH_IRT',
            'tether': 'USDT_IRT',
            'ripple': 'XRP_IRT',
            'litecoin': 'LTC_IRT',
            'binancecoin': 'BNB_IRT',
            'dogecoin': 'DOGE_IRT',
            'cardano': 'ADA_IRT',
            'solana': 'SOL_IRT',
            'tron': 'TRX_IRT',
            'stellar': 'XLM_IRT',
            'polkadot': 'DOT_IRT',
            'shiba-inu': 'SHIB_IRT',
            'the-open-network': 'TON_IRT',
            'usd-coin': 'USDC_IRT',
            'chainlink': 'LINK_IRT',
            'uniswap': 'UNI_IRT',
            'avalanche-2': 'AVAX_IRT'
        }

        # Mapping معکوس برای پیدا کردن crypto ID از symbol
        symbol_to_crypto = {v: k for k, v in bitpin_symbols.items()}

        result = {}

        try:
            # درخواست به API Bitpin برای همه تیکرها
            url = "https://api.bitpin.org/api/v1/mkt/tickers/"

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # data یک لیست از تیکرها است
                # هر ticker شامل: symbol, price, daily_change_price, low, high, timestamp
                if isinstance(data, list):
                    for ticker in data:
                        symbol = ticker.get('symbol')

                        if symbol and symbol in symbol_to_crypto:
                            crypto_id = symbol_to_crypto[symbol]

                            # دریافت قیمت و تغییرات (به صورت string است)
                            price = ticker.get('price')
                            daily_change = ticker.get('daily_change_price')

                            if price:
                                # تبدیل به float (قیمت به ریال است، تبدیل به تومان)
                                price_toman = self.safe_float(price, 0) / 10
                                change_24h = self.safe_float(daily_change, 0)

                                if price_toman > 0:
                                    result[crypto_id] = {
                                        'price': price_toman,
                                        'change_24h': change_24h
                                    }

            return result

        except Exception as e:
            print(f"خطا در دریافت قیمت تومانی از Bitpin: {e}")
            return {}

    def get_gold_price(self) -> Optional[Dict]:
        """
        دریافت قیمت طلا (اونس جهانی)

        Returns:
            dict: {'price': 1850.50, 'change_7d': 2.5, 'unit': 'USD/oz'}
        """
        try:
            # استفاده از API رایگان برای قیمت طلا
            url = "https://api.gold-api.com/price/XAU"

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    'price': self.safe_float(data.get('price'), 0),
                    'change_24h': self.safe_float(data.get('change_24h'), 0),
                    'change_7d': self.safe_float(data.get('change_7d'), 0),
                    'unit': 'USD/oz',
                    'symbol': '🥇'
                }
            else:
                # اگر API اصلی کار نکرد، از CoinGecko استفاده می‌کنیم
                return self._get_gold_from_coingecko()

        except Exception as e:
            print(f"خطا در دریافت قیمت طلا: {e}")
            # تلاش برای دریافت از منبع جایگزین
            return self._get_gold_from_coingecko()

    def _get_gold_from_coingecko(self) -> Optional[Dict]:
        """دریافت قیمت طلا از CoinGecko (روش جایگزین)"""
        try:
            url = f"{COINGECKO_API}/simple/price"
            params = {
                'ids': 'pax-gold',  # توکن طلا
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_7d_change': 'true'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'pax-gold' in data:
                gold_data = data['pax-gold']
                return {
                    'price': self.safe_float(gold_data.get('usd'), 0),
                    'change_24h': self.safe_float(gold_data.get('usd_24h_change'), 0),
                    'change_7d': self.safe_float(gold_data.get('usd_7d_change'), 0),
                    'unit': 'USD/oz',
                    'symbol': '🥇'
                }
            return None

        except Exception as e:
            print(f"خطا در دریافت طلا از CoinGecko: {e}")
            return None

    def get_silver_price(self) -> Optional[Dict]:
        """
        دریافت قیمت نقره جهانی (با استفاده از tgju API و fallback به CoinGecko)

        Returns:
            dict: {'price': 24.50, 'change_7d': 1.5, 'unit': 'USD/oz'}
        """
        try:
            # روش 1: استفاده از API سریع tgju
            tgju_data = self._fetch_tgju_price('SILVER')
            if tgju_data and tgju_data.get('price', 0) > 0:
                # قیمت در tgju به دلار به ازای اونس است
                return {
                    'price': tgju_data['price'],
                    'change_24h': tgju_data.get('change_24h', 0),
                    'change_7d': 0,  # tgju فقط 24h داره
                    'unit': 'USD/oz',
                    'symbol': '🥈'
                }

            # روش 2 (fallback): استفاده از توکن نقره در CoinGecko
            url = f"{COINGECKO_API}/simple/price"
            params = {
                'ids': 'silver-token',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_7d_change': 'true'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'silver-token' in data:
                silver_data = data['silver-token']
                return {
                    'price': self.safe_float(silver_data.get('usd'), 0),
                    'change_24h': self.safe_float(silver_data.get('usd_24h_change'), 0),
                    'change_7d': self.safe_float(silver_data.get('usd_7d_change'), 0),
                    'unit': 'USD/oz',
                    'symbol': '🥈'
                }
            return None

        except Exception as e:
            print(f"خطا در دریافت قیمت نقره: {e}")
            return None

    async def get_silver_price_iran(self) -> Optional[Dict]:
        """
        دریافت قیمت نقره در ایران (تومان) - با استفاده از tgju API

        محاسبه بر اساس: قیمت جهانی نقره (tgju) × نرخ دلار (tgju)
        از tgju استفاده می‌کند (سریع و بدون نیاز به مرورگر)

        Returns:
            dict: {'price': 125000, 'change_24h': 1.5, 'unit': 'تومان/گرم', 'symbol': '🥈'}
        """
        try:
            # دریافت قیمت جهانی نقره (دلار به ازای اونس) - از tgju با fallback
            silver_global = self.get_silver_price()

            # دریافت نرخ دلار (تومان) - از tgju با fallback
            usd_irr = await self.get_usd_irr_price()

            if not silver_global or not usd_irr:
                return None

            # تبدیل اونس به گرم (1 اونس = 31.1035 گرم)
            price_per_gram_usd = silver_global['price'] / 31.1035

            # محاسبه قیمت به تومان
            price_toman = price_per_gram_usd * usd_irr['price']

            return {
                'price': price_toman,
                'change_24h': silver_global.get('change_24h', 0),
                'change_7d': silver_global.get('change_7d', 0),
                'unit': 'تومان/گرم',
                'symbol': '🥈'
            }

        except Exception as e:
            print(f"خطا در محاسبه قیمت نقره ایران: {e}")
            return None

    async def get_usd_irr_price(self) -> Optional[Dict]:
        """
        دریافت قیمت دلار به تومان (با استفاده از tgju API و fallback به روش‌های قدیمی)

        Returns:
            dict: {'price': 580000, 'change_7d': -0.5}
        """
        try:
            # روش 1: استفاده از API سریع tgju (بدون نیاز به مرورگر)
            tgju_data = self._fetch_tgju_price('PRICE_DOLLAR_RL')
            if tgju_data and tgju_data.get('price', 0) > 0:
                # قیمت در tgju به ریال است، تبدیل به تومان می‌کنیم
                price_toman = tgju_data['price'] / 10
                return {
                    'price': price_toman,
                    'change_24h': tgju_data.get('change_24h', 0),
                    'change_7d': 0,  # tgju فقط 24h داره
                    'unit': 'تومان',
                    'symbol': '💵'
                }

            # روش 2 (fallback): استفاده از API accessban
            url = "https://api.accessban.com/v1/market/indicator/summary-table-data/price_dollar_rl"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # چک کردن فرمت داده (ممکنه dict یا list باشه)
                if isinstance(data, dict) and 'data' in data:
                    price_data = data['data']
                    if isinstance(price_data, dict):
                        current_price = self.safe_float(price_data.get('p'), 0) / 10  # تبدیل به تومان
                    elif isinstance(price_data, list) and len(price_data) > 0:
                        # اگر لیست بود، اولین آیتم رو بگیر
                        current_price = self.safe_float(price_data[0].get('p'), 0) / 10 if isinstance(price_data[0], dict) else 0
                    else:
                        current_price = 0

                    if current_price > 0:
                        return {
                            'price': current_price,
                            'change_24h': 0,  # این API تغییرات را ندارد
                            'change_7d': 0,
                            'unit': 'تومان',
                            'symbol': '💵'
                        }
                elif isinstance(data, list) and len(data) > 0:
                    # اگر مستقیم لیست بود
                    price_data = data[0] if isinstance(data[0], dict) else {}
                    current_price = self.safe_float(price_data.get('p'), 0) / 10 if price_data else 0

                    if current_price > 0:
                        return {
                            'price': current_price,
                            'change_24h': 0,
                            'change_7d': 0,
                            'unit': 'تومان',
                            'symbol': '💵'
                        }

            # روش 3 (fallback نهایی): استفاده از API bonbast (غیررسمی)
            return await self._get_usd_from_bonbast()

        except Exception as e:
            print(f"خطا در دریافت قیمت دلار: {e}")
            return await self._get_usd_from_bonbast()

    async def _get_bonbast_data(self, use_cache: bool = True) -> Optional[Dict]:
        """
        دریافت داده‌های bonbast با cache

        Args:
            use_cache: استفاده از cache (5 دقیقه)
        """
        try:
            # بررسی cache
            if use_cache and self._bonbast_cache and self._bonbast_cache_time:
                time_diff = (datetime.now() - self._bonbast_cache_time).total_seconds()
                if time_diff < 300:  # 5 minutes
                    return self._bonbast_cache

            # دریافت داده‌های جدید
            rates = await self.bonbast_scraper.get_rates()

            if rates:
                extracted_data = self.bonbast_scraper.extract_currency_data(rates)
                self._bonbast_cache = extracted_data
                self._bonbast_cache_time = datetime.now()
                return extracted_data

            return None

        except Exception as e:
            print(f"خطا در دریافت داده از Bonbast: {e}")
            return None

    async def _get_usd_from_bonbast(self) -> Optional[Dict]:
        """دریافت قیمت دلار از Bonbast (روش جایگزین)"""
        try:
            bonbast_data = await self._get_bonbast_data()

            if bonbast_data and 'currencies' in bonbast_data:
                usd_data = bonbast_data['currencies'].get('usd')
                if usd_data:
                    return {
                        'price': usd_data['sell'],
                        'change_24h': 0,
                        'change_7d': 0,
                        'unit': 'تومان',
                        'symbol': '💵'
                    }

            # API بک‌آپ دوم: tgju.org
            return self._get_usd_from_tgju()

        except Exception as e:
            print(f"خطا در دریافت دلار از Bonbast: {e}")
            return self._get_usd_from_tgju()

    def _get_usd_from_tgju(self) -> Optional[Dict]:
        """دریافت قیمت دلار از tgju (روش بک‌آپ دوم)"""
        try:
            # استفاده از API عمومی tgju
            url = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # استخراج قیمت از فرمت‌های مختلف
                price = None

                if isinstance(data, dict):
                    if 'data' in data:
                        price_data = data['data']
                        if isinstance(price_data, dict):
                            price = price_data.get('p')
                        elif isinstance(price_data, list) and len(price_data) > 0:
                            price = price_data[0].get('p') if isinstance(price_data[0], dict) else None
                    elif 'p' in data:
                        price = data.get('p')
                elif isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        price = data[0].get('p')

                if price:
                    current_price = self.safe_float(price, 0) / 10  # تبدیل به تومان
                    if current_price > 0:
                        return {
                            'price': current_price,
                            'change_24h': 0,
                            'change_7d': 0,
                            'unit': 'تومان',
                            'symbol': '💵'
                        }

            # اگر همه API ها فیل شدند، یک قیمت ثابت موقت برگردون
            print("تمام API های دلار فیل شدند، استفاده از قیمت تخمینی")
            return {
                'price': 700000,  # قیمت تخمینی
                'change_24h': 0,
                'change_7d': 0,
                'unit': 'تومان (تخمینی)',
                'symbol': '💵'
            }

        except Exception as e:
            print(f"خطا در دریافت دلار از tgju: {e}")
            # قیمت پیش‌فرض در صورت خطا
            return {
                'price': 700000,
                'change_24h': 0,
                'change_7d': 0,
                'unit': 'تومان (تخمینی)',
                'symbol': '💵'
            }

    async def get_fiat_currencies(self, currency_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت ارزهای فیات از bonbast

        Returns:
            dict: {'usd': {'name': '...', 'buy': 112850, 'sell': 112750}, ...}
        """
        try:
            bonbast_data = await self._get_bonbast_data()

            if not bonbast_data or 'currencies' not in bonbast_data:
                return {}

            result = {}
            for currency_id in currency_ids:
                if currency_id in bonbast_data['currencies']:
                    currency_data = bonbast_data['currencies'][currency_id]
                    result[currency_id] = {
                        'name': currency_data['name'],
                        'buy': currency_data['buy'],
                        'sell': currency_data['sell'],
                        'symbol': FIAT_CURRENCIES.get(currency_id, {}).get('symbol', currency_id.upper())
                    }

            return result

        except Exception as e:
            print(f"خطا در دریافت ارزهای فیات: {e}")
            return {}

    async def get_gold_coins(self, coin_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت سکه‌های طلا از bonbast

        Returns:
            dict: {'azadi1': {'name': '...', 'buy': 111600000, 'sell': 109800000}, ...}
        """
        try:
            bonbast_data = await self._get_bonbast_data()

            if not bonbast_data or 'coins' not in bonbast_data:
                return {}

            result = {}
            for coin_id in coin_ids:
                if coin_id in bonbast_data['coins']:
                    coin_data = bonbast_data['coins'][coin_id]
                    result[coin_id] = {
                        'name': coin_data['name'],
                        'buy': coin_data['buy'],
                        'sell': coin_data['sell'],
                        'symbol': GOLD_COINS.get(coin_id, {}).get('symbol', '🪙')
                    }

            return result

        except Exception as e:
            print(f"خطا در دریافت سکه‌های طلا: {e}")
            return {}

    async def get_gold_items(self, item_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت آیتم‌های طلا (با استفاده از tgju API و fallback به bonbast)

        Returns:
            dict: {'gol18': {'name': '...', 'price': 11306847}, ...}
        """
        try:
            # نقشه‌برداری از item_id به نماد tgju
            tgju_symbol_map = {
                'gol18': 'GERAM18',
                'mithqal': 'MESGHAL',
                'ounce': 'GOLD'  # اونس طلا
            }

            result = {}

            # روش 1: استفاده از API سریع tgju
            for item_id in item_ids:
                if item_id in tgju_symbol_map:
                    tgju_data = self._fetch_tgju_price(tgju_symbol_map[item_id])
                    if tgju_data and tgju_data.get('price', 0) > 0:
                        # قیمت در tgju به تومان است
                        result[item_id] = {
                            'name': GOLD_ITEMS.get(item_id, {}).get('name', item_id),
                            'price': tgju_data['price'],
                            'unit': 'تومان',
                            'symbol': GOLD_ITEMS.get(item_id, {}).get('symbol', '✨')
                        }

            # اگر همه آیتم‌ها با موفقیت دریافت شدند، برگردان
            if len(result) == len(item_ids):
                return result

            # روش 2 (fallback): استفاده از bonbast برای آیتم‌های ناموفق
            bonbast_data = await self._get_bonbast_data()

            if bonbast_data and 'gold' in bonbast_data:
                for item_id in item_ids:
                    # اگر قبلاً از tgju گرفته شد، skip کن
                    if item_id in result:
                        continue

                    if item_id in bonbast_data['gold']:
                        gold_data = bonbast_data['gold'][item_id]
                        result[item_id] = {
                            'name': gold_data['name'],
                            'price': gold_data['price'],
                            'unit': gold_data['unit'],
                            'symbol': GOLD_ITEMS.get(item_id, {}).get('symbol', '✨')
                        }

            return result

        except Exception as e:
            print(f"خطا در دریافت آیتم‌های طلا: {e}")
            return {}

    async def get_all_prices(self, crypto_ids: List[str] = None,
                      include_gold: bool = True,
                      include_silver: bool = True,
                      include_usd: bool = True,
                      fiat_currency_ids: List[str] = None,
                      gold_coin_ids: List[str] = None,
                      gold_item_ids: List[str] = None) -> Dict:
        """
        دریافت تمام قیمت‌ها

        Returns:
            dict: {
                'cryptos': {...},
                'gold': {...},
                'silver': {...},
                'silver_iran': {...},
                'usd_irr': {...},
                'fiat_currencies': {...},
                'gold_coins': {...},
                'gold_items': {...}
            }
        """
        result = {
            'cryptos': {},
            'gold': None,
            'silver': None,
            'silver_iran': None,
            'usd_irr': None,
            'fiat_currencies': {},
            'gold_coins': {},
            'gold_items': {},
            'timestamp': datetime.now().isoformat()
        }

        # دریافت قیمت کریپتوها
        if crypto_ids:
            result['cryptos'] = self.get_crypto_prices(crypto_ids)
            # دریافت قیمت تومانی
            toman_prices = await self.get_crypto_toman_prices(crypto_ids)
            # افزودن قیمت تومانی به نتایج
            for crypto_id, toman_data in toman_prices.items():
                if crypto_id in result['cryptos']:
                    result['cryptos'][crypto_id]['price_toman'] = toman_data.get('price')
                    # استفاده از تغییرات تومانی اگر موجود بود
                    if 'change_24h' in toman_data:
                        result['cryptos'][crypto_id]['change_24h_toman'] = toman_data['change_24h']

        # دریافت قیمت طلا
        if include_gold:
            result['gold'] = self.get_gold_price()

        # دریافت قیمت نقره جهانی
        if include_silver:
            result['silver'] = self.get_silver_price()

        # دریافت قیمت دلار
        if include_usd:
            result['usd_irr'] = await self.get_usd_irr_price()

        # دریافت قیمت نقره ایران (بعد از دریافت دلار)
        if include_silver:
            result['silver_iran'] = await self.get_silver_price_iran()

        # دریافت ارزهای فیات
        if fiat_currency_ids:
            result['fiat_currencies'] = await self.get_fiat_currencies(fiat_currency_ids)

        # دریافت سکه‌های طلا
        if gold_coin_ids:
            result['gold_coins'] = await self.get_gold_coins(gold_coin_ids)

        # دریافت آیتم‌های طلا
        if gold_item_ids:
            result['gold_items'] = await self.get_gold_items(gold_item_ids)

        return result

    def format_price_message(self, prices: Dict) -> tuple:
        """
        فرمت کردن قیمت‌ها به صورت پیام تلگرام (فرمت فشرده)

        Args:
            prices: خروجی تابع get_all_prices

        Returns:
            tuple: (پیام فرمت شده, آیا خطایی وجود داشته)
        """
        lines = []
        lines.append("📊 وضعیت بازار همین لحظه با ارزَلان")
        lines.append("")
        has_error = False

        # 1. دلار آمریکا
        if prices.get('usd_irr'):
            usd = prices['usd_irr']
            lines.append(f"{usd['symbol']} دلار: {self.format_number_no_decimal(usd['price'])}")
        else:
            has_error = True

        # 2. طلای 18 عیار (از آیتم‌های طلا)
        if prices.get('gold_items'):
            for item_id, data in prices['gold_items'].items():
                if item_id == 'gol18':
                    lines.append(f"{data['symbol']} {data['name']}: {self.format_number_no_decimal(data['price'])}")

        # 3. نقره ایران (تومان)
        if prices.get('silver_iran') and prices['silver_iran'] is not None:
            silver_iran = prices['silver_iran']
            lines.append(f"{silver_iran['symbol']} نقره (گرم): {self.format_number_no_decimal(silver_iran['price'])}")

        lines.append("")

        # 4. ارزهای دیجیتال
        if prices.get('cryptos'):
            for crypto_id, data in prices['cryptos'].items():
                symbol = data['symbol']
                price_usd = self.format_number(data['price'])
                change_24h = data.get('change_24h', 0)
                change_str = self.format_percentage_compact(change_24h)
                emoji = self.get_trend_emoji(change_24h)

                # خط اول: قیمت دلاری
                lines.append(f"{emoji} {symbol} USDT: ${price_usd} (24h: {change_str})")

                # خط دوم: قیمت تومانی (اگر موجود باشد)
                if 'price_toman' in data and data.get('price_toman') and data['price_toman'] > 0:
                    price_toman = self.format_number_no_decimal(data['price_toman'])
                    # استفاده از تغییرات تومانی اگر موجود بود
                    change_24h_toman = data.get('change_24h_toman', change_24h)
                    change_toman_str = self.format_percentage_compact(change_24h_toman)
                    emoji_toman = self.get_trend_emoji(change_24h_toman)
                    lines.append(f"{emoji_toman} {symbol} IRT: {price_toman} (24h: {change_toman_str})")
                    lines.append("")

        # 5. سکه‌های طلا
        if prices.get('gold_coins'):
            lines.append("")
            for coin_id, data in prices['gold_coins'].items():
                symbol = data['symbol']
                name = data['name']
                buy = self.format_number_no_decimal(data['buy'])
                lines.append(f"{symbol} {name}: {buy}")

        # 6. سایر آیتم‌های طلا (به جز طلای 18 عیار که قبلاً نمایش داده شد)
        if prices.get('gold_items'):
            for item_id, data in prices['gold_items'].items():
                if item_id != 'gol18':
                    symbol = data['symbol']
                    name = data['name']
                    price = self.format_number_no_decimal(data['price'])
                    lines.append(f"{symbol} {name}: {price}")

        # 7. ارزهای فیات
        if prices.get('fiat_currencies'):
            lines.append("")
            for currency_id, data in prices['fiat_currencies'].items():
                name = data['name']
                buy = self.format_number_no_decimal(data['buy'])
                lines.append(f"{name}: {buy}")

        # Footer استاندارد
        lines.append("")
        lines.append(BotConstants.get_message_footer(include_divider=True))

        # بررسی اینکه آیا اصلا داده‌ای داریم یا نه
        if not prices.get('cryptos') and not prices.get('usd_irr') and not prices.get('gold_items'):
            has_error = True

        return "\n".join(lines), has_error
