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

    def format_number(self, number: float) -> str:
        """فرمت کردن اعداد به صورت خوانا"""
        if number >= 1:
            return f"{number:,.2f}"
        elif number >= 0.01:
            return f"{number:.4f}"
        else:
            return f"{number:.8f}"

    def format_percentage(self, percentage: float) -> str:
        """فرمت کردن درصد تغییرات"""
        if percentage > 0:
            return f"📈 +{percentage:.2f}%"
        elif percentage < 0:
            return f"📉 {percentage:.2f}%"
        else:
            return f"➡️ {percentage:.2f}%"

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

                        price = float(data.get('lastPrice', 0))
                        change_24h = float(data.get('priceChangePercent', 0))

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
                        'price': crypto_data.get('usd', 0),
                        'change_24h': crypto_data.get('usd_24h_change', 0),
                        'change_7d': 0,
                        'symbol': CRYPTO_SYMBOLS.get(crypto_id, crypto_id.upper())
                    }

            return result
        except Exception as e:
            print(f"خطا در دریافت قیمت از CoinGecko: {e}")
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
                    'price': data.get('price', 0),
                    'change_24h': data.get('change_24h', 0),
                    'change_7d': data.get('change_7d', 0),
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
                    'price': gold_data.get('usd', 0),
                    'change_24h': gold_data.get('usd_24h_change', 0),
                    'change_7d': gold_data.get('usd_7d_change', 0),
                    'unit': 'USD/oz',
                    'symbol': '🥇'
                }
            return None

        except Exception as e:
            print(f"خطا در دریافت طلا از CoinGecko: {e}")
            return None

    def get_silver_price(self) -> Optional[Dict]:
        """
        دریافت قیمت نقره

        Returns:
            dict: {'price': 24.50, 'change_7d': 1.5, 'unit': 'USD/oz'}
        """
        try:
            # استفاده از توکن نقره در CoinGecko
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
                    'price': silver_data.get('usd', 0),
                    'change_24h': silver_data.get('usd_24h_change', 0),
                    'change_7d': silver_data.get('usd_7d_change', 0),
                    'unit': 'USD/oz',
                    'symbol': '🥈'
                }
            return None

        except Exception as e:
            print(f"خطا در دریافت قیمت نقره: {e}")
            return None

    def get_usd_irr_price(self) -> Optional[Dict]:
        """
        دریافت قیمت دلار به تومان

        Returns:
            dict: {'price': 580000, 'change_7d': -0.5}
        """
        try:
            # استفاده از API tgju برای قیمت دلار
            url = "https://api.accessban.com/v1/market/indicator/summary-table-data/price_dollar_rl"

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # چک کردن فرمت داده (ممکنه dict یا list باشه)
                if isinstance(data, dict) and 'data' in data:
                    price_data = data['data']
                    if isinstance(price_data, dict):
                        current_price = float(price_data.get('p', 0)) / 10  # تبدیل به تومان
                    elif isinstance(price_data, list) and len(price_data) > 0:
                        # اگر لیست بود، اولین آیتم رو بگیر
                        current_price = float(price_data[0].get('p', 0)) / 10 if isinstance(price_data[0], dict) else 0
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
                    current_price = float(price_data.get('p', 0)) / 10 if price_data else 0

                    if current_price > 0:
                        return {
                            'price': current_price,
                            'change_24h': 0,
                            'change_7d': 0,
                            'unit': 'تومان',
                            'symbol': '💵'
                        }

            # روش جایگزین: استفاده از API bonbast (غیررسمی)
            return self._get_usd_from_bonbast()

        except Exception as e:
            print(f"خطا در دریافت قیمت دلار: {e}")
            return self._get_usd_from_bonbast()

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

    def _get_bonbast_data_sync(self, use_cache: bool = True) -> Optional[Dict]:
        """نسخه sync از تابع دریافت داده bonbast"""
        try:
            # اجرای async function در sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._get_bonbast_data(use_cache))
            loop.close()
            return result
        except Exception as e:
            print(f"خطا در دریافت داده از Bonbast (sync): {e}")
            return None

    def _get_usd_from_bonbast(self) -> Optional[Dict]:
        """دریافت قیمت دلار از Bonbast (روش جایگزین)"""
        try:
            bonbast_data = self._get_bonbast_data_sync()

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
                    current_price = float(price) / 10  # تبدیل به تومان
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

    def get_fiat_currencies(self, currency_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت ارزهای فیات از bonbast

        Returns:
            dict: {'usd': {'name': '...', 'buy': 112850, 'sell': 112750}, ...}
        """
        try:
            bonbast_data = self._get_bonbast_data_sync()

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

    def get_gold_coins(self, coin_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت سکه‌های طلا از bonbast

        Returns:
            dict: {'azadi1': {'name': '...', 'buy': 111600000, 'sell': 109800000}, ...}
        """
        try:
            bonbast_data = self._get_bonbast_data_sync()

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

    def get_gold_items(self, item_ids: List[str]) -> Dict[str, Dict]:
        """
        دریافت قیمت آیتم‌های طلا از bonbast

        Returns:
            dict: {'gol18': {'name': '...', 'price': 11306847}, ...}
        """
        try:
            bonbast_data = self._get_bonbast_data_sync()

            if not bonbast_data or 'gold' not in bonbast_data:
                return {}

            result = {}
            for item_id in item_ids:
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

    def get_all_prices(self, crypto_ids: List[str] = None,
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
            'usd_irr': None,
            'fiat_currencies': {},
            'gold_coins': {},
            'gold_items': {},
            'timestamp': datetime.now().isoformat()
        }

        # دریافت قیمت کریپتوها
        if crypto_ids:
            result['cryptos'] = self.get_crypto_prices(crypto_ids)

        # دریافت قیمت طلا
        if include_gold:
            result['gold'] = self.get_gold_price()

        # دریافت قیمت نقره
        if include_silver:
            result['silver'] = self.get_silver_price()

        # دریافت قیمت دلار
        if include_usd:
            result['usd_irr'] = self.get_usd_irr_price()

        # دریافت ارزهای فیات
        if fiat_currency_ids:
            result['fiat_currencies'] = self.get_fiat_currencies(fiat_currency_ids)

        # دریافت سکه‌های طلا
        if gold_coin_ids:
            result['gold_coins'] = self.get_gold_coins(gold_coin_ids)

        # دریافت آیتم‌های طلا
        if gold_item_ids:
            result['gold_items'] = self.get_gold_items(gold_item_ids)

        return result

    def format_price_message(self, prices: Dict) -> str:
        """
        فرمت کردن قیمت‌ها به صورت پیام تلگرام

        Args:
            prices: خروجی تابع get_all_prices

        Returns:
            str: پیام فرمت شده
        """
        lines = []
        lines.append("📊 گزارش قیمت‌های لحظه‌ای")
        lines.append("=" * 35)
        lines.append("")

        # ارزهای دیجیتال
        if prices.get('cryptos'):
            lines.append("🪙 ارزهای دیجیتال:")
            lines.append("")

            for crypto_id, data in prices['cryptos'].items():
                symbol = data['symbol']
                price = self.format_number(data['price'])
                change_24h = self.format_percentage(data['change_24h'])

                lines.append(f"▫️ {symbol}")
                lines.append(f"   قیمت: ${price}")
                lines.append(f"   تغییر 24h: {change_24h}")
                lines.append("")

        # طلا
        if prices.get('gold'):
            gold = prices['gold']
            lines.append(f"{gold['symbol']} طلا (اونس جهانی):")
            lines.append(f"   قیمت: ${self.format_number(gold['price'])}")
            if gold.get('change_7d', 0) != 0:
                lines.append(f"   تغییر 7d: {self.format_percentage(gold['change_7d'])}")
            lines.append("")

        # نقره
        if prices.get('silver'):
            silver = prices['silver']
            lines.append(f"{silver['symbol']} نقره (اونس جهانی):")
            lines.append(f"   قیمت: ${self.format_number(silver['price'])}")
            if silver.get('change_7d', 0) != 0:
                lines.append(f"   تغییر 7d: {self.format_percentage(silver['change_7d'])}")
            lines.append("")

        # دلار
        if prices.get('usd_irr'):
            usd = prices['usd_irr']
            lines.append(f"{usd['symbol']} دلار آمریکا:")
            lines.append(f"   قیمت: {self.format_number(usd['price'])} {usd['unit']}")
            lines.append("")

        # ارزهای فیات
        if prices.get('fiat_currencies'):
            lines.append("💱 ارزهای فیات:")
            lines.append("")

            for currency_id, data in prices['fiat_currencies'].items():
                symbol = data['symbol']
                name = data['name']
                buy = self.format_number(data['buy'])
                sell = self.format_number(data['sell'])

                lines.append(f"▫️ {symbol} {name}")
                lines.append(f"   خرید: {buy} تومان")
                lines.append(f"   فروش: {sell} تومان")
                lines.append("")

        # سکه‌های طلا
        if prices.get('gold_coins'):
            lines.append("🪙 سکه‌های طلا:")
            lines.append("")

            for coin_id, data in prices['gold_coins'].items():
                symbol = data['symbol']
                name = data['name']
                buy = self.format_number(data['buy'])
                sell = self.format_number(data['sell'])

                lines.append(f"{symbol} {name}")
                lines.append(f"   خرید: {buy} تومان")
                lines.append(f"   فروش: {sell} تومان")
                lines.append("")

        # آیتم‌های طلا
        if prices.get('gold_items'):
            lines.append("✨ طلا:")
            lines.append("")

            for item_id, data in prices['gold_items'].items():
                symbol = data['symbol']
                name = data['name']
                price = self.format_number(data['price'])
                unit = data['unit']

                lines.append(f"{symbol} {name}")
                lines.append(f"   قیمت: {price} {unit}")
                lines.append("")

        # زمان به‌روزرسانی
        lines.append("─" * 35)
        now = datetime.now()
        lines.append(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)
