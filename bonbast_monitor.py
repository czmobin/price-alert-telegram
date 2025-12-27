import asyncio
from playwright.async_api import async_playwright
import requests
import json
from datetime import datetime, timedelta

class BonbastScraper:
    def __init__(self):
        self.url = 'https://www.bonbast.com/'
        self.api_url = 'https://www.bonbast.com/json'
        # Cache برای param و cookies (30 دقیقه اعتبار)
        self._cached_param = None
        self._cached_cookies = None
        self._cache_time = None
        self._cache_duration = timedelta(minutes=30)

    async def capture_param_and_cookies(self):
        """فقط گرفتن param و cookies از مرورگر"""
        print("🌐 باز کردن مرورگر...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            captured_data = {'param': None}
            
            # Intercept کردن Request
            async def handle_request(request):
                if '/json' in request.url and request.method == 'POST':
                    post_data = request.post_data
                    if post_data and 'param=' in post_data:
                        captured_data['param'] = post_data.replace('param=', '')
                        print(f"✅ param گرفته شد")
            
            page.on('request', handle_request)
            
            # رفتن به صفحه
            await page.goto(self.url, wait_until='domcontentloaded')
            
            # صبر برای request (حداکثر 15 ثانیه - کاهش یافته برای سرعت بیشتر)
            print("⏳ صبر برای request...")
            for i in range(15):
                if captured_data['param']:
                    break
                await asyncio.sleep(1)
            
            # گرفتن cookies
            cookies_dict = None
            if captured_data['param']:
                cookies = await context.cookies()
                cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                print(f"✅ {len(cookies_dict)} کوکی دریافت شد")
            
            await browser.close()
            
            return captured_data['param'], cookies_dict
    
    def fetch_rates(self, param, cookies):
        """ارسال request با requests"""
        
        cookie_string = '; '.join([f'{k}={v}' for k, v in cookies.items()])
        
        headers = {
            'authority': 'www.bonbast.com',
            'method': 'POST',
            'path': '/json',
            'scheme': 'https',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'cookie': cookie_string,
            'origin': 'https://www.bonbast.com',
            'priority': 'u=1, i',
            'referer': 'https://www.bonbast.com/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        data = f'param={param}'
        
        try:
            print("📡 ارسال request...")
            response = requests.post(self.api_url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ دیتا دریافت شد!")
                return response.json()
            else:
                print(f"❌ خطا {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ خطا: {e}")
            return None
    
    async def get_rates(self):
        """گرفتن نرخ ارز با استفاده از cache"""
        # چک کردن cache
        if self._is_cache_valid():
            print("⚡ استفاده از cache (سریع!)")
            rates = self.fetch_rates(self._cached_param, self._cached_cookies)
            if rates:
                return rates
            # اگر cache کار نکرد، دوباره بگیر
            print("⚠️ cache منقضی شده، دریافت مجدد...")

        # دریافت param و cookies جدید
        param, cookies = await self.capture_param_and_cookies()

        if not param or not cookies:
            print("❌ نتونستم param/cookies رو بگیرم!")
            return None

        # ذخیره در cache
        self._cached_param = param
        self._cached_cookies = cookies
        self._cache_time = datetime.now()

        return self.fetch_rates(param, cookies)

    def _is_cache_valid(self) -> bool:
        """بررسی معتبر بودن cache"""
        if not self._cached_param or not self._cached_cookies or not self._cache_time:
            return False

        # چک کردن زمان
        elapsed = datetime.now() - self._cache_time
        return elapsed < self._cache_duration

    def extract_currency_data(self, rates: dict) -> dict:
        """
        استخراج و دسته‌بندی داده‌های bonbast

        Returns:
            dict: {
                'currencies': {...},  # ارزهای فیات
                'coins': {...},       # سکه‌ها
                'gold': {...},        # طلا
                'crypto': {...},      # ارزهای دیجیتال
                'market': {...}       # بازار بورس و...
            }
        """
        if not rates:
            return None

        result = {
            'currencies': {},
            'coins': {},
            'gold': {},
            'crypto': {},
            'market': {},
            'timestamp': rates.get('created', '')
        }

        # ارزهای فیات - نرخ خرید (1) و فروش (2)
        fiat_currencies = {
            'usd': 'دلار آمریکا',
            'eur': 'یورو',
            'gbp': 'پوند انگلیس',
            'chf': 'فرانک سوئیس',
            'cad': 'دلار کانادا',
            'aud': 'دلار استرالیا',
            'sek': 'کرون سوئد',
            'nok': 'کرون نروژ',
            'dkk': 'کرون دانمارک',
            'jpy': 'ین ژاپن',
            'cny': 'یوان چین',
            'try': 'لیر ترکیه',
            'rub': 'روبل روسیه',
            'inr': 'روپیه هند',
            'aed': 'درهم امارات',
            'sar': 'ریال عربستان',
            'qar': 'ریال قطر',
            'kwd': 'دینار کویت',
            'omr': 'ریال عمان',
            'bhd': 'دینار بحرین',
            'iqd': 'دینار عراق',
            'myr': 'رینگیت مالزی',
            'sgd': 'دلار سنگاپور',
            'hkd': 'دلار هنگ کنگ',
            'azn': 'منات آذربایجان',
            'amd': 'درام ارمنستان',
            'afn': 'افغانی افغانستان',
            'thb': 'بات تایلند'
        }

        for currency, name in fiat_currencies.items():
            buy_key = f'{currency}1'
            sell_key = f'{currency}2'
            if buy_key in rates and sell_key in rates:
                try:
                    result['currencies'][currency] = {
                        'name': name,
                        'buy': int(rates[buy_key]),
                        'sell': int(rates[sell_key]),
                        'symbol': currency.upper()
                    }
                except (ValueError, TypeError):
                    continue

        # سکه‌های طلا
        coins_map = {
            'azadi1': {'name': 'سکه بهار آزادی', 'type': 'full'},
            'azadi1_2': {'name': 'نیم سکه', 'type': 'half'},
            'azadi1_4': {'name': 'ربع سکه', 'type': 'quarter'},
            'azadi1g': {'name': 'یک گرمی', 'type': 'gram'},
            'emami1': {'name': 'سکه امامی', 'type': 'emami'}
        }

        for coin_key, coin_info in coins_map.items():
            buy_key = coin_key
            sell_key = f'{coin_key}2'
            if buy_key in rates and sell_key in rates:
                try:
                    result['coins'][coin_key] = {
                        'name': coin_info['name'],
                        'type': coin_info['type'],
                        'buy': int(rates[buy_key]),
                        'sell': int(rates[sell_key])
                    }
                except (ValueError, TypeError):
                    continue

        # طلا
        gold_items = {
            'gol18': {'name': 'طلای ۱۸ عیار (گرم)', 'unit': 'تومان'},
            'mithqal': {'name': 'مثقال طلا', 'unit': 'تومان'},
            'ounce': {'name': 'اونس طلا', 'unit': 'دلار'}
        }

        for gold_key, gold_info in gold_items.items():
            if gold_key in rates:
                try:
                    result['gold'][gold_key] = {
                        'name': gold_info['name'],
                        'price': float(rates[gold_key]),
                        'unit': gold_info['unit']
                    }
                except (ValueError, TypeError):
                    continue

        # ارزهای دیجیتال
        if 'bitcoin' in rates:
            try:
                result['crypto']['bitcoin'] = {
                    'name': 'بیت کوین',
                    'price': float(rates['bitcoin']),
                    'symbol': 'BTC'
                }
            except (ValueError, TypeError):
                pass

        # بازار
        if 'bourse' in rates:
            try:
                result['market']['bourse'] = {
                    'name': 'شاخص بورس',
                    'value': float(rates['bourse'])
                }
            except (ValueError, TypeError):
                pass

        return result

async def main():
    scraper = BonbastScraper()
    rates = await scraper.get_rates()
    
    if rates:
        print("\n" + "="*60)
        print("💰 نرخ‌های ارز:")
        print("="*60)
        print(json.dumps(rates, indent=2, ensure_ascii=False))
    else:
        print("❌ نتونستم نرخ‌ها رو بگیرم!")

if __name__ == '__main__':
    asyncio.run(main())