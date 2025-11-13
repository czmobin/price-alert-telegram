"""
دریافت قیمت‌های ارزهای دیجیتال، طلا، نقره و دلار
"""
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from config import COINGECKO_API, CRYPTO_SYMBOLS


class PriceFetcher:
    """کلاس دریافت قیمت‌ها از APIهای مختلف"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

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
        دریافت قیمت ارزهای دیجیتال از CoinGecko

        Returns:
            dict: {'bitcoin': {'price': 45000, 'change_7d': 5.2, 'symbol': 'BTC'}, ...}
        """
        try:
            # تبدیل لیست به رشته جدا شده با کاما
            ids_string = ','.join(crypto_ids)

            url = f"{COINGECKO_API}/simple/price"
            params = {
                'ids': ids_string,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_7d_change': 'true'
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
                        'change_7d': crypto_data.get('usd_7d_change', 0),
                        'symbol': CRYPTO_SYMBOLS.get(crypto_id, crypto_id.upper())
                    }

            return result

        except Exception as e:
            print(f"خطا در دریافت قیمت کریپتو: {e}")
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
                if isinstance(data, dict) and 'data' in data:
                    price_data = data['data']
                    current_price = float(price_data.get('p', 0)) / 10  # تبدیل به تومان

                    return {
                        'price': current_price,
                        'change_24h': 0,  # این API تغییرات را ندارد
                        'change_7d': 0,
                        'unit': 'تومان',
                        'symbol': '💵'
                    }

            # روش جایگزین: استفاده از API bonbast (غیررسمی)
            return self._get_usd_from_bonbast()

        except Exception as e:
            print(f"خطا در دریافت قیمت دلار: {e}")
            return self._get_usd_from_bonbast()

    def _get_usd_from_bonbast(self) -> Optional[Dict]:
        """دریافت قیمت دلار از Bonbast (روش جایگزین)"""
        try:
            url = "https://www.bonbast.com/json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                usd_sell = float(data.get('usd', {}).get('sell', 0)) / 10

                return {
                    'price': usd_sell,
                    'change_24h': 0,
                    'change_7d': 0,
                    'unit': 'تومان',
                    'symbol': '💵'
                }
            return None

        except Exception as e:
            print(f"خطا در دریافت دلار از Bonbast: {e}")
            return None

    def get_all_prices(self, crypto_ids: List[str], include_gold: bool = True,
                      include_silver: bool = True, include_usd: bool = True) -> Dict:
        """
        دریافت تمام قیمت‌ها

        Returns:
            dict: {
                'cryptos': {...},
                'gold': {...},
                'silver': {...},
                'usd_irr': {...}
            }
        """
        result = {
            'cryptos': {},
            'gold': None,
            'silver': None,
            'usd_irr': None,
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
                change_7d = self.format_percentage(data['change_7d'])

                lines.append(f"▫️ {symbol}")
                lines.append(f"   قیمت: ${price}")
                lines.append(f"   تغییر 24h: {change_24h}")
                lines.append(f"   تغییر 7d: {change_7d}")
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

        # زمان به‌روزرسانی
        lines.append("─" * 35)
        now = datetime.now()
        lines.append(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)
