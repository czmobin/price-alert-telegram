"""
ربات تلگرام اطلاع‌رسانی قیمت سرمایه‌گذاری
"""
import asyncio
import logging
from datetime import datetime, time
from typing import List

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import pytz

from config import TELEGRAM_BOT_TOKEN, TIMEZONE, CRYPTO_SYMBOLS, DEFAULT_CRYPTOS
from database import Database
from price_fetcher import PriceFetcher

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# وضعیت‌های مکالمه
PHONE_NUMBER, SELECT_TIME, SELECT_CRYPTOS = range(3)

# نمونه‌های global
db = Database()
price_fetcher = PriceFetcher()


class InvestmentBot:
    """کلاس اصلی ربات"""

    def __init__(self):
        self.application = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        user_data = db.get_user(user.id)

        # ثبت یا به‌روزرسانی کاربر
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )

        welcome_message = f"""
سلام {user.first_name} عزیز! 👋

به ربات اطلاع‌رسانی قیمت سرمایه‌گذاری خوش آمدید.

این ربات می‌تواند:
🔹 قیمت ارزهای دیجیتال را نمایش دهد
🔹 قیمت طلا و نقره را نمایش دهد
🔹 قیمت دلار را نمایش دهد
🔹 تغییرات هفتگی را نمایش دهد
🔹 در ساعت دلخواه شما پیام ارسال کند

دستورات موجود:
/price - دریافت قیمت‌های فعلی
/settings - تنظیمات شخصی
/schedule - تنظیم زمان‌بندی
/cryptos - انتخاب ارزهای دیجیتال
/help - راهنما

برای شروع، لطفاً شماره تماس خود را با من به اشتراک بگذارید.
"""

        # چک کردن اینکه آیا کاربر شماره تلفن داده یا نه
        if not user_data or not user_data.get('phone_number'):
            # دکمه درخواست شماره تلفن
            contact_button = KeyboardButton("📱 اشتراک شماره تلفن", request_contact=True)
            reply_markup = ReplyKeyboardMarkup(
                [[contact_button]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
            return PHONE_NUMBER
        else:
            await update.message.reply_text(welcome_message)
            return ConversationHandler.END

    async def receive_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت شماره تلفن کاربر"""
        if update.message.contact:
            phone_number = update.message.contact.phone_number
            user_id = update.effective_user.id

            # ذخیره شماره در دیتابیس
            db.update_phone_number(user_id, phone_number)

            await update.message.reply_text(
                f"✅ شماره تلفن شما ({phone_number}) ثبت شد.\n\n"
                "برای دریافت قیمت‌ها از دستور /price استفاده کنید.",
                reply_markup=ReplyKeyboardMarkup([['📊 دریافت قیمت‌ها']], resize_keyboard=True)
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "لطفاً از دکمه 'اشتراک شماره تلفن' استفاده کنید."
            )
            return PHONE_NUMBER

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /price - نمایش قیمت‌ها"""
        user_id = update.effective_user.id

        # ارسال پیام در حال پردازش
        processing_msg = await update.message.reply_text("⏳ در حال دریافت قیمت‌ها...")

        try:
            # دریافت تنظیمات کاربر
            settings = db.get_user_settings(user_id)

            if not settings:
                crypto_ids = DEFAULT_CRYPTOS
                include_gold = True
                include_silver = True
                include_usd = True
            else:
                crypto_ids = settings['selected_cryptos']
                include_gold = bool(settings['include_gold'])
                include_silver = bool(settings['include_silver'])
                include_usd = bool(settings['include_usd'])

            # دریافت قیمت‌ها
            prices = price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd
            )

            # فرمت کردن پیام
            message = price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
                [
                    InlineKeyboardButton("⚙️ تنظیمات", callback_data='open_settings'),
                    InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_cryptos')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # حذف پیام پردازش و ارسال پیام اصلی
            await processing_msg.delete()
            await update.message.reply_text(message, reply_markup=reply_markup)

            # ثبت در تاریخچه
            db.log_message(user_id, 'price_request')

        except Exception as e:
            logger.error(f"خطا در دریافت قیمت: {e}")
            await processing_msg.edit_text(
                "❌ متأسفانه در دریافت قیمت‌ها خطایی رخ داد. لطفاً دوباره تلاش کنید."
            )

    async def refresh_prices_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای به‌روزرسانی قیمت‌ها"""
        query = update.callback_query
        await query.answer("در حال به‌روزرسانی...")

        user_id = update.effective_user.id

        try:
            # دریافت تنظیمات کاربر
            settings = db.get_user_settings(user_id)

            if not settings:
                crypto_ids = DEFAULT_CRYPTOS
                include_gold = True
                include_silver = True
                include_usd = True
            else:
                crypto_ids = settings['selected_cryptos']
                include_gold = bool(settings['include_gold'])
                include_silver = bool(settings['include_silver'])
                include_usd = bool(settings['include_usd'])

            # دریافت قیمت‌های جدید
            prices = price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd
            )

            # فرمت کردن پیام
            message = price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
                [
                    InlineKeyboardButton("⚙️ تنظیمات", callback_data='open_settings'),
                    InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_cryptos')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # به‌روزرسانی پیام
            await query.edit_message_text(message, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی قیمت: {e}")
            await query.edit_message_text(
                "❌ متأسفانه در به‌روزرسانی قیمت‌ها خطایی رخ داد."
            )

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /settings - تنظیمات"""
        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        if not settings:
            message = "شما هنوز تنظیماتی ندارید."
            notification_status = "❌ غیرفعال"
            notification_time = "تنظیم نشده"
        else:
            notification_status = "✅ فعال" if settings['notification_enabled'] else "❌ غیرفعال"
            notification_time = settings['notification_time']

            message = f"""
⚙️ تنظیمات شما:

🔔 وضعیت اعلان: {notification_status}
🕐 زمان ارسال: {notification_time}
🪙 تعداد ارزها: {len(settings['selected_cryptos'])}
🥇 طلا: {'✅' if settings['include_gold'] else '❌'}
🥈 نقره: {'✅' if settings['include_silver'] else '❌'}
💵 دلار: {'✅' if settings['include_usd'] else '❌'}
"""

        # دکمه‌های تنظیمات
        keyboard = [
            [InlineKeyboardButton("⏰ تنظیم زمان‌بندی", callback_data='setup_schedule')],
            [InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_cryptos')],
            [InlineKeyboardButton("💰 انتخاب دارایی‌ها", callback_data='select_assets')],
        ]

        if settings and settings['notification_enabled']:
            keyboard.append([InlineKeyboardButton("🔕 غیرفعال کردن اعلان", callback_data='disable_notification')])
        else:
            keyboard.append([InlineKeyboardButton("🔔 فعال کردن اعلان", callback_data='enable_notification')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # بررسی اینکه آیا از command آمده یا callback
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def select_cryptos_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب ارزهای دیجیتال"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_cryptos = settings['selected_cryptos'] if settings else DEFAULT_CRYPTOS

        message = """
📋 انتخاب ارزهای دیجیتال:

لیست ارزهای فعال شما را مشخص کنید.
روی هر ارز کلیک کنید تا فعال/غیرفعال شود.
"""

        # ساخت دکمه‌های ارزها
        keyboard = []
        available_cryptos = list(CRYPTO_SYMBOLS.keys())

        for i in range(0, len(available_cryptos), 2):
            row = []
            for j in range(2):
                if i + j < len(available_cryptos):
                    crypto = available_cryptos[i + j]
                    symbol = CRYPTO_SYMBOLS[crypto]
                    is_selected = crypto in current_cryptos
                    button_text = f"{'✅' if is_selected else '⬜️'} {symbol}"
                    row.append(InlineKeyboardButton(button_text, callback_data=f'toggle_crypto_{crypto}'))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("✔️ تأیید و بازگشت", callback_data='back_to_settings')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def toggle_crypto_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تغییر وضعیت ارز"""
        query = update.callback_query
        crypto_id = query.data.split('_', 2)[2]

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_cryptos = settings['selected_cryptos'] if settings else DEFAULT_CRYPTOS.copy()

        # toggle کردن ارز
        if crypto_id in current_cryptos:
            current_cryptos.remove(crypto_id)
        else:
            current_cryptos.append(crypto_id)

        # حداقل یک ارز باید انتخاب شده باشد
        if len(current_cryptos) == 0:
            await query.answer("حداقل یک ارز باید انتخاب شود!", show_alert=True)
            return

        # ذخیره در دیتابیس
        db.update_selected_cryptos(user_id, current_cryptos)

        await query.answer("✅ تغییرات ذخیره شد")

        # به‌روزرسانی پیام
        await self.select_cryptos_callback(update, context)

    async def select_assets_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب دارایی‌های دیگر"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        include_gold = bool(settings['include_gold']) if settings else True
        include_silver = bool(settings['include_silver']) if settings else True
        include_usd = bool(settings['include_usd']) if settings else True

        message = "💰 انتخاب دارایی‌های دیگر:"

        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if include_gold else '⬜️'} 🥇 طلا",
                callback_data='toggle_asset_gold'
            )],
            [InlineKeyboardButton(
                f"{'✅' if include_silver else '⬜️'} 🥈 نقره",
                callback_data='toggle_asset_silver'
            )],
            [InlineKeyboardButton(
                f"{'✅' if include_usd else '⬜️'} 💵 دلار",
                callback_data='toggle_asset_usd'
            )],
            [InlineKeyboardButton("✔️ تأیید و بازگشت", callback_data='back_to_settings')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def toggle_asset_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تغییر وضعیت دارایی"""
        query = update.callback_query
        asset_type = query.data.split('_', 2)[2]

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        # دریافت وضعیت فعلی
        current_value = bool(settings[f'include_{asset_type}']) if settings else True

        # تغییر وضعیت
        new_value = not current_value

        # ذخیره در دیتابیس
        kwargs = {f'include_{asset_type}': new_value}
        db.update_asset_preferences(user_id, **kwargs)

        await query.answer("✅ تغییرات ذخیره شد")

        # به‌روزرسانی پیام
        await self.select_assets_callback(update, context)

    async def setup_schedule_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تنظیم زمان‌بندی"""
        query = update.callback_query
        await query.answer()

        message = """
⏰ تنظیم زمان‌بندی:

لطفاً ساعت دلخواه خود را برای دریافت گزارش روزانه وارد کنید.

فرمت: HH:MM (مثال: 09:00 یا 14:30)

برای لغو از /cancel استفاده کنید.
"""

        await query.edit_message_text(message)

        # ذخیره وضعیت در context
        context.user_data['waiting_for_time'] = True

    async def receive_schedule_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت زمان از کاربر"""
        if not context.user_data.get('waiting_for_time'):
            return

        user_id = update.effective_user.id
        time_text = update.message.text.strip()

        # اعتبارسنجی فرمت زمان
        try:
            hour, minute = map(int, time_text.split(':'))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ فرمت زمان اشتباه است. لطفاً به فرمت HH:MM وارد کنید (مثال: 09:00)"
            )
            return

        # ذخیره در دیتابیس
        db.update_notification_settings(user_id, enabled=True, notification_time=time_text)

        # برنامه‌ریزی job جدید
        self.schedule_user_notification(user_id, time_text)

        context.user_data['waiting_for_time'] = False

        await update.message.reply_text(
            f"✅ زمان‌بندی با موفقیت تنظیم شد.\n\n"
            f"🕐 هر روز در ساعت {time_text} گزارش قیمت‌ها برای شما ارسال می‌شود."
        )

    async def enable_notification_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای فعال کردن اعلان"""
        query = update.callback_query
        user_id = update.effective_user.id

        # فعال کردن نوتیفیکیشن
        db.update_notification_settings(user_id, enabled=True)

        await query.answer("✅ اعلان‌ها فعال شدند")

        # بارگذاری مجدد تنظیمات
        settings = db.get_user_settings(user_id)
        if settings and settings['notification_time']:
            self.schedule_user_notification(user_id, settings['notification_time'])

        # نمایش تنظیمات
        await self.settings_command(update, context)

    async def disable_notification_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای غیرفعال کردن اعلان"""
        query = update.callback_query
        user_id = update.effective_user.id

        # غیرفعال کردن نوتیفیکیشن
        db.update_notification_settings(user_id, enabled=False)

        # حذف job زمان‌بندی
        if self.application and self.application.job_queue:
            job_name = f'notification_{user_id}'
            current_jobs = self.application.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()

        await query.answer("✅ اعلان‌ها غیرفعال شدند")

        # نمایش تنظیمات
        await self.settings_command(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = """
📚 راهنمای استفاده از ربات:

🔹 دستورات اصلی:
/start - شروع کار با ربات
/price - دریافت قیمت‌های فعلی
/settings - مشاهده و تغییر تنظیمات
/schedule - تنظیم زمان ارسال خودکار
/cryptos - انتخاب ارزهای دیجیتال
/help - نمایش این راهنما

🔹 قابلیت‌ها:
• مشاهده قیمت لحظه‌ای ارزهای دیجیتال
• مشاهده قیمت طلا و نقره
• مشاهده قیمت دلار
• تغییرات هفتگی تمام دارایی‌ها
• دریافت خودکار در ساعت دلخواه
• شخصی‌سازی لیست ارزها

🔹 نحوه استفاده:
1️⃣ از دستور /price برای دریافت قیمت‌ها استفاده کنید
2️⃣ روی دکمه 🔄 کلیک کنید تا قیمت‌ها به‌روز شوند
3️⃣ از /settings برای تنظیمات استفاده کنید
4️⃣ ارزهای دلخواه خود را انتخاب کنید
5️⃣ زمان دریافت خودکار را تنظیم کنید

سوالی دارید؟ پیام بدهید! 💬
"""
        await update.message.reply_text(help_text)

    def schedule_user_notification(self, user_id: int, notification_time: str):
        """برنامه‌ریزی ارسال خودکار برای کاربر"""
        try:
            if not self.application or not self.application.job_queue:
                logger.error("JobQueue در دسترس نیست")
                return

            hour, minute = map(int, notification_time.split(':'))

            # حذف job قبلی اگر وجود دارد
            job_name = f'notification_{user_id}'
            current_jobs = self.application.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()

            # تبدیل زمان به time object با timezone
            tz = pytz.timezone(TIMEZONE)
            scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

            # اضافه کردن job جدید
            self.application.job_queue.run_daily(
                self.send_scheduled_price,
                time=scheduled_time,
                data=user_id,
                name=job_name
            )

            logger.info(f"زمان‌بندی برای کاربر {user_id} در ساعت {notification_time} تنظیم شد")

        except Exception as e:
            logger.error(f"خطا در زمان‌بندی: {e}")

    async def send_scheduled_price(self, context: ContextTypes.DEFAULT_TYPE):
        """ارسال قیمت‌ها در زمان برنامه‌ریزی شده"""
        try:
            # دریافت user_id از job data
            user_id = context.job.data

            # دریافت تنظیمات کاربر
            settings = db.get_user_settings(user_id)

            if not settings or not settings['notification_enabled']:
                return

            crypto_ids = settings['selected_cryptos']
            include_gold = bool(settings['include_gold'])
            include_silver = bool(settings['include_silver'])
            include_usd = bool(settings['include_usd'])

            # دریافت قیمت‌ها
            prices = price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd
            )

            # فرمت کردن پیام
            message = "📊 گزارش روزانه شما:\n\n"
            message += price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # ارسال پیام
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=reply_markup
            )

            # ثبت در تاریخچه
            db.log_message(user_id, 'scheduled_notification')

            logger.info(f"گزارش برنامه‌ریزی شده برای کاربر {user_id} ارسال شد")

        except Exception as e:
            logger.error(f"خطا در ارسال گزارش برنامه‌ریزی شده: {e}")

    def load_scheduled_notifications(self):
        """بارگذاری تمام زمان‌بندی‌های ذخیره شده"""
        try:
            # دریافت تمام کاربران با نوتیفیکیشن فعال
            # این کار را با query مستقیم انجام می‌دهیم
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT u.user_id, s.notification_time
                FROM users u
                JOIN user_settings s ON u.user_id = s.user_id
                WHERE s.notification_enabled = 1 AND u.is_active = 1
            ''')

            users = cursor.fetchall()
            conn.close()

            for user in users:
                user_id = user['user_id']
                notification_time = user['notification_time']
                self.schedule_user_notification(user_id, notification_time)

            logger.info(f"تعداد {len(users)} زمان‌بندی بارگذاری شد")

        except Exception as e:
            logger.error(f"خطا در بارگذاری زمان‌بندی‌ها: {e}")

    async def run(self):
        """اجرای ربات"""
        # ساخت Application
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # ConversationHandler برای ثبت نام
        registration_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start_command)],
            states={
                PHONE_NUMBER: [MessageHandler(filters.CONTACT, self.receive_phone_number)],
            },
            fallbacks=[],
        )

        # Handler ها
        self.application.add_handler(registration_handler)
        self.application.add_handler(CommandHandler('price', self.price_command))
        self.application.add_handler(CommandHandler('settings', self.settings_command))
        self.application.add_handler(CommandHandler('help', self.help_command))

        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(
            self.refresh_prices_callback, pattern='^refresh_prices$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.select_cryptos_callback, pattern='^select_cryptos$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_crypto_callback, pattern='^toggle_crypto_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.select_assets_callback, pattern='^select_assets$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_asset_callback, pattern='^toggle_asset_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.setup_schedule_callback, pattern='^setup_schedule$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.enable_notification_callback, pattern='^enable_notification$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.disable_notification_callback, pattern='^disable_notification$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.settings_command, pattern='^back_to_settings$'
        ))

        # Handler برای دریافت زمان
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.receive_schedule_time
        ))

        # بارگذاری زمان‌بندی‌های ذخیره شده
        self.load_scheduled_notifications()

        # اجرای ربات
        logger.info("ربات در حال اجرا است...")

        # Initialize and start the application
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        # Keep the bot running
        try:
            # Wait until the application is stopped
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("توقف ربات...")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


async def main():
    """تابع اصلی"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("توکن تلگرام یافت نشد! لطفاً فایل .env را تنظیم کنید.")
        return

    bot = InvestmentBot()
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
