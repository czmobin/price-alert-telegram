"""
دریافت و فرمت‌کردن اخبار امنیت کریپتو از arzdigital.com
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from datetime import datetime


class SecurityNewsFetcher:
    """کلاس دریافت و پردازش اخبار امنیتی کریپتو"""

    def __init__(self):
        self.base_url = "https://arzdigital.com/breaking/security/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fa,en-US;q=0.7,en;q=0.3',
        })

    def fetch_security_news(self) -> Optional[List[Dict]]:
        """
        دریافت اخبار امنیتی از arzdigital.com

        Returns:
            list: لیست اخبار یا None در صورت خطا
        """
        try:
            print("در حال دریافت اخبار امنیتی از arzdigital.com...")

            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            news_list = []

            # پیدا کردن آیتم‌های خبری
            # معمولاً در article یا div با کلاس مشخص هستند
            articles = soup.find_all('article', limit=15)

            if not articles:
                # تلاش جایگزین: پیدا کردن div های خبری
                articles = soup.find_all('div', class_=['post', 'news-item', 'article-item'], limit=15)

            for article in articles:
                try:
                    # استخراج عنوان
                    title_elem = article.find(['h2', 'h3', 'h4', 'a'])
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    if not title:
                        continue

                    # استخراج لینک
                    link = None
                    link_elem = article.find('a', href=True)
                    if link_elem:
                        link = link_elem.get('href', '')
                        if link and not link.startswith('http'):
                            link = f"https://arzdigital.com{link}"

                    # استخراج توضیحات
                    desc_elem = article.find(['p', 'div'], class_=['excerpt', 'summary', 'description'])
                    description = ''
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:200]

                    # استخراج زمان (اگر موجود باشد)
                    time_elem = article.find('time')
                    published_at = datetime.now().strftime('%Y-%m-%d')
                    if time_elem:
                        published_at = time_elem.get_text(strip=True) or published_at

                    news_obj = {
                        'title': title,
                        'url': link or self.base_url,
                        'description': description,
                        'published_at': published_at
                    }

                    news_list.append(news_obj)

                except Exception as e:
                    print(f"خطا در پردازش یک خبر: {e}")
                    continue

            print(f"✅ {len(news_list)} خبر امنیتی دریافت شد")
            return news_list if news_list else None

        except requests.exceptions.RequestException as e:
            print(f"خطا در اتصال به arzdigital.com: {e}")
            return None
        except Exception as e:
            print(f"خطا در دریافت اخبار امنیتی: {e}")
            import traceback
            traceback.print_exc()
            return None

    def format_security_news_message(self, news_items: List[Dict]) -> str:
        """
        فرمت کردن اخبار امنیتی به صورت پیام تلگرام

        Args:
            news_items: لیست اخبار دریافتی

        Returns:
            str: پیام فرمت شده
        """
        lines = []
        lines.append("🔒 *اخبار امنیت کریپتو*")
        lines.append("─" * 35)
        lines.append("")

        if not news_items:
            lines.append("⚠️ اخبار امنیتی موجود نیست.")
        else:
            # لیست لینک‌ها برای نمایش در انتها
            links = []
            link_counter = 1

            # نمایش تا 10 خبر اول
            for item in news_items[:10]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'

                url = item.get('url', '')
                if url:
                    lines.append(f"🔸 {title} [{link_counter}]")
                    links.append(f"[{link_counter}] {url}")
                    link_counter += 1
                else:
                    lines.append(f"🔸 {title}")

                # اضافه کردن توضیحات مختصر (اگر موجود باشد)
                description = item.get('description', '')
                if description and len(description) > 20:
                    desc_short = description[:60] + '...' if len(description) > 60 else description
                    lines.append(f"   💬 {desc_short}")

                published_at = item.get('published_at', '')
                if published_at:
                    lines.append(f"   📅 {published_at}")

                lines.append("")

            # لینک‌های منابع
            if links:
                lines.append("─" * 35)
                lines.append("🔗 منابع خبری:")
                for link in links:
                    lines.append(link)
                lines.append("")

        # زمان به‌روزرسانی
        lines.append("─" * 35)
        now = datetime.now()
        lines.append(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("منبع: arzdigital.com")
        lines.append("")
        lines.append("ارزَلان دستیار اطلاع‌رسانی قیمت")
        lines.append("@arzzalanbot")

        return "\n".join(lines)

    def get_security_news(self) -> Optional[str]:
        """
        دریافت و فرمت کردن اخبار امنیتی

        Returns:
            str یا None: پیام فرمت شده
        """
        news_items = self.fetch_security_news()

        if not news_items:
            return """🔒 *اخبار امنیت کریپتو*

⚠️ متأسفانه در حال حاضر نتوانستیم اخبار امنیتی را دریافت کنیم.

🔗 می‌توانید مستقیماً از منبع مشاهده کنید:
https://arzdigital.com/breaking/security/

─────────────────────────────
ارزَلان دستیار اطلاع‌رسانی قیمت
@arzzalanbot"""

        return self.format_security_news_message(news_items)
