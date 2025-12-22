"""
ثابت‌ها و فرمت‌های مشترک برای ربات
"""
from jdatetime import datetime as jalalidatetime


class BotConstants:
    """کلاس نگهداری ثابت‌ها و فرمت‌های مشترک"""

    # اطلاعات ربات (پیش‌فرض)
    BOT_NAME = "ارزَلان"
    DEFAULT_FOOTER_TEXT = "ارزَلان دستیار اطلاع‌رسانی قیمت‌ها"
    DEFAULT_FOOTER_USERNAME = "@arzzalanbot"

    # نمونه database برای دسترسی عمومی
    _db_instance = None

    @classmethod
    def set_db_instance(cls, db_instance):
        """تنظیم نمونه database برای استفاده در کلاس"""
        cls._db_instance = db_instance

    @classmethod
    def get_message_footer(cls, include_divider: bool = True) -> str:
        """
        دریافت footer استاندارد برای پیام‌ها (از database)

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

        # دریافت footer از database
        if cls._db_instance:
            try:
                footer_settings = cls._db_instance.get_footer_settings()
                footer_text = footer_settings.get('footer_text', cls.DEFAULT_FOOTER_TEXT)
                footer_username = footer_settings.get('footer_username', cls.DEFAULT_FOOTER_USERNAME)
            except Exception as e:
                print(f"خطا در دریافت footer از database: {e}")
                footer_text = cls.DEFAULT_FOOTER_TEXT
                footer_username = cls.DEFAULT_FOOTER_USERNAME
        else:
            footer_text = cls.DEFAULT_FOOTER_TEXT
            footer_username = cls.DEFAULT_FOOTER_USERNAME

        lines.append(footer_text)
        lines.append(footer_username)

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
