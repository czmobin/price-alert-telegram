"""
سیستم رصد و هشدار سقف قیمتی برای دلار و طلا
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from jdatetime import datetime as jdatetime
from database import Database
from price_fetcher import PriceFetcher
from constants import BotConstants


class PriceCeilingMonitor:
    """کلاس رصد و هشدار سقف قیمتی"""

    def __init__(self, db: Database, price_fetcher: PriceFetcher):
        """
        راه‌اندازی سیستم رصد سقف قیمتی

        Args:
            db: نمونه دیتابیس
            price_fetcher: نمونه PriceFetcher
        """
        self.db = db
        self.price_fetcher = price_fetcher
        # حداقل فاصله بین دو هشدار برای هر دارایی (24 ساعت = 1 روز)
        self.min_alert_interval = timedelta(hours=24)

    async def check_and_alert_all(self) -> List[Dict]:
        """
        بررسی و ارسال هشدار برای همه دارایی‌ها

        Returns:
            لیست دارایی‌هایی که سقفشان شکسته شده
        """
        alerts_sent = []

        # چک کردن دلار
        usd_alert = await self.check_ceiling_break('usd', 'usd_irr')
        if usd_alert:
            alerts_sent.append(usd_alert)

        # چک کردن طلای 18 عیار
        gold_alert = await self.check_ceiling_break('gold', 'gol18')
        if gold_alert:
            alerts_sent.append(gold_alert)

        return alerts_sent

    async def check_ceiling_break(self, asset_type: str, asset_id: str) -> Optional[Dict]:
        """
        بررسی شکست سقف قیمتی یک دارایی

        Args:
            asset_type: نوع دارایی ('usd' یا 'gold')
            asset_id: شناسه دارایی ('usd_irr' یا 'gol18')

        Returns:
            دیکشنری اطلاعات هشدار در صورت شکست سقف، در غیر این صورت None
        """
        try:
            # دریافت قیمت فعلی
            current_price = await self._get_current_price(asset_type, asset_id)
            if not current_price or current_price <= 0:
                return None

            # ذخیره قیمت در تاریخچه
            self.db.save_price_snapshot(asset_type, asset_id, current_price)

            # دریافت سقف قیمتی فعلی
            ceiling = self.db.get_price_ceiling(asset_type, asset_id)
            if ceiling is None:
                # اولین بار است، سقف را تنظیم کن
                self.db.update_price_ceiling(asset_type, asset_id, current_price)
                return None

            # بررسی شکست سقف (با 0.1% تلورانس برای جلوگیری از نوسانات کوچک)
            tolerance = 1.001  # 0.1% بیشتر
            if current_price <= ceiling * tolerance:
                # سقف شکسته نشده
                return None

            # بررسی آخرین زمان هشدار (جلوگیری از spam)
            last_alert_time = self.db.get_last_ceiling_alert_time(asset_type, asset_id)
            if last_alert_time:
                time_since_last_alert = datetime.now() - last_alert_time
                if time_since_last_alert < self.min_alert_interval:
                    # خیلی زود است برای هشدار جدید
                    return None

            # سقف شکسته شده! به‌روزرسانی سقف
            self.db.update_price_ceiling(asset_type, asset_id, current_price)

            # آماده‌سازی اطلاعات هشدار
            alert_info = {
                'asset_type': asset_type,
                'asset_id': asset_id,
                'current_price': current_price,
                'previous_ceiling': ceiling,
                'price_24h': self.db.get_historical_price(asset_type, asset_id, 24),
                'price_7d': self.db.get_historical_price(asset_type, asset_id, 24 * 7),
                'price_30d': self.db.get_historical_price(asset_type, asset_id, 24 * 30),
            }

            return alert_info

        except Exception as e:
            print(f"خطا در بررسی سقف قیمتی {asset_type}/{asset_id}: {e}")
            return None

    async def _get_current_price(self, asset_type: str, asset_id: str) -> Optional[float]:
        """
        دریافت قیمت فعلی یک دارایی

        Args:
            asset_type: نوع دارایی
            asset_id: شناسه دارایی

        Returns:
            قیمت فعلی یا None
        """
        try:
            if asset_type == 'usd' and asset_id == 'usd_irr':
                usd_data = await self.price_fetcher.get_usd_irr_price()
                return usd_data['price'] if usd_data else None

            elif asset_type == 'gold' and asset_id == 'gol18':
                gold_data = await self.price_fetcher.get_gold_items(['gol18'])
                if gold_data and 'gol18' in gold_data:
                    return gold_data['gol18']['price']
                return None

            return None

        except Exception as e:
            print(f"خطا در دریافت قیمت فعلی: {e}")
            return None

    def format_ceiling_alert_message(self, alert_info: Dict) -> str:
        """
        فرمت کردن پیام هشدار سقف قیمتی

        Args:
            alert_info: اطلاعات هشدار

        Returns:
            پیام فرمت شده
        """
        asset_type = alert_info['asset_type']
        asset_id = alert_info['asset_id']
        current_price = alert_info['current_price']
        price_24h = alert_info.get('price_24h')
        price_7d = alert_info.get('price_7d')
        price_30d = alert_info.get('price_30d')

        # تعیین نام و emoji بر اساس نوع دارایی
        if asset_type == 'usd':
            asset_name = "دلار"
            symbol = "💵"
        elif asset_type == 'gold':
            asset_name = "طلای ۱۸ عیار"
            symbol = "✨"
        else:
            asset_name = asset_id
            symbol = "💰"

        lines = []
        lines.append("🚨 سقف تاریخی قیمت " + asset_name + " شکسته شد")
        lines.append("")
        lines.append(f"🏅 قیمت فعلی {asset_name}:")
        lines.append("")
        lines.append(f"{self.price_fetcher.format_number_no_decimal(current_price)} تومان")
        lines.append("")
        lines.append("📊 مقایسه قیمت:")

        # مقایسه با 24 ساعت گذشته
        if price_24h and price_24h > 0:
            change_24h = ((current_price - price_24h) / price_24h) * 100
            emoji_24h = "📈" if change_24h > 0 else "📉"
            lines.append(
                f" {emoji_24h} ۲۴ ساعت گذشته: "
                f"{self.price_fetcher.format_number_no_decimal(price_24h)} تومان "
                f"({change_24h:+.1f}%)"
            )
        else:
            lines.append(f" • ۲۴ ساعت گذشته: داده کافی موجود نیست")

        # مقایسه با 7 روز گذشته
        if price_7d and price_7d > 0:
            change_7d = ((current_price - price_7d) / price_7d) * 100
            emoji_7d = "📈" if change_7d > 0 else "📉"
            lines.append(
                f" {emoji_7d} یک هفته گذشته: "
                f"{self.price_fetcher.format_number_no_decimal(price_7d)} تومان "
                f"({change_7d:+.1f}%)"
            )
        else:
            lines.append(f" • یک هفته گذشته: داده کافی موجود نیست")

        # مقایسه با 30 روز گذشته
        if price_30d and price_30d > 0:
            change_30d = ((current_price - price_30d) / price_30d) * 100
            emoji_30d = "📈" if change_30d > 0 else "📉"
            lines.append(
                f" {emoji_30d} یک ماه گذشته: "
                f"{self.price_fetcher.format_number_no_decimal(price_30d)} تومان "
                f"({change_30d:+.1f}%)"
            )
        else:
            lines.append(f" • یک ماه گذشته: داده کافی موجود نیست")

        lines.append("")

        # تاریخ و زمان شمسی
        now = jdatetime.now()
        jalali_date = now.strftime('%Y/%m/%d')
        jalali_time = now.strftime('%H:%M')
        lines.append(f"🕐 {jalali_date} - {jalali_time}")

        # Footer
        lines.append("")
        lines.append(BotConstants.get_message_footer(include_divider=True))

        return "\n".join(lines)
