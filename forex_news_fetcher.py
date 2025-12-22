"""
دریافت و فرمت‌کردن اخبار اقتصاد جهانی از فارکس فکتوری
"""
import asyncio
import datetime
import httpx
from playwright.async_api import async_playwright
from typing import Optional, List, Dict
import os
from constants import BotConstants


class ForexNewsFetcher:
    """کلاس دریافت و پردازش اخبار اقتصاد جهانی"""

    def __init__(self):
        self.base_url = "https://forexfactory.live/"
        self.api_base = "https://requests.forexfactory.live/api/calendars/events"
        self.x_signature = None
        # استفاده از متغیر محیطی برای فعال/غیرفعال کردن Playwright
        self.use_playwright = os.getenv('USE_PLAYWRIGHT', 'false').lower() == 'true'

    def get_news_color(self, impact: str) -> str:
        """
        دریافت رنگ برای سطح تاثیر خبر

        Args:
            impact: سطح تاثیر (high, mid, low)

        Returns:
            str: ایموجی رنگ مربوطه
        """
        if impact == "high":
            return "🔴"
        elif impact == "mid":
            return "🟡"
        elif impact == "low":
            return "⚪"
        return "⚫"

    def format_event(self, event: Dict, details: Optional[Dict] = None) -> str:
        """
        فرمت کردن یک رویداد خبری

        Args:
            event: داده‌های رویداد
            details: جزئیات اضافی (اختیاری)

        Returns:
            str: متن فرمت شده خبر
        """
        e = event.get("event", {})

        text = f"""
*{self.get_news_color(event.get('impact'))} {event.get('currency_symbol','')} {event.get('time','')}*

📌 *{e.get('event_name_fa','')}* ({e.get('event_name','')})
📊 تاثیر: *{str(event.get('impact')).upper() or e.get('impact_metals') or 'N/A'}*
🔹 فعلی: {event.get('actual','')}
🔸 پیش‌بینی: {event.get('forecast','')}
⬅️ قبلی: {event.get('previous','')}
📝 توضیح: {e.get('measures','')}
🔗 [لینک منبع]({e.get('source_link','')})
🗓️ انتشار بعدی: {event.get('next_release','')}
"""

        if details:
            text += f"""
🤺 چرا مهم است: {details.get("why_trader_cares","")}
📒 نکات: {details.get("ff_note","")}
📌 اثر معمول: {details.get("usual_effect","")}
"""
        return text.strip()

    async def get_x_signature(self):
        """
        استخراج x-signature از سایت با استفاده از Playwright
        """
        if self.x_signature:
            return  # اگر قبلاً دریافت شده، دوباره دریافت نکن

        # بررسی اینکه آیا Playwright فعال است یا نه
        if not self.use_playwright:
            print("⚠️ Playwright غیرفعال است. برای فعال‌سازی متغیر USE_PLAYWRIGHT=true را تنظیم کنید.")
            return

        signature_event = asyncio.Event()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()

                async def log_request(request):
                    if self.x_signature:
                        return
                    if "api/calendars/events" in request.url:
                        try:
                            headers = await request.all_headers()
                            sig = headers.get("x-signature")
                            if sig:
                                self.x_signature = sig
                                print(f"\n✅ x-signature دریافت شد: {self.x_signature}")
                                signature_event.set()
                        except Exception as e:
                            print(f"خطا در دریافت headers: {e}")

                page.on("request", log_request)

                # رفتن به صفحه و صبر برای بارگذاری کامل
                await page.goto(self.base_url, wait_until="networkidle", timeout=30000)

                # صبر اضافی برای اطمینان از بارگذاری کامل
                await asyncio.sleep(3)

                try:
                    await asyncio.wait_for(signature_event.wait(), timeout=15)
                except asyncio.TimeoutError:
                    print("❌ x-signature پیدا نشد! در حال تلاش مجدد...")
                    # تلاش مجدد با رفرش صفحه
                    await page.reload(wait_until="networkidle")
                    await asyncio.sleep(2)
                    try:
                        await asyncio.wait_for(signature_event.wait(), timeout=10)
                    except asyncio.TimeoutError:
                        print("❌ x-signature در تلاش دوم هم پیدا نشد!")

                await browser.close()
        except Exception as e:
            print(f"❌ خطا در راه‌اندازی Playwright: {e}")
            import traceback
            traceback.print_exc()

    async def fetch_event_details(self, client: httpx.AsyncClient, event_id: str, currency_symbol: str) -> Optional[Dict]:
        """
        دریافت جزئیات یک رویداد خبری

        Args:
            client: کلاینت HTTP
            event_id: شناسه رویداد
            currency_symbol: نماد ارز

        Returns:
            dict یا None: جزئیات رویداد
        """
        url = f"{self.api_base}/history/{event_id}/{currency_symbol}/"
        headers = {"x-signature": self.x_signature}
        try:
            resp = await client.get(url, headers=headers, timeout=10)
            data = resp.json()
            if "data" in data and data["data"]:
                return data["data"][0]["event"]
        except Exception as e:
            print(f"❌ خطا در گرفتن دیتیل {event_id}: {e}")
        return None

    async def fetch_events(self, start_date: datetime.date, end_date: datetime.date) -> Dict:
        """
        دریافت رویدادهای خبری در بازه زمانی مشخص

        Args:
            start_date: تاریخ شروع
            end_date: تاریخ پایان

        Returns:
            dict: داده‌های رویدادها
        """
        # چک کردن وجود x-signature (بدون تلاش مجدد برای دریافت)
        if not self.x_signature:
            raise Exception("x-signature موجود نیست. لطفاً بات را مجدداً راه‌اندازی کنید.")

        headers = {"x-signature": self.x_signature}
        url = f"{self.api_base}/?start_date={start_date}&end_date={end_date}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            return resp.json()

    async def get_daily_news(self) -> Optional[str]:
        """
        دریافت اخبار امروز به صورت فرمت شده

        Returns:
            str یا None: پیام فرمت شده اخبار روز
        """
        try:
            # چک کردن دسترسی به API
            if not self.use_playwright:
                return self._get_unavailable_message()

            today = datetime.date.today()

            # دریافت اخبار
            data = await self.fetch_events(today, today)
            forex_days = data.get("data", {}).get("forex", [])

            if not forex_days:
                return "📰 اخبار اقتصاد جهانی امروز موجود نیست."

            # ساخت پیام
            msg_lines = [f"📰 *اخبار اقتصاد جهانی امروز* ({today})", ""]

            for day in forex_days:
                events = day.get("events", [])
                if not events:
                    continue

                # گروه‌بندی بر اساس سطح تاثیر
                high_impact = []
                mid_impact = []
                low_impact = []

                for ev in events:
                    impact = ev.get('impact', '').lower()
                    event_info = {
                        'color': self.get_news_color(impact),
                        'currency': ev.get('currency_symbol', ''),
                        'time': ev.get('time', ''),
                        'name_fa': ev['event'].get('event_name_fa', ''),
                        'name_en': ev['event'].get('event_name', ''),
                        'actual': ev.get('actual', '-'),
                        'forecast': ev.get('forecast', '-'),
                        'previous': ev.get('previous', '-')
                    }

                    if impact == 'high':
                        high_impact.append(event_info)
                    elif impact == 'mid':
                        mid_impact.append(event_info)
                    else:
                        low_impact.append(event_info)

                # نمایش اخبار بر اساس اولویت
                if high_impact:
                    msg_lines.append("🔴 *اخبار پرتاثیر*")
                    for ev in high_impact:
                        msg_lines.append(f"{ev['color']} {ev['currency']} {ev['time']}")
                        msg_lines.append(f"   📌 {ev['name_fa']}")
                        msg_lines.append(f"   💱 تاثیر بر: {ev['currency']}")
                        msg_lines.append(f"   🔹 فعلی: {ev['actual']} | 🔸 پیش‌بینی: {ev['forecast']} | ⬅️ قبلی: {ev['previous']}")
                        msg_lines.append("")

                if mid_impact:
                    msg_lines.append("🟡 *اخبار تاثیر متوسط*")
                    for ev in mid_impact[:5]:  # فقط 5 تای اول
                        msg_lines.append(f"{ev['color']} {ev['currency']} {ev['time']} - {ev['name_fa']}")
                    msg_lines.append("")

                if low_impact and len(high_impact) + len(mid_impact) < 10:
                    msg_lines.append("⚪ *سایر اخبار*")
                    for ev in low_impact[:3]:  # فقط 3 تای اول
                        msg_lines.append(f"{ev['color']} {ev['currency']} {ev['time']} - {ev['name_fa']}")
                    msg_lines.append("")

            msg_lines.append("─" * 35)
            msg_lines.append("منبع: ForexFactory.live")
            msg_lines.append("")
            msg_lines.append(BotConstants.get_message_footer(include_divider=False))

            return "\n".join(msg_lines)

        except Exception as e:
            print(f"❌ خطا در دریافت اخبار جهانی: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_unavailable_message(self) -> str:
        """پیام موقت برای زمانی که سرویس در دسترس نیست"""
        return """
📰 *اخبار اقتصاد جهانی*

⚠️ *موقتاً در دسترس نیست*

متأسفانه در حال حاضر به دلیل محدودیت‌های شبکه، امکان دریافت اخبار اقتصادی وجود ندارد.

🔄 *منابع جایگزین پیشنهادی:*
• [Forex Factory](https://forexfactory.live/)
• [Investing.com Economic Calendar](https://www.investing.com/economic-calendar/)
• [Trading Economics](https://tradingeconomics.com/calendar)
• [FXStreet Calendar](https://www.fxstreet.com/economic-calendar)

این قابلیت به‌زودی با منبع دیگری جایگزین خواهد شد.
"""
        # اضافه کردن footer
        error_msg += "\n\n" + BotConstants.get_message_footer(include_divider=True)

    async def get_weekly_news(self) -> Optional[str]:
        """
        دریافت اخبار هفته به صورت فرمت شده

        Returns:
            str یا None: پیام فرمت شده اخبار هفته
        """
        try:
            # چک کردن دسترسی به API
            if not self.use_playwright:
                return self._get_unavailable_message()

            today = datetime.date.today()
            end = today + datetime.timedelta(days=6)

            # دریافت اخبار
            data = await self.fetch_events(today, end)
            forex_days = data.get("data", {}).get("forex", [])

            if not forex_days:
                return "📅 اخبار اقتصاد جهانی این هفته موجود نیست."

            # ساخت پیام
            msg_lines = ["📅 *اخبار اقتصاد جهانی این هفته*", ""]

            for day in forex_days:
                date = day.get("date")
                events = day.get("events", [])

                if not events:
                    continue

                msg_lines.append(f"🗓️ *{date}*")

                # فقط اخبار پرتاثیر و متوسط
                for ev in events:
                    impact = ev.get('impact', '').lower()
                    if impact in ['high', 'mid']:
                        color = self.get_news_color(impact)
                        currency = ev.get('currency_symbol', '')
                        time_str = ev.get('time', '')
                        name_fa = ev['event'].get('event_name_fa', '')
                        # اضافه کردن ارز تاثیرگذار
                        msg_lines.append(f"  {color} {time_str} - {name_fa} ({currency})")

                msg_lines.append("")

            msg_lines.append("─" * 35)
            msg_lines.append("منبع: ForexFactory.live")
            msg_lines.append("")
            msg_lines.append(BotConstants.get_message_footer(include_divider=False))

            return "\n".join(msg_lines)

        except Exception as e:
            print(f"❌ خطا در دریافت اخبار هفتگی: {e}")
            import traceback
            traceback.print_exc()
            return None
