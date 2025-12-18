"""
دریافت و خلاصه‌سازی اخبار کریپتو با استفاده از AI
"""
from datetime import datetime
from typing import Dict, List, Optional
import requests
import json
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


class NewsFetcher:
    """کلاس دریافت و پردازش اخبار"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fa,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        # استفاده از Ramzarz.news به دلیل داشتن RSS Feed
        self.ramzarz_rss_url = 'https://ramzarz.news/feed/rss/'
        self.ramzarz_url = 'https://ramzarz.news/'

    def _parse_persian_time(self, time_text: str) -> str:
        """
        تبدیل زمان فارسی به فرمت استاندارد

        Args:
            time_text: متن زمان به فارسی (مثلاً "۳ ساعت پیش")

        Returns:
            str: زمان به فرمت YYYY-MM-DD HH:MM
        """
        from datetime import timedelta
        import re

        now = datetime.now()

        # تبدیل اعداد فارسی به انگلیسی
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        time_text = time_text.translate(persian_to_english)

        # استخراج عدد
        number_match = re.search(r'(\d+)', time_text)
        if not number_match:
            return now.strftime('%Y-%m-%d %H:%M')

        number = int(number_match.group(1))

        # تشخیص نوع زمان
        if 'ساعت' in time_text or 'hour' in time_text:
            time_ago = now - timedelta(hours=number)
        elif 'روز' in time_text or 'day' in time_text:
            time_ago = now - timedelta(days=number)
        elif 'دقیقه' in time_text or 'minute' in time_text:
            time_ago = now - timedelta(minutes=number)
        else:
            time_ago = now

        return time_ago.strftime('%Y-%m-%d %H:%M')

    def fetch_crypto_news_from_ramzarz(self) -> Optional[List[Dict]]:
        """
        دریافت اخبار کریپتو از Ramzarz.news (با استفاده از RSS Feed)

        Returns:
            list: لیست اخبار یا None در صورت خطا
        """
        try:
            print("در حال دریافت اخبار از Ramzarz.news...")

            # دریافت RSS Feed
            # استفاده از requests.get مستقیم بجای session برای جلوگیری از مشکلات encoding
            response = requests.get(
                self.ramzarz_rss_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=10
            )
            response.raise_for_status()

            # پاک کردن BOM و whitespace اضافی
            content = response.content

            # حذف BOM اگر وجود داشت
            if content.startswith(b'\xef\xbb\xbf'):
                content = content[3:]

            # حذف whitespace قبل از XML
            content = content.lstrip()

            # پارس XML
            root = ET.fromstring(content)

            # پیدا کردن namespace (در صورت وجود)
            namespaces = {'content': 'http://purl.org/rss/1.0/modules/content/',
                         'dc': 'http://purl.org/dc/elements/1.1/'}

            news_list = []

            # پیدا کردن تمام آیتم‌های خبری
            for item in root.findall('.//item')[:20]:  # فقط 20 خبر اول
                try:
                    # استخراج عنوان
                    title_elem = item.find('title')
                    title = title_elem.text if title_elem is not None else ''

                    # استخراج لینک
                    link_elem = item.find('link')
                    url = link_elem.text if link_elem is not None else ''

                    # استخراج توضیحات/محتوا
                    desc_elem = item.find('description')
                    description = ''
                    if desc_elem is not None and desc_elem.text:
                        # حذف HTML tags از description
                        soup = BeautifulSoup(desc_elem.text, 'lxml')
                        description = soup.get_text(strip=True)[:200]  # 200 کاراکتر اول

                    # اگر description خالی بود، از content:encoded استفاده کن
                    if not description:
                        content_elem = item.find('content:encoded', namespaces)
                        if content_elem is not None and content_elem.text:
                            soup = BeautifulSoup(content_elem.text, 'lxml')
                            description = soup.get_text(strip=True)[:200]

                    # استخراج زمان انتشار
                    pub_date_elem = item.find('pubDate')
                    published_at = datetime.now().strftime('%Y-%m-%d %H:%M')

                    if pub_date_elem is not None and pub_date_elem.text:
                        try:
                            # فرمت RSS: Mon, 07 Dec 2025 12:00:00 +0000
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pub_date_elem.text)
                            published_at = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            pass

                    # استخراج دسته‌بندی
                    categories = []
                    for cat_elem in item.findall('category'):
                        if cat_elem.text:
                            categories.append(cat_elem.text)

                    # ساخت آبجکت خبر
                    news_obj = {
                        'title': title.strip(),
                        'source': 'Ramzarz',
                        'body': description or title,  # اگر توضیحات نبود، از عنوان استفاده کن
                        'url': url.strip(),
                        'published_at': published_at,
                        'categories': categories
                    }

                    if title and url:  # فقط اگر عنوان و لینک داشت
                        news_list.append(news_obj)

                except Exception as e:
                    print(f"خطا در پردازش یک خبر: {e}")
                    continue

            print(f"✅ {len(news_list)} خبر از Ramzarz دریافت شد")
            return news_list

        except requests.exceptions.RequestException as e:
            print(f"خطا در اتصال به Ramzarz: {e}")
            return None
        except ET.ParseError as e:
            print(f"خطا در پارس XML: {e}")
            return None
        except Exception as e:
            print(f"خطا در دریافت اخبار از Ramzarz: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_crypto_news_from_coingecko(self) -> Optional[List[Dict]]:
        """
        دریافت اخبار کریپتو - این متد حالا از Ramzarz.news استفاده می‌کند

        Returns:
            list: لیست اخبار یا None در صورت خطا
        """
        # استفاده از RSS Feed از Ramzarz.news
        return self.fetch_crypto_news_from_ramzarz()

    def categorize_news(self, news_items: List[Dict]) -> Dict:
        """
        دسته‌بندی اخبار به صورت ساده

        Args:
            news_items: لیست اخبار دریافتی

        Returns:
            dict: اخبار دسته‌بندی شده
        """
        categorized = {
            'global_economy': [],
            'crypto': [],
            'security': [],
            'highlight': None
        }

        security_keywords = ['hack', 'hacked', 'exploit', 'vulnerability', 'breach', 'scam', 'rug pull']
        economy_keywords = ['fed', 'interest rate', 'inflation', 'economy', 'recession', 'gdp', 'dollar index']

        for item in news_items:
            title = item.get('title', '').lower()
            body = item.get('body', '').lower()

            news_obj = {
                'title': item.get('title', ''),
                'source': item.get('source', ''),
                'url': item.get('url', ''),
                'published_at': item.get('published_at', '')
            }

            # چک کردن امنیت
            if any(keyword in title or keyword in body for keyword in security_keywords):
                categorized['security'].append(news_obj)
            # چک کردن اقتصاد جهانی
            elif any(keyword in title or keyword in body for keyword in economy_keywords):
                categorized['global_economy'].append(news_obj)
            # بقیه کریپتو
            else:
                categorized['crypto'].append(news_obj)

        # انتخاب highlight (اولین خبر مهم)
        if news_items:
            categorized['highlight'] = news_items[0].get('title', '')

        return categorized

    def format_news_message(self, news_data: Dict) -> str:
        """
        فرمت کردن اخبار به صورت پیام تلگرام

        Args:
            news_data: داده‌های خبری دریافت شده

        Returns:
            str: پیام فرمت شده
        """
        lines = []
        lines.append("📰 خلاصه اخبار کریپتو امروز")
        lines.append("─" * 3)
        lines.append("")

        # لیست لینک‌ها برای نمایش در انتها
        links = []
        link_counter = 1

        # دریافت بخش‌های مختلف خبر
        if 'global_economy' in news_data and news_data['global_economy']:
            lines.append("🌍 اقتصاد جهانی")
            # فقط 3 تا اول
            for item in news_data['global_economy'][:3]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'

                # اضافه کردن شماره لینک
                url = item.get('url', '')
                if url:
                    lines.append(f" • {title} [{link_counter}]")
                    links.append(f"[{link_counter}] {url}")
                    link_counter += 1
                else:
                    lines.append(f" • {title}")

                # اضافه کردن تاریخ و منبع
                source = item.get('source', '')
                published_at = item.get('published_at', '')

                if published_at and source:
                    lines.append(f"   📅 {published_at} | 📰 {source}")
            lines.append("")

        if 'crypto' in news_data and news_data['crypto']:
            lines.append("₿ کریپتو")
            # فقط 5 تا اول
            for item in news_data['crypto'][:5]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'

                # اضافه کردن شماره لینک
                url = item.get('url', '')
                if url:
                    lines.append(f" • {title} [{link_counter}]")
                    links.append(f"[{link_counter}] {url}")
                    link_counter += 1
                else:
                    lines.append(f" • {title}")

                # اضافه کردن تاریخ و منبع
                source = item.get('source', '')
                published_at = item.get('published_at', '')

                if published_at and source:
                    lines.append(f"   📅 {published_at} | 📰 {source}")
            lines.append("")

        if 'security' in news_data and news_data['security']:
            lines.append("🔒 امنیت")
            # فقط 2 تا اول
            for item in news_data['security'][:2]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'

                # اضافه کردن شماره لینک
                url = item.get('url', '')
                if url:
                    lines.append(f" • {title} [{link_counter}]")
                    links.append(f"[{link_counter}] {url}")
                    link_counter += 1
                else:
                    lines.append(f" • {title}")

                # اضافه کردن تاریخ و منبع
                source = item.get('source', '')
                published_at = item.get('published_at', '')

                if published_at and source:
                    lines.append(f"   📅 {published_at} | 📰 {source}")
            lines.append("")

        if 'highlight' in news_data and news_data['highlight']:
            lines.append("💡 نکته روز")
            highlight = news_data['highlight']
            if len(highlight) > 100:
                highlight = highlight[:97] + '...'
            lines.append(f" • {highlight}")
            lines.append("")

        # لینک‌های منابع
        if links:
            lines.append("─" * 3)
            lines.append("🔗 منابع خبری:")
            for link in links:
                lines.append(link)
            lines.append("")

        # زمان به‌روزرسانی
        lines.append("─" * 3)
        now = datetime.now()
        lines.append(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("ارزَلان دستیار اطلاع‌رسانی قیمت")
        lines.append("@arzzalanbot")

        return "\n".join(lines)

    def get_ai_prompt(self) -> str:
        """
        ساخت prompt برای AI جهت خلاصه‌سازی اخبار

        Returns:
            str: prompt آماده برای ارسال به AI
        """
        prompt = """
لطفاً اخبار مهم کریپتو و بازارهای مالی امروز را به صورت خلاصه و دسته‌بندی شده استخراج کن.

فرمت خروجی باید به صورت JSON باشد:
{
  "global_economy": [
    "خبر کوتاه 1 درباره اقتصاد جهانی",
    "خبر کوتاه 2 درباره اقتصاد جهانی"
  ],
  "crypto": [
    "خبر کوتاه 1 درباره کریپتو (با ذکر دلیل اگر مهمه)",
    "خبر کوتاه 2 درباره کریپتو"
  ],
  "security": [
    "هشدار امنیتی یا هک (در صورت وجود)"
  ],
  "highlight": "نکته مهم روز که معامله‌گران باید بدونند"
}

نکات مهم:
- هر خبر باید خیلی خلاصه باشه (حداکثر 15-20 کلمه)
- فقط اخبار مهم و تأثیرگذار
- اگه اخبار امنیتی یا هک مهمی نیست، security رو خالی بذار []
- زبان: فارسی ساده و روان
- بدون emoji اضافی
- عدد‌ها رو واضح بنویس (مثلاً: 2.5% یا 50M دلار)

فقط JSON برگردون، بدون توضیح اضافی.
"""
        return prompt
