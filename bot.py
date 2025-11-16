"""
ربات تلگرام دستیار ارزَلان - اطلاع‌رسانی قیمت ارزهای دیجیتال
"""
import asyncio
import logging
import sys
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
from telegram.error import TelegramError
import pytz

from config import (
    TELEGRAM_BOT_TOKEN, CHANNEL_ID, TIMEZONE, CRYPTO_SYMBOLS,
    DEFAULT_CRYPTOS, TOP_5_CRYPTOS, TOP_10_CRYPTOS, PRESET_TIMES,
    FIAT_CURRENCIES, GOLD_COINS, GOLD_ITEMS
)
from database import Database
from price_fetcher import PriceFetcher

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# وضعیت‌های مکالمه
WAITING_FOR_TIME = range(1)
WAITING_FOR_BROADCAST_MESSAGE = range(1)

# نمونه‌های global
db = Database()
price_fetcher = PriceFetcher()


class ArzalanBot:
    """کلاس اصلی ربات دستیار ارزَلان"""

    def __init__(self):
        self.application = None

    async def is_admin(self, user_id: int) -> bool:
        """چک کردن ادمین بودن کاربر"""
        return db.is_admin(user_id)

    async def check_channel_membership(self, user_id: int) -> bool:
        """چک کردن عضویت کاربر در کانال"""
        try:
            member = await self.application.bot.get_chat_member(CHANNEL_ID, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except TelegramError as e:
            logger.error(f"خطا در چک عضویت کانال: {e}")
            return True  # در صورت خطا، اجازه ادامه بده

    async def require_membership(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        چک عضویت و نمایش پیام درخواست عضویت در صورت نیاز

        Returns:
            True اگر کاربر عضو است، False اگر عضو نیست
        """
        user_id = update.effective_user.id
        is_member = await self.check_channel_membership(user_id)

        if not is_member:
            membership_message = """برای استفاده از دستیار ارزَلان کافیه در کانال اصلی اون عضو بشی.
خبری از تبلیغات نیست کانال خودمونه."""

            keyboard = [
                [InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data='check_membership')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # بررسی اینکه آیا از callback آمده یا message
            if update.callback_query:
                await update.callback_query.answer("⚠️ ابتدا باید در کانال عضو شوید", show_alert=True)
                await update.callback_query.edit_message_text(membership_message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(membership_message, reply_markup=reply_markup)

            return False

        return True

    def get_main_menu_keyboard(self):
        """منوی اصلی با دکمه‌های keyboard"""
        keyboard = [
            ['📤 ارسال قیمت الان'],
            ['🕒 تنظیم زمان ارسال روزانه پیام', '🔔 اعلان تغییر قیمت'],
            ['❓ راهنما', '⚙️ تنظیمات'],
            ['👤 پشتیبانی']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start - پیام خوش‌آمد و چک عضویت"""
        user = update.effective_user
        user_id = user.id

        # ثبت یا به‌روزرسانی کاربر
        db.add_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )

        # پیام خوش‌آمد
        welcome_message = f"""📲 به دستیار ابزار ارز دیجیتال ارزَلان خوش اومدی!

با دستیار ارزَلان میتونی:
🔹 قیمت لحظه‌ای ارزهای دیجیتال، طلا، نقره و ارزهای فیات رو ببینی.
🔹 قیمت لحظه‌ای دلار در ایران رو ببینی.
🔹 در زمانبندی دلخواه خودت از قیمت ها باخبر بشی.

هر جا نیاز به کمک داشتی روی راهنما کلیک کن
/help"""

        await update.message.reply_text(welcome_message)

        # چک عضویت در کانال
        is_member = await self.check_channel_membership(user_id)

        if not is_member:
            # پیام درخواست عضویت
            membership_message = """برای استفاده از دستیار ارزَلان کافیه در کانال اصلی اون عضو بشی.
خبری از تبلیغات نیست کانال خودمونه."""

            keyboard = [
                [InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                [InlineKeyboardButton("✅ عضو شدم", callback_data='check_membership')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(membership_message, reply_markup=reply_markup)
        else:
            # نمایش منوی اصلی و ارسال لیست قیمت‌ها
            await self.show_main_menu(update, context)

    async def check_membership_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای چک عضویت"""
        query = update.callback_query
        user_id = update.effective_user.id

        is_member = await self.check_channel_membership(user_id)

        if is_member:
            await query.answer("✅ عضویت شما تأیید شد!")
            await query.edit_message_text("✅ عضویت شما تأیید شد! خوش اومدی به ارزَلان 🎉")

            # ارسال منوی اصلی و قیمت‌ها
            await self.show_main_menu_after_callback(query, context)
        else:
            await query.answer("❌ برای ادامه باید عضو کانال باشی", show_alert=True)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی اصلی و ارسال قیمت‌ها"""
        # نمایش منوی keyboard
        await update.message.reply_text(
            "منوی اصلی:",
            reply_markup=self.get_main_menu_keyboard()
        )

        # ارسال قیمت‌ها
        await self.send_prices(update, context, is_first_time=True)

    async def show_main_menu_after_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی اصلی بعد از callback"""
        user_id = query.from_user.id

        # ارسال منوی keyboard
        await context.bot.send_message(
            chat_id=user_id,
            text="منوی اصلی:",
            reply_markup=self.get_main_menu_keyboard()
        )

        # ارسال قیمت‌ها
        await self.send_prices_to_user(user_id, context, is_first_time=True)

    async def send_prices(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_first_time: bool = False):
        """ارسال قیمت‌ها"""
        # چک عضویت کاربر
        if not await self.require_membership(update, context):
            return

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
                fiat_currency_ids = []
                gold_coin_ids = []
                gold_item_ids = []
            else:
                crypto_ids = settings['selected_cryptos']
                include_gold = bool(settings['include_gold'])
                include_silver = bool(settings['include_silver'])
                include_usd = bool(settings['include_usd'])
                fiat_currency_ids = settings.get('selected_fiat_currencies', [])
                gold_coin_ids = settings.get('selected_gold_coins', [])
                gold_item_ids = settings.get('selected_gold_items', [])

            # دریافت قیمت‌ها
            prices = await price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd,
                fiat_currency_ids=fiat_currency_ids,
                gold_coin_ids=gold_coin_ids,
                gold_item_ids=gold_item_ids
            )

            # فرمت کردن پیام
            message = price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
                [
                    InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_assets_main'),
                    InlineKeyboardButton("⏰ زمان‌بندی ارسال", callback_data='setup_schedule')
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

    async def send_prices_to_user(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, is_first_time: bool = False):
        """ارسال قیمت‌ها به کاربر (برای callback)"""
        try:
            # دریافت تنظیمات کاربر
            settings = db.get_user_settings(user_id)

            if not settings:
                crypto_ids = DEFAULT_CRYPTOS
                include_gold = True
                include_silver = True
                include_usd = True
                fiat_currency_ids = []
                gold_coin_ids = []
                gold_item_ids = []
            else:
                crypto_ids = settings['selected_cryptos']
                include_gold = bool(settings['include_gold'])
                include_silver = bool(settings['include_silver'])
                include_usd = bool(settings['include_usd'])
                fiat_currency_ids = settings.get('selected_fiat_currencies', [])
                gold_coin_ids = settings.get('selected_gold_coins', [])
                gold_item_ids = settings.get('selected_gold_items', [])

            # دریافت قیمت‌ها
            prices = await price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd,
                fiat_currency_ids=fiat_currency_ids,
                gold_coin_ids=gold_coin_ids,
                gold_item_ids=gold_item_ids
            )

            # فرمت کردن پیام
            message = price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
                [
                    InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_assets_main'),
                    InlineKeyboardButton("⏰ زمان‌بندی ارسال", callback_data='setup_schedule')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # ارسال پیام
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=reply_markup
            )

            # ثبت در تاریخچه
            db.log_message(user_id, 'price_request')

        except Exception as e:
            logger.error(f"خطا در ارسال قیمت: {e}")

    async def refresh_prices_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای به‌روزرسانی قیمت‌ها"""
        query = update.callback_query

        # چک عضویت کاربر
        if not await self.require_membership(update, context):
            return

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
                fiat_currency_ids = []
                gold_coin_ids = []
                gold_item_ids = []
            else:
                crypto_ids = settings['selected_cryptos']
                include_gold = bool(settings['include_gold'])
                include_silver = bool(settings['include_silver'])
                include_usd = bool(settings['include_usd'])
                fiat_currency_ids = settings.get('selected_fiat_currencies', [])
                gold_coin_ids = settings.get('selected_gold_coins', [])
                gold_item_ids = settings.get('selected_gold_items', [])

            # دریافت قیمت‌های جدید
            prices = await price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd,
                fiat_currency_ids=fiat_currency_ids,
                gold_coin_ids=gold_coin_ids,
                gold_item_ids=gold_item_ids
            )

            # فرمت کردن پیام
            message = price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
                [
                    InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_assets_main'),
                    InlineKeyboardButton("⏰ زمان‌بندی ارسال", callback_data='setup_schedule')
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

    async def select_assets_main_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب نوع دارایی"""
        query = update.callback_query

        # چک عضویت کاربر
        if not await self.require_membership(update, context):
            return

        await query.answer()

        message = "چه نوع دارایی می‌خوای اضافه کنی؟"

        keyboard = [
            [InlineKeyboardButton("💰 ارز دیجیتال (Cryptocurrency)", callback_data='asset_type_crypto')],
            [InlineKeyboardButton("🥇 طلا و نقره", callback_data='asset_type_gold_silver')],
            [InlineKeyboardButton("💵 دلار", callback_data='asset_type_usd')],
            [InlineKeyboardButton("💱 ارزهای فیات", callback_data='asset_type_fiat')],
            [InlineKeyboardButton("🪙 سکه‌های طلا", callback_data='asset_type_gold_coins')],
            [InlineKeyboardButton("✨ طلا (گرمی، مثقال، اونس)", callback_data='asset_type_gold_items')],
            [InlineKeyboardButton("📊 بورس ایران (به زودی)", callback_data='asset_type_stock')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def asset_type_crypto_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب ارزهای دیجیتال"""
        query = update.callback_query
        await query.answer()

        message = """ارزهای خود را به صورت دستی یا با انتخاب گزینه های زیر انتخاب کنید."""

        keyboard = [
            [InlineKeyboardButton("⭐️ ۵ ارز برتر بازار", callback_data='crypto_top5')],
            [InlineKeyboardButton("🔟 ارزهای منتخب بازار", callback_data='crypto_top10')],
            [InlineKeyboardButton("✍️ انتخاب دستی", callback_data='crypto_manual')],
            [InlineKeyboardButton("🔙 بازگشت", callback_data='select_assets_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def crypto_top5_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب 5 ارز برتر"""
        query = update.callback_query
        user_id = update.effective_user.id

        # ذخیره 5 ارز برتر
        db.update_selected_cryptos(user_id, TOP_5_CRYPTOS)

        await query.answer("✅ 5 ارز برتر بازار انتخاب شد")

        # نمایش لیست با تیک
        message = """✅ 5 ارز برتر بازار انتخاب شد:

☑️ BTC
☑️ ETH
☑️ USDT
☑️ BNB
☑️ SOL"""

        keyboard = [
            [InlineKeyboardButton("✍️ ویرایش دستی", callback_data='crypto_manual')],
            [InlineKeyboardButton("✔️ تأیید و ادامه", callback_data='select_assets_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def crypto_top10_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای نمایش ارزهای منتخب بازار (10 ارز)"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_cryptos = settings['selected_cryptos'] if settings else DEFAULT_CRYPTOS

        message = """ارز مورد نظرت رو با نام اون بنویس یا از لیست زیر انتخاب کن.

ارزهای منتخب بازار:"""

        # ساخت دکمه‌های ارزها
        keyboard = []

        for crypto in TOP_10_CRYPTOS:
            symbol = CRYPTO_SYMBOLS.get(crypto, crypto.upper())
            is_selected = crypto in current_cryptos
            button_text = f"{'☑️' if is_selected else '⬜️'} {symbol}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'toggle_crypto_{crypto}')])

        keyboard.append([InlineKeyboardButton("✔️ تأیید و ادامه", callback_data='select_assets_main')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def crypto_manual_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب دستی ارزها"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_cryptos = settings['selected_cryptos'] if settings else DEFAULT_CRYPTOS

        message = """لیست کامل ارزهای دیجیتال:

روی هر ارز کلیک کنید تا انتخاب/لغو شود."""

        # ساخت دکمه‌های تمام ارزها
        keyboard = []
        available_cryptos = list(CRYPTO_SYMBOLS.keys())

        for i in range(0, len(available_cryptos), 2):
            row = []
            for j in range(2):
                if i + j < len(available_cryptos):
                    crypto = available_cryptos[i + j]
                    symbol = CRYPTO_SYMBOLS[crypto]
                    is_selected = crypto in current_cryptos
                    button_text = f"{'☑️' if is_selected else '⬜️'} {symbol}"
                    row.append(InlineKeyboardButton(button_text, callback_data=f'toggle_crypto_{crypto}'))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("✔️ تأیید و ادامه", callback_data='select_assets_main')])

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

        # به‌روزرسانی پیام (بازگشت به همان صفحه)
        # چک کنیم کاربر در کدام لیست بود
        if crypto_id in TOP_10_CRYPTOS:
            await self.crypto_top10_callback(update, context)
        else:
            await self.crypto_manual_callback(update, context)

    async def asset_type_gold_silver_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب طلا و نقره"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        include_gold = bool(settings['include_gold']) if settings else True
        include_silver = bool(settings['include_silver']) if settings else True

        message = "انتخاب طلا و نقره:"

        keyboard = [
            [InlineKeyboardButton(
                f"{'☑️' if include_gold else '⬜️'} 🥇 طلا",
                callback_data='toggle_asset_gold'
            )],
            [InlineKeyboardButton(
                f"{'☑️' if include_silver else '⬜️'} 🥈 نقره",
                callback_data='toggle_asset_silver'
            )],
            [InlineKeyboardButton("✔️ تأیید و بازگشت", callback_data='select_assets_main')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def asset_type_usd_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب دلار"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        include_usd = bool(settings['include_usd']) if settings else True

        message = "انتخاب دلار:"

        keyboard = [
            [InlineKeyboardButton(
                f"{'☑️' if include_usd else '⬜️'} 💵 دلار آمریکا",
                callback_data='toggle_asset_usd'
            )],
            [InlineKeyboardButton("✔️ تأیید و بازگشت", callback_data='select_assets_main')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def asset_type_fiat_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب ارزهای فیات"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_fiats = settings.get('selected_fiat_currencies', []) if settings else []

        message = """💱 لیست ارزهای فیات:

روی هر ارز کلیک کنید تا انتخاب/لغو شود."""

        # ساخت دکمه‌های ارزهای فیات
        keyboard = []
        available_fiats = list(FIAT_CURRENCIES.keys())

        for i in range(0, len(available_fiats), 2):
            row = []
            for j in range(2):
                if i + j < len(available_fiats):
                    fiat_id = available_fiats[i + j]
                    fiat_info = FIAT_CURRENCIES[fiat_id]
                    is_selected = fiat_id in current_fiats
                    button_text = f"{'☑️' if is_selected else '⬜️'} {fiat_info['flag']} {fiat_info['symbol']}"
                    row.append(InlineKeyboardButton(button_text, callback_data=f'toggle_fiat_{fiat_id}'))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("✔️ تأیید و ادامه", callback_data='select_assets_main')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def asset_type_gold_coins_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب سکه‌های طلا"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_coins = settings.get('selected_gold_coins', []) if settings else []

        message = """🪙 لیست سکه‌های طلا:

روی هر سکه کلیک کنید تا انتخاب/لغو شود."""

        # ساخت دکمه‌های سکه‌های طلا
        keyboard = []
        available_coins = list(GOLD_COINS.keys())

        for coin_id in available_coins:
            coin_info = GOLD_COINS[coin_id]
            is_selected = coin_id in current_coins
            button_text = f"{'☑️' if is_selected else '⬜️'} {coin_info['name']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'toggle_coin_{coin_id}')])

        keyboard.append([InlineKeyboardButton("✔️ تأیید و ادامه", callback_data='select_assets_main')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def asset_type_gold_items_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای انتخاب آیتم‌های طلا"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_items = settings.get('selected_gold_items', []) if settings else []

        message = """✨ لیست آیتم‌های طلا:

روی هر آیتم کلیک کنید تا انتخاب/لغو شود."""

        # ساخت دکمه‌های آیتم‌های طلا
        keyboard = []
        available_items = list(GOLD_ITEMS.keys())

        for item_id in available_items:
            item_info = GOLD_ITEMS[item_id]
            is_selected = item_id in current_items
            button_text = f"{'☑️' if is_selected else '⬜️'} {item_info['name']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'toggle_gold_item_{item_id}')])

        keyboard.append([InlineKeyboardButton("✔️ تأیید و ادامه", callback_data='select_assets_main')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def asset_type_stock_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای بورس ایران (به زودی)"""
        query = update.callback_query
        await query.answer("این قابلیت به زودی اضافه می‌شود", show_alert=True)

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
        if asset_type == 'gold' or asset_type == 'silver':
            await self.asset_type_gold_silver_callback(update, context)
        elif asset_type == 'usd':
            await self.asset_type_usd_callback(update, context)

    async def toggle_fiat_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تغییر وضعیت ارز فیات"""
        query = update.callback_query
        fiat_id = query.data.split('_', 2)[2]

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_fiats = settings.get('selected_fiat_currencies', []) if settings else []

        # toggle کردن ارز فیات
        if fiat_id in current_fiats:
            current_fiats.remove(fiat_id)
        else:
            current_fiats.append(fiat_id)

        # ذخیره در دیتابیس
        db.update_selected_fiat_currencies(user_id, current_fiats)

        await query.answer("✅ تغییرات ذخیره شد")

        # به‌روزرسانی پیام
        await self.asset_type_fiat_callback(update, context)

    async def toggle_coin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تغییر وضعیت سکه طلا"""
        query = update.callback_query
        coin_id = query.data.split('_', 2)[2]

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_coins = settings.get('selected_gold_coins', []) if settings else []

        # toggle کردن سکه
        if coin_id in current_coins:
            current_coins.remove(coin_id)
        else:
            current_coins.append(coin_id)

        # ذخیره در دیتابیس
        db.update_selected_gold_coins(user_id, current_coins)

        await query.answer("✅ تغییرات ذخیره شد")

        # به‌روزرسانی پیام
        await self.asset_type_gold_coins_callback(update, context)

    async def toggle_gold_item_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تغییر وضعیت آیتم طلا"""
        query = update.callback_query
        item_id = query.data.split('_', 3)[3]

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        current_items = settings.get('selected_gold_items', []) if settings else []

        # toggle کردن آیتم
        if item_id in current_items:
            current_items.remove(item_id)
        else:
            current_items.append(item_id)

        # ذخیره در دیتابیس
        db.update_selected_gold_items(user_id, current_items)

        await query.answer("✅ تغییرات ذخیره شد")

        # به‌روزرسانی پیام
        await self.asset_type_gold_items_callback(update, context)

    async def setup_schedule_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تنظیم زمان‌بندی"""
        query = update.callback_query

        # چک عضویت کاربر
        if not await self.require_membership(update, context):
            return

        await query.answer()

        message = """⏰ تنظیم زمان‌بندی:

چه زمانی هر روز می‌خوای قیمت‌ها برات ارسال بشن؟
یه دکمه رو انتخاب کن یا تایم دلخواهت رو بنویس.

فرمت: HH:MM (مثال: 09:00 یا 14:30)"""

        # دکمه‌های ساعت پیش‌فرض
        keyboard = []
        for i in range(0, len(PRESET_TIMES), 2):
            row = []
            for j in range(2):
                if i + j < len(PRESET_TIMES):
                    time_str = PRESET_TIMES[i + j]
                    row.append(InlineKeyboardButton(f"🕐 {time_str}", callback_data=f'set_time_{time_str}'))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

        # ذخیره وضعیت برای دریافت زمان دستی
        context.user_data['waiting_for_time'] = True

    async def set_time_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای تنظیم زمان از دکمه‌های پیش‌فرض"""
        query = update.callback_query
        time_str = query.data.split('_', 2)[2]

        user_id = update.effective_user.id

        # ذخیره در دیتابیس
        db.update_notification_settings(user_id, enabled=True, notification_time=time_str)

        # برنامه‌ریزی job جدید
        self.schedule_user_notification(user_id, time_str)

        await query.answer("✅ زمان‌بندی تنظیم شد")

        message = f"""✅ زمان‌بندی با موفقیت تنظیم شد.

🕐 هر روز در ساعت {time_str} گزارش قیمت‌ها برای شما ارسال می‌شود."""

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def receive_schedule_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت زمان دستی از کاربر"""
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

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /settings یا دکمه تنظیمات"""
        # چک عضویت کاربر
        if not await self.require_membership(update, context):
            return

        user_id = update.effective_user.id
        settings = db.get_user_settings(user_id)

        if not settings:
            message = "شما هنوز تنظیماتی ندارید."
            notification_status = "❌ غیرفعال"
            notification_time = "تنظیم نشده"
        else:
            notification_status = "✅ فعال" if settings['notification_enabled'] else "❌ غیرفعال"
            notification_time = settings['notification_time']

            message = f"""⚙️ تنظیمات شما:

🔔 وضعیت اعلان: {notification_status}
🕐 زمان ارسال: {notification_time}
🪙 تعداد ارزها: {len(settings['selected_cryptos'])}
🥇 طلا: {'✅' if settings['include_gold'] else '❌'}
🥈 نقره: {'✅' if settings['include_silver'] else '❌'}
💵 دلار: {'✅' if settings['include_usd'] else '❌'}"""

        # دکمه‌های تنظیمات
        keyboard = [
            [InlineKeyboardButton("🗑 حذف دارایی از لیست", callback_data='remove_assets')],
            [InlineKeyboardButton("🕒 تغییر زمان ارسال", callback_data='setup_schedule')],
            [InlineKeyboardButton("🔕 حذف اعلان تغییر قیمت", callback_data='disable_notification')],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # بررسی اینکه آیا از command آمده یا callback
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def remove_assets_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """callback برای حذف دارایی‌ها"""
        query = update.callback_query
        await query.answer()

        # هدایت به انتخاب دارایی‌ها
        await self.select_assets_main_callback(update, context)

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

        message = "✅ اعلان‌های خودکار غیرفعال شدند."

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به تنظیمات", callback_data='open_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help یا دکمه راهنما"""
        help_text = """📚 راهنمای دستیار ارزَلان:

🔹 دستورات اصلی:
/start - شروع کار با ربات
/help - نمایش این راهنما

🔹 امکانات:
• مشاهده قیمت لحظه‌ای ارزهای دیجیتال
• مشاهده قیمت طلا و نقره
• مشاهده قیمت دلار در ایران
• تغییرات 24 ساعته و 7 روزه
• دریافت خودکار در ساعت دلخواه
• انتخاب ارزهای دلخواه

🔹 نحوه استفاده:
1️⃣ روی دکمه "📤 ارسال قیمت الان" کلیک کنید
2️⃣ برای انتخاب ارزها روی "📋 انتخاب ارزها" کلیک کنید
3️⃣ برای تنظیم زمان‌بندی روی "🕒 تنظیم زمان" کلیک کنید
4️⃣ در تنظیمات می‌توانید دارایی‌ها را مدیریت کنید

سوالی دارید؟ از دکمه پشتیبانی استفاده کنید! 💬"""

        if update.callback_query:
            await update.callback_query.edit_message_text(help_text)
        else:
            await update.message.reply_text(help_text)

    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دکمه پشتیبانی"""
        support_text = """👤 پشتیبانی دستیار ارزَلان

برای ارتباط با پشتیبانی می‌توانید:
• پیام خود را در همین چت بنویسید
• یا با آیدی @support_arzalan در تماس باشید

ما در اسرع وقت پاسخگوی شما خواهیم بود."""

        await update.message.reply_text(support_text)

    async def handle_keyboard_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دکمه‌های keyboard"""
        # چک کردن اینکه آیا در حالت انتظار برای broadcast هستیم
        if context.user_data.get('waiting_for_broadcast'):
            await self.receive_broadcast_message(update, context)
            return

        text = update.message.text

        if text == '📤 ارسال قیمت الان':
            await self.send_prices(update, context)
        elif text == '🕒 تنظیم زمان ارسال روزانه پیام':
            # چک عضویت کاربر
            if not await self.require_membership(update, context):
                return
            # ارسال پیام با دکمه‌های inline
            user = update.effective_user
            await context.bot.send_message(
                chat_id=user.id,
                text="برای تنظیم زمان‌بندی روی دکمه زیر کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏰ تنظیم زمان‌بندی", callback_data='setup_schedule')]
                ])
            )
        elif text == '🔔 اعلان تغییر قیمت':
            await update.message.reply_text("این قابلیت به زودی اضافه می‌شود...")
        elif text == '❓ راهنما':
            await self.help_command(update, context)
        elif text == '⚙️ تنظیمات':
            await self.settings_command(update, context)
        elif text == '👤 پشتیبانی':
            await self.support_command(update, context)

    async def back_to_main_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بازگشت به منوی اصلی"""
        query = update.callback_query
        await query.answer()

        message = "منوی اصلی"

        keyboard = [
            [InlineKeyboardButton("📤 ارسال قیمت الان", callback_data='send_prices_now')],
            [InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_assets_main')],
            [InlineKeyboardButton("⏰ زمان‌بندی", callback_data='setup_schedule')],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data='open_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def send_prices_now_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال قیمت‌ها از طریق callback"""
        query = update.callback_query

        # چک عضویت کاربر
        if not await self.require_membership(update, context):
            return

        await query.answer("در حال دریافت قیمت‌ها...")

        user_id = update.effective_user.id

        try:
            # دریافت تنظیمات کاربر
            settings = db.get_user_settings(user_id)

            if not settings:
                crypto_ids = DEFAULT_CRYPTOS
                include_gold = True
                include_silver = True
                include_usd = True
                fiat_currency_ids = []
                gold_coin_ids = []
                gold_item_ids = []
            else:
                crypto_ids = settings['selected_cryptos']
                include_gold = bool(settings['include_gold'])
                include_silver = bool(settings['include_silver'])
                include_usd = bool(settings['include_usd'])
                fiat_currency_ids = settings.get('selected_fiat_currencies', [])
                gold_coin_ids = settings.get('selected_gold_coins', [])
                gold_item_ids = settings.get('selected_gold_items', [])

            # دریافت قیمت‌ها
            prices = await price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd,
                fiat_currency_ids=fiat_currency_ids,
                gold_coin_ids=gold_coin_ids,
                gold_item_ids=gold_item_ids
            )

            # فرمت کردن پیام
            message = price_fetcher.format_price_message(prices)

            # ایجاد دکمه‌های inline
            keyboard = [
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='refresh_prices')],
                [
                    InlineKeyboardButton("📋 انتخاب ارزها", callback_data='select_assets_main'),
                    InlineKeyboardButton("⏰ زمان‌بندی ارسال", callback_data='setup_schedule')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(message, reply_markup=reply_markup)

            # ثبت در تاریخچه
            db.log_message(user_id, 'price_request')

        except Exception as e:
            logger.error(f"خطا در دریافت قیمت: {e}")
            await query.edit_message_text(
                "❌ متأسفانه در دریافت قیمت‌ها خطایی رخ داد."
            )

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
            fiat_currency_ids = settings.get('selected_fiat_currencies', [])
            gold_coin_ids = settings.get('selected_gold_coins', [])
            gold_item_ids = settings.get('selected_gold_items', [])

            # دریافت قیمت‌ها
            prices = await price_fetcher.get_all_prices(
                crypto_ids=crypto_ids,
                include_gold=include_gold,
                include_silver=include_silver,
                include_usd=include_usd,
                fiat_currency_ids=fiat_currency_ids,
                gold_coin_ids=gold_coin_ids,
                gold_item_ids=gold_item_ids
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

    # توابع پنل ادمین

    async def admin_panel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /admin - نمایش پنل ادمین"""
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await update.message.reply_text("⛔️ شما دسترسی به پنل ادمین ندارید.")
            return

        await self.show_admin_panel(update, context)

    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل ادمین"""
        message = """🔐 پنل مدیریت ربات ارزَلان

به پنل مدیریت خوش آمدید!"""

        keyboard = [
            [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats_general')],
            [InlineKeyboardButton("👥 آمار کاربران", callback_data='admin_stats_users')],
            [InlineKeyboardButton("📨 آمار پیام‌ها", callback_data='admin_stats_messages')],
            [InlineKeyboardButton("🔥 محبوب‌ترین ارزها", callback_data='admin_stats_popular_cryptos')],
            [InlineKeyboardButton("📈 فعالیت کاربران", callback_data='admin_stats_activity')],
            [InlineKeyboardButton("👤 کاربران اخیر", callback_data='admin_recent_users')],
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data='admin_broadcast')],
            [InlineKeyboardButton("🔙 بستن پنل", callback_data='admin_close')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def admin_stats_general_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار کلی"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت آمار
        total_users = db.get_total_users_count()
        active_users = db.get_active_users_count()
        new_users_7d = db.get_new_users_count(7)
        new_users_30d = db.get_new_users_count(30)
        total_messages = db.get_total_messages_count()
        active_notifications = db.get_active_notifications_count()

        message = f"""📊 آمار کلی ربات

👥 کاربران:
• کل کاربران: {total_users:,}
• کاربران فعال: {active_users:,}
• کاربران جدید (7 روز): {new_users_7d:,}
• کاربران جدید (30 روز): {new_users_30d:,}

📨 پیام‌ها:
• کل پیام‌ها: {total_messages:,}

🔔 اعلان‌ها:
• کاربران با اعلان فعال: {active_notifications:,}"""

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='admin_stats_general')],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def admin_stats_users_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار کاربران"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت آمار
        total_users = db.get_total_users_count()
        active_users = db.get_active_users_count()
        inactive_users = total_users - active_users
        new_users_24h = db.get_new_users_count(1)
        new_users_7d = db.get_new_users_count(7)
        new_users_30d = db.get_new_users_count(30)

        message = f"""👥 آمار تفصیلی کاربران

📈 تعداد کاربران:
• کل کاربران: {total_users:,}
• کاربران فعال: {active_users:,}
• کاربران غیرفعال: {inactive_users:,}

🆕 کاربران جدید:
• امروز (24 ساعت): {new_users_24h:,}
• 7 روز اخیر: {new_users_7d:,}
• 30 روز اخیر: {new_users_30d:,}

📊 نرخ رشد:
• هفتگی: {new_users_7d:,} کاربر جدید
• ماهانه: {new_users_30d:,} کاربر جدید"""

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='admin_stats_users')],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def admin_stats_messages_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار پیام‌ها"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت آمار
        total_messages = db.get_total_messages_count()
        messages_by_type = db.get_messages_by_type()

        message = f"""📨 آمار پیام‌ها

📊 کل پیام‌ها: {total_messages:,}

📋 تفکیک بر اساس نوع:"""

        # نمایش پیام‌ها بر اساس نوع
        type_names = {
            'price_request': '📤 درخواست قیمت',
            'scheduled_notification': '🔔 اعلان زمان‌بندی شده',
            'refresh': '🔄 به‌روزرسانی',
            'start': '▶️ شروع'
        }

        for msg_type, count in messages_by_type.items():
            type_display = type_names.get(msg_type, msg_type)
            message += f"\n• {type_display}: {count:,}"

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='admin_stats_messages')],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def admin_stats_popular_cryptos_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش محبوب‌ترین ارزها"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت محبوب‌ترین ارزها
        popular_cryptos = db.get_popular_cryptos(limit=10)

        message = """🔥 محبوب‌ترین ارزهای انتخاب شده

ارزهایی که کاربران بیشتر انتخاب کرده‌اند:

"""

        if popular_cryptos:
            for i, (crypto_id, count) in enumerate(popular_cryptos.items(), 1):
                crypto_symbol = CRYPTO_SYMBOLS.get(crypto_id, crypto_id.upper())
                message += f"{i}. {crypto_symbol}: {count:,} کاربر\n"
        else:
            message += "هنوز آماری ثبت نشده است."

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='admin_stats_popular_cryptos')],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def admin_stats_activity_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار فعالیت کاربران"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت آمار فعالیت
        activity_stats = db.get_user_activity_stats()

        message = f"""📈 آمار فعالیت کاربران

👤 کاربران فعال:
• 24 ساعت اخیر: {activity_stats.get('active_24h', 0):,}
• 7 روز اخیر: {activity_stats.get('active_7d', 0):,}
• 30 روز اخیر: {activity_stats.get('active_30d', 0):,}

این آمار بر اساس تعداد کاربرانی که در بازه‌های زمانی مشخص شده با ربات تعامل داشته‌اند محاسبه شده است."""

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='admin_stats_activity')],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def admin_recent_users_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش کاربران اخیر"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت کاربران اخیر
        recent_users = db.get_recent_users(limit=10)

        message = """👤 کاربران اخیر (10 نفر آخر)

"""

        if recent_users:
            for i, user in enumerate(recent_users, 1):
                username = f"@{user['username']}" if user.get('username') else "بدون یوزرنیم"
                first_name = user.get('first_name', 'نامشخص')
                created_at = user.get('created_at', '')[:10]  # فقط تاریخ
                message += f"{i}. {first_name} ({username})\n   📅 {created_at}\n\n"
        else:
            message += "هنوز کاربری ثبت نشده است."

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data='admin_recent_users')],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بازگشت به پنل ادمین"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()
        await self.show_admin_panel(update, context)

    async def admin_close_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بستن پنل ادمین"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("✅ پنل ادمین بسته شد.")

    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند ارسال پیام همگانی"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت تعداد کاربران فعال
        active_users_count = db.get_active_users_count()

        message = f"""📢 ارسال پیام همگانی

تعداد کاربران فعال: {active_users_count:,}

لطفاً پیامی که می‌خواهید برای همه کاربران ارسال شود را بنویسید.

⚠️ توجه:
• پیام برای همه کاربران فعال ارسال می‌شود
• می‌توانید متن، عکس، ویدیو یا فایل ارسال کنید
• برای لغو، /cancel را ارسال کنید"""

        keyboard = [
            [InlineKeyboardButton("❌ لغو", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

        # ذخیره وضعیت در context
        context.user_data['waiting_for_broadcast'] = True

    async def receive_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت پیام برای ارسال همگانی"""
        # چک اینکه آیا در حالت انتظار برای broadcast هستیم
        if not context.user_data.get('waiting_for_broadcast'):
            return

        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            return

        # ذخیره پیام در context
        context.user_data['broadcast_message'] = update.message
        context.user_data['waiting_for_broadcast'] = False

        # نمایش پیش‌نمایش و درخواست تایید
        active_users_count = db.get_active_users_count()

        preview_message = f"""✅ پیام دریافت شد!

📊 این پیام برای {active_users_count:,} کاربر فعال ارسال خواهد شد.

آیا از ارسال این پیام اطمینان دارید؟"""

        keyboard = [
            [
                InlineKeyboardButton("✅ بله، ارسال شود", callback_data='admin_broadcast_confirm'),
                InlineKeyboardButton("❌ لغو", callback_data='admin_broadcast_cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(preview_message, reply_markup=reply_markup)

    async def admin_broadcast_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید و ارسال پیام همگانی"""
        query = update.callback_query
        user_id = update.effective_user.id

        # چک ادمین بودن
        if not await self.is_admin(user_id):
            await query.answer("⛔️ دسترسی غیرمجاز", show_alert=True)
            return

        await query.answer()

        # دریافت پیام از context
        broadcast_message = context.user_data.get('broadcast_message')
        if not broadcast_message:
            await query.edit_message_text("❌ خطا: پیامی برای ارسال یافت نشد.")
            return

        # نمایش پیام در حال ارسال
        await query.edit_message_text("⏳ در حال ارسال پیام به کاربران...")

        # دریافت لیست کاربران فعال
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE is_active = 1')
            users = [row['user_id'] for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logger.error(f"خطا در دریافت کاربران: {e}")
            await query.edit_message_text("❌ خطا در دریافت لیست کاربران")
            return

        # ارسال پیام به کاربران
        success_count = 0
        failed_count = 0

        for target_user_id in users:
            try:
                # ارسال پیام بر اساس نوع
                if broadcast_message.text:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=broadcast_message.text
                    )
                elif broadcast_message.photo:
                    await context.bot.send_photo(
                        chat_id=target_user_id,
                        photo=broadcast_message.photo[-1].file_id,
                        caption=broadcast_message.caption
                    )
                elif broadcast_message.video:
                    await context.bot.send_video(
                        chat_id=target_user_id,
                        video=broadcast_message.video.file_id,
                        caption=broadcast_message.caption
                    )
                elif broadcast_message.document:
                    await context.bot.send_document(
                        chat_id=target_user_id,
                        document=broadcast_message.document.file_id,
                        caption=broadcast_message.caption
                    )
                elif broadcast_message.audio:
                    await context.bot.send_audio(
                        chat_id=target_user_id,
                        audio=broadcast_message.audio.file_id,
                        caption=broadcast_message.caption
                    )
                elif broadcast_message.voice:
                    await context.bot.send_voice(
                        chat_id=target_user_id,
                        voice=broadcast_message.voice.file_id,
                        caption=broadcast_message.caption
                    )

                success_count += 1

                # تاخیر کوچک برای جلوگیری از rate limit
                await asyncio.sleep(0.05)

            except Exception as e:
                logger.error(f"خطا در ارسال به {target_user_id}: {e}")
                failed_count += 1

        # نمایش نتیجه
        result_message = f"""✅ ارسال پیام همگانی تکمیل شد

📊 آمار ارسال:
• موفق: {success_count:,} کاربر
• ناموفق: {failed_count:,} کاربر
• جمع کل: {success_count + failed_count:,} کاربر"""

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(result_message, reply_markup=reply_markup)

        # پاک کردن پیام از context
        context.user_data.pop('broadcast_message', None)

    async def admin_broadcast_cancel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو ارسال پیام همگانی"""
        query = update.callback_query
        await query.answer()

        # پاک کردن وضعیت از context
        context.user_data.pop('broadcast_message', None)
        context.user_data.pop('waiting_for_broadcast', None)

        await query.edit_message_text("❌ ارسال پیام همگانی لغو شد.")

        # بازگشت به پنل ادمین
        await self.show_admin_panel(update, context)

    async def run(self):
        """اجرای ربات"""
        # ساخت Application
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Handler ها
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('settings', self.settings_command))
        self.application.add_handler(CommandHandler('admin', self.admin_panel_command))

        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(
            self.check_membership_callback, pattern='^check_membership$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.refresh_prices_callback, pattern='^refresh_prices$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.select_assets_main_callback, pattern='^select_assets_main$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_crypto_callback, pattern='^asset_type_crypto$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.crypto_top5_callback, pattern='^crypto_top5$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.crypto_top10_callback, pattern='^crypto_top10$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.crypto_manual_callback, pattern='^crypto_manual$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_crypto_callback, pattern='^toggle_crypto_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_gold_silver_callback, pattern='^asset_type_gold_silver$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_usd_callback, pattern='^asset_type_usd$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_fiat_callback, pattern='^asset_type_fiat$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_gold_coins_callback, pattern='^asset_type_gold_coins$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_gold_items_callback, pattern='^asset_type_gold_items$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.asset_type_stock_callback, pattern='^asset_type_stock$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_asset_callback, pattern='^toggle_asset_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_fiat_callback, pattern='^toggle_fiat_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_coin_callback, pattern='^toggle_coin_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.toggle_gold_item_callback, pattern='^toggle_gold_item_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.setup_schedule_callback, pattern='^setup_schedule$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.set_time_callback, pattern='^set_time_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.remove_assets_callback, pattern='^remove_assets$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.disable_notification_callback, pattern='^disable_notification$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.settings_command, pattern='^open_settings$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.back_to_main_callback, pattern='^back_to_main$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.send_prices_now_callback, pattern='^send_prices_now$'
        ))

        # Callback handlers برای پنل ادمین
        self.application.add_handler(CallbackQueryHandler(
            self.admin_panel_callback, pattern='^admin_panel$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_stats_general_callback, pattern='^admin_stats_general$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_stats_users_callback, pattern='^admin_stats_users$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_stats_messages_callback, pattern='^admin_stats_messages$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_stats_popular_cryptos_callback, pattern='^admin_stats_popular_cryptos$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_stats_activity_callback, pattern='^admin_stats_activity$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_recent_users_callback, pattern='^admin_recent_users$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_broadcast_callback, pattern='^admin_broadcast$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_broadcast_confirm_callback, pattern='^admin_broadcast_confirm$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_broadcast_cancel_callback, pattern='^admin_broadcast_cancel$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.admin_close_callback, pattern='^admin_close$'
        ))

        # Handler برای دکمه‌های keyboard
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_keyboard_buttons
        ))

        # Handler برای دریافت انواع پیام برای broadcast
        self.application.add_handler(MessageHandler(
            (filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.VOICE) & ~filters.COMMAND,
            self.receive_broadcast_message
        ))

        # بارگذاری زمان‌بندی‌های ذخیره شده
        self.load_scheduled_notifications()

        # اجرای ربات
        logger.info("ربات دستیار ارزَلان در حال اجرا است...")

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

    bot = ArzalanBot()
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
