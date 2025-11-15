import asyncio
from playwright.async_api import async_playwright
import requests
import json

class BonbastScraper:
    def __init__(self):
        self.url = 'https://www.bonbast.com/'
        self.api_url = 'https://www.bonbast.com/json'
        
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
            
            # صبر برای request (حداکثر 70 ثانیه)
            print("⏳ صبر برای request...")
            for i in range(70):
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
        """گرفتن نرخ ارز"""
        param, cookies = await self.capture_param_and_cookies()
        
        if not param or not cookies:
            print("❌ نتونستم param/cookies رو بگیرم!")
            return None
        
        return self.fetch_rates(param, cookies)

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