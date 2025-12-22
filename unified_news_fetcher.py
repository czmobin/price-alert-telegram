"""
سیستم خلاصه اخبار یکپارچه - ترکیب تمام منابع خبری
"""
from typing import Optional
from news_fetcher import NewsFetcher
from forex_news_fetcher import ForexNewsFetcher
from security_news_fetcher import SecurityNewsFetcher
from constants import BotConstants
from jdatetime import datetime as jalalidatetime


class UnifiedNewsFetcher:
    """کلاس ترکیب و نمایش یکپارچه اخبار"""

    def __init__(self):
        self.crypto_fetcher = NewsFetcher()
        self.forex_fetcher = ForexNewsFetcher()
        self.security_fetcher = SecurityNewsFetcher()

    async def get_unified_news(self) -> str:
        """
        دریافت و ترکیب تمام اخبار از منابع مختلف

        Returns:
            str: پیام فرمت شده با تمام اخبار
        """
        lines = []
        lines.append("📰خلاصه مهم‌ترین اخبار روز با ارزَلان:")
        lines.append("")

        # 1. اخبار اقتصاد جهانی
        try:
            forex_news = await self.forex_fetcher.get_daily_news()
            if forex_news and isinstance(forex_news, str):
                # استخراج فقط قسمت اخبار (بدون header و footer)
                forex_lines = forex_news.split('\n')
                # پیدا کردن ایندکس شروع اخبار
                start_idx = 0
                for i, line in enumerate(forex_lines):
                    if '🌍' in line or 'اقتصاد جهانی' in line:
                        start_idx = i
                        break

                # پیدا کردن ایندکس پایان اخبار (قبل از footer)
                end_idx = len(forex_lines)
                for i, line in enumerate(forex_lines):
                    if '─' * 20 in line and i > start_idx + 5:
                        end_idx = i
                        break

                # اضافه کردن اخبار اقتصاد جهانی
                lines.append("🌍 اقتصاد جهانی")
                lines.append("")

                # فیلتر کردن اخبار واقعی
                news_added = False
                for line in forex_lines[start_idx+1:end_idx]:
                    line = line.strip()
                    # فقط خطوطی که شامل محتوای خبر هستند
                    if line and not line.startswith('─') and not line.startswith('منبع:'):
                        # حذف خطوط header اضافی
                        if 'اخبار مهم روز' not in line and 'ForexFactory' not in line:
                            lines.append(line)
                            news_added = True

                if not news_added:
                    lines.append("• اخبار اقتصاد جهانی در دسترس نیست")

                lines.append("")
                lines.append("--")

        except Exception as e:
            print(f"خطا در دریافت اخبار اقتصاد جهانی: {e}")
            lines.append("🌍 اقتصاد جهانی")
            lines.append("")
            lines.append("• خطا در دریافت اخبار")
            lines.append("")
            lines.append("--")

        # 2. اخبار کریپتو
        try:
            crypto_news_items = self.crypto_fetcher.fetch_crypto_news_from_coingecko()

            if crypto_news_items and len(crypto_news_items) > 0:
                lines.append("₿ کریپتو")
                lines.append("")

                # نمایش تا 4 خبر اول
                for item in crypto_news_items[:4]:
                    title = item.get('title', '')
                    source = item.get('source', '')
                    url = item.get('url', '')

                    if title:
                        # محدود کردن طول تیتر
                        if len(title) > 100:
                            title = title[:97] + '...'

                        lines.append(f"• {title}")

                        # اضافه کردن زمان و منبع
                        published_at = item.get('published_at', '')
                        time_part = published_at.split()[1] if ' ' in published_at else published_at
                        if time_part and source:
                            lines.append(f"🕒 {time_part} — {source} ({url})")
                        lines.append("")

                lines.append("--")

            else:
                lines.append("₿ کریپتو")
                lines.append("")
                lines.append("• خبر جدیدی موجود نیست")
                lines.append("")
                lines.append("--")

        except Exception as e:
            print(f"خطا در دریافت اخبار کریپتو: {e}")
            lines.append("₿ کریپتو")
            lines.append("")
            lines.append("• خطا در دریافت اخبار")
            lines.append("")
            lines.append("--")

        # 3. اخبار امنیت بازار (اختیاری - فقط اگر خبری باشد)
        try:
            security_news = self.security_fetcher.fetch_security_news()

            if security_news and len(security_news) > 0:
                lines.append("🔒 امنیت بازار")
                lines.append("")

                # نمایش تا 2 خبر اول
                for item in security_news[:2]:
                    title = item.get('title', '')
                    if title:
                        if len(title) > 100:
                            title = title[:97] + '...'
                        lines.append(f"• {title}")
                        lines.append("")

                lines.append("--")

        except Exception as e:
            print(f"خطا در دریافت اخبار امنیتی: {e}")
            # اخبار امنیتی اجباری نیست، پس در صورت خطا نمایش نمی‌دهیم

        # 4. نکته روز (از اخبار کریپتو)
        try:
            if crypto_news_items and len(crypto_news_items) > 0:
                highlight = crypto_news_items[0].get('title', '')
                if highlight:
                    if len(highlight) > 120:
                        highlight = highlight[:117] + '...'

                    lines.append("💡 نکته روز ارزَلان")
                    lines.append("")
                    lines.append(f" • {highlight}")
                    lines.append("")
        except Exception as e:
            print(f"خطا در تنظیم نکته روز: {e}")

        # Footer استاندارد
        lines.append("")
        lines.append("─" * 35)
        lines.append(BotConstants.get_message_footer(include_divider=False))

        return "\n".join(lines)

    async def get_news_summary(self) -> str:
        """
        نام مستعار برای get_unified_news (برای سازگاری با کدهای قدیمی)
        """
        return await self.get_unified_news()
