"""
ثابت‌ها و فرمت‌های مشترک برای ربات
"""
from jdatetime import datetime as jalalidatetime


class BotConstants:
    """کلاس نگهداری ثابت‌ها و فرمت‌های مشترک"""

    # اطلاعات ربات
    BOT_NAME = "ارزَلان"
    BOT_USERNAME = "@arzzalanbot"
    BOT_DESCRIPTION = "دستیار اطلاع‌رسانی قیمت‌ها"

    @staticmethod
    def get_message_footer(include_divider: bool = True) -> str:
        """
        دریافت footer استاندارد برای پیام‌ها

        Args:
            include_divider: آیا خط جداکننده اضافه شود یا نه

        Returns:
            str: footer فرمت شده
        """
        lines = []

        if include_divider:
            lines.append("─" * 35)

        # زمان فعلی به صورت شمسی
        now = jalalidatetime.now()
        jalali_date = now.strftime('%Y/%m/%d')
        jalali_time = now.strftime('%H:%M')

        lines.append(f"🕐 {jalali_date} - {jalali_time}")
        lines.append("--")
        lines.append(f"{BotConstants.BOT_NAME} {BotConstants.BOT_DESCRIPTION}")
        lines.append(BotConstants.BOT_USERNAME)

        return "\n".join(lines)

    @staticmethod
    def format_time(include_date: bool = True) -> str:
        """
        فرمت کردن زمان فعلی به شمسی

        Args:
            include_date: آیا تاریخ هم نمایش داده شود

        Returns:
            str: زمان فرمت شده
        """
        now = jalalidatetime.now()

        if include_date:
            return now.strftime('%Y/%m/%d - %H:%M')
        else:
            return now.strftime('%H:%M')
