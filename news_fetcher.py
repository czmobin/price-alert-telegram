"""
دریافت و خلاصه‌سازی اخبار کریپتو با استفاده از AI
"""
from datetime import datetime
from typing import Dict, List, Optional
import requests
import json
import xml.etree.ElementTree as ET


class NewsFetcher:
    """کلاس دریافت و پردازش اخبار"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_crypto_news_from_coingecko(self) -> Optional[List[Dict]]:
        """
        دریافت اخبار کریپتو

        نکته: برای استفاده واقعی، باید یک API key رایگان از CryptoPanic یا NewsAPI دریافت کنید.
        این نسخه داده‌های نمونه برمی‌گرداند برای نمایش ساختار.

        Returns:
            list: لیست اخبار یا None در صورت خطا
        """
        try:
            # TODO: برای production، از یکی از این API ها استفاده کن:
            # 1. CryptoPanic API (نیاز به API key رایگان)
            # 2. NewsAPI.org (50 request روزانه رایگان)
            # 3. CoinGecko (محدودیت rate limit داره)

            # برای الان، داده نمونه برمی‌گردونیم
            sample_news = [
                {
                    'title': 'Bitcoin Surges Past $85,000 as Institutional Adoption Grows',
                    'source': 'CoinDesk',
                    'body': 'fed interest rate bitcoin institutional adoption',
                    'url': ''
                },
                {
                    'title': 'Ethereum Network Completes Major Upgrade, Gas Fees Drop 40%',
                    'source': 'CoinTelegraph',
                    'body': 'ethereum upgrade scaling layer 2',
                    'url': ''
                },
                {
                    'title': 'Federal Reserve Hints at Potential Rate Cuts in Q2 2025',
                    'source': 'Bloomberg',
                    'body': 'federal reserve interest rate inflation economy',
                    'url': ''
                },
                {
                    'title': 'Solana DeFi Protocol Reports $12M Exploit',
                    'source': 'The Block',
                    'body': 'solana hack exploit vulnerability defi protocol',
                    'url': ''
                },
                {
                    'title': 'Tether Reaches $120B Market Cap, Dominates Stablecoin Market',
                    'source': 'CoinDesk',
                    'body': 'usdt tether stablecoin market cap',
                    'url': ''
                },
                {
                    'title': 'SEC Approves New Bitcoin ETF Applications',
                    'source': 'Reuters',
                    'body': 'sec bitcoin etf approval institutional',
                    'url': ''
                }
            ]

            return sample_news

        except Exception as e:
            print(f"خطا در دریافت اخبار: {e}")
            return None

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

            # چک کردن امنیت
            if any(keyword in title or keyword in body for keyword in security_keywords):
                categorized['security'].append({
                    'title': item.get('title', ''),
                    'source': item.get('source', '')
                })
            # چک کردن اقتصاد جهانی
            elif any(keyword in title or keyword in body for keyword in economy_keywords):
                categorized['global_economy'].append({
                    'title': item.get('title', ''),
                    'source': item.get('source', '')
                })
            # بقیه کریپتو
            else:
                categorized['crypto'].append({
                    'title': item.get('title', ''),
                    'source': item.get('source', '')
                })

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
        lines.append("─" * 35)
        lines.append("")

        # دریافت بخش‌های مختلف خبر
        if 'global_economy' in news_data and news_data['global_economy']:
            lines.append("🌍 اقتصاد جهانی")
            # فقط 3 تا اول
            for item in news_data['global_economy'][:3]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'
                lines.append(f" • {title}")
            lines.append("")

        if 'crypto' in news_data and news_data['crypto']:
            lines.append("₿ کریپتو")
            # فقط 5 تا اول
            for item in news_data['crypto'][:5]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'
                lines.append(f" • {title}")
            lines.append("")

        if 'security' in news_data and news_data['security']:
            lines.append("🔒 امنیت")
            # فقط 2 تا اول
            for item in news_data['security'][:2]:
                title = item['title']
                if len(title) > 80:
                    title = title[:77] + '...'
                lines.append(f" • {title}")
            lines.append("")

        if 'highlight' in news_data and news_data['highlight']:
            lines.append("💡 نکته روز")
            highlight = news_data['highlight']
            if len(highlight) > 100:
                highlight = highlight[:97] + '...'
            lines.append(f" • {highlight}")
            lines.append("")

        # زمان به‌روزرسانی
        lines.append("─" * 35)
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
