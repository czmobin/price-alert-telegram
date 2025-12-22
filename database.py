"""
مدیریت پایگاه داده SQLite برای ربات تلگرام
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from config import (
    DATABASE_PATH, DEFAULT_CRYPTOS, DEFAULT_NOTIFICATION_TIME,
    DEFAULT_FIAT_CURRENCIES, DEFAULT_COINS, DEFAULT_GOLD_ITEMS
)


class Database:
    """کلاس مدیریت پایگاه داده"""

    def __init__(self, db_path: str = DATABASE_PATH):
        """راه‌اندازی اتصال به پایگاه داده"""
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """ایجاد اتصال به پایگاه داده"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # برای دسترسی به ستون‌ها با نام
        return conn

    def init_database(self):
        """ایجاد جداول پایگاه داده"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                language_code TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # جدول تنظیمات کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                notification_enabled INTEGER DEFAULT 0,
                notification_time TEXT DEFAULT '09:00',
                selected_cryptos TEXT,
                include_gold INTEGER DEFAULT 1,
                include_silver INTEGER DEFAULT 1,
                include_usd INTEGER DEFAULT 1,
                selected_fiat_currencies TEXT,
                selected_gold_coins TEXT,
                selected_gold_items TEXT,
                include_bourse INTEGER DEFAULT 0,
                timezone TEXT DEFAULT 'Asia/Tehran',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # جدول تاریخچه پیام‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_type TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # جدول ادمین‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # جدول زمان‌بندی اعلان‌ها (چندین تایم برای هر کاربر)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_time TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, notification_time)
            )
        ''')

        # جدول تنظیمات عمومی ربات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER
            )
        ''')

        # مقداردهی اولیه footer
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (key, value)
            VALUES ('footer_text', 'ارزَلان دستیار اطلاع‌رسانی قیمت‌ها')
        ''')

        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (key, value)
            VALUES ('footer_username', '@arzzalanbot')
        ''')

        # جدول تاریخچه قیمت‌ها (برای سیستم هشدار سقف قیمتی)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                price REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ایجاد ایندکس برای جستجوی سریع تاریخچه قیمت‌ها
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_price_history_asset_time
            ON price_history(asset_type, asset_id, recorded_at)
        ''')

        # جدول سقف قیمتی (ذخیره بالاترین قیمت تاریخی)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_ceilings (
                asset_type TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                ceiling_price REAL NOT NULL,
                previous_ceiling REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (asset_type, asset_id)
            )
        ''')

        # جدول هشدارهای سقف قیمتی ارسال شده
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ceiling_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                ceiling_price REAL NOT NULL,
                alerted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                recipients_count INTEGER DEFAULT 0
            )
        ''')

        # مقداردهی اولیه سقف قیمت‌ها (با قیمت‌های اولیه)
        cursor.execute('''
            INSERT OR IGNORE INTO price_ceilings (asset_type, asset_id, ceiling_price)
            VALUES
                ('usd', 'usd_irr', 0),
                ('gold', 'gol18', 0)
        ''')

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: str = None, first_name: str = None,
                 last_name: str = None, phone_number: str = None,
                 language_code: str = None) -> bool:
        """افزودن یا به‌روزرسانی کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name,
                                   phone_number, language_code)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    phone_number = COALESCE(excluded.phone_number, phone_number),
                    language_code = excluded.language_code,
                    last_interaction = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name, last_name, phone_number, language_code))

            # ایجاد تنظیمات پیش‌فرض برای کاربر جدید
            cursor.execute('''
                INSERT OR IGNORE INTO user_settings (user_id, selected_cryptos,
                    selected_fiat_currencies, selected_gold_coins, selected_gold_items)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, json.dumps(DEFAULT_CRYPTOS),
                  json.dumps(DEFAULT_FIAT_CURRENCIES),
                  json.dumps(DEFAULT_COINS),
                  json.dumps(DEFAULT_GOLD_ITEMS)))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در افزودن کاربر: {e}")
            return False

    def update_phone_number(self, user_id: int, phone_number: str) -> bool:
        """به‌روزرسانی شماره تلفن کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET phone_number = ?, last_interaction = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (phone_number, user_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی شماره: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"خطا در دریافت کاربر: {e}")
            return None

    def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """دریافت تنظیمات کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()

            conn.close()

            if row:
                settings = dict(row)
                # تبدیل JSON به لیست
                settings['selected_cryptos'] = json.loads(settings['selected_cryptos']) if settings.get('selected_cryptos') else DEFAULT_CRYPTOS
                settings['selected_fiat_currencies'] = json.loads(settings['selected_fiat_currencies']) if settings.get('selected_fiat_currencies') else DEFAULT_FIAT_CURRENCIES
                settings['selected_gold_coins'] = json.loads(settings['selected_gold_coins']) if settings.get('selected_gold_coins') else DEFAULT_COINS
                settings['selected_gold_items'] = json.loads(settings['selected_gold_items']) if settings.get('selected_gold_items') else DEFAULT_GOLD_ITEMS
                return settings
            return None
        except Exception as e:
            print(f"خطا در دریافت تنظیمات: {e}")
            return None

    def update_notification_settings(self, user_id: int, enabled: bool,
                                     notification_time: str = None) -> bool:
        """به‌روزرسانی تنظیمات نوتیفیکیشن"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if notification_time:
                cursor.execute('''
                    UPDATE user_settings
                    SET notification_enabled = ?, notification_time = ?
                    WHERE user_id = ?
                ''', (1 if enabled else 0, notification_time, user_id))
            else:
                cursor.execute('''
                    UPDATE user_settings
                    SET notification_enabled = ?
                    WHERE user_id = ?
                ''', (1 if enabled else 0, user_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی نوتیفیکیشن: {e}")
            return False

    def update_selected_cryptos(self, user_id: int, cryptos: List[str]) -> bool:
        """به‌روزرسانی ارزهای انتخابی کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE user_settings
                SET selected_cryptos = ?
                WHERE user_id = ?
            ''', (json.dumps(cryptos), user_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی ارزها: {e}")
            return False

    def update_asset_preferences(self, user_id: int, include_gold: bool = None,
                                 include_silver: bool = None, include_usd: bool = None) -> bool:
        """به‌روزرسانی تنظیمات دارایی‌های دیگر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            updates = []
            values = []

            if include_gold is not None:
                updates.append('include_gold = ?')
                values.append(1 if include_gold else 0)

            if include_silver is not None:
                updates.append('include_silver = ?')
                values.append(1 if include_silver else 0)

            if include_usd is not None:
                updates.append('include_usd = ?')
                values.append(1 if include_usd else 0)

            if updates:
                values.append(user_id)
                query = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?"
                cursor.execute(query, values)

                conn.commit()

            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی دارایی‌ها: {e}")
            return False

    def get_users_with_notifications(self, notification_time: str) -> List[int]:
        """دریافت کاربرانی که نوتیفیکیشن فعال دارند"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT u.user_id
                FROM users u
                JOIN user_settings s ON u.user_id = s.user_id
                WHERE s.notification_enabled = 1
                AND s.notification_time = ?
                AND u.is_active = 1
            ''', (notification_time,))

            users = [row['user_id'] for row in cursor.fetchall()]

            conn.close()
            return users
        except Exception as e:
            print(f"خطا در دریافت کاربران: {e}")
            return []

    def log_message(self, user_id: int, message_type: str) -> bool:
        """ثبت تاریخچه ارسال پیام"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO message_history (user_id, message_type)
                VALUES (?, ?)
            ''', (user_id, message_type))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در ثبت پیام: {e}")
            return False

    def update_selected_fiat_currencies(self, user_id: int, currencies: List[str]) -> bool:
        """به‌روزرسانی ارزهای فیات انتخابی کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE user_settings
                SET selected_fiat_currencies = ?
                WHERE user_id = ?
            ''', (json.dumps(currencies), user_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی ارزهای فیات: {e}")
            return False

    def update_selected_gold_coins(self, user_id: int, coins: List[str]) -> bool:
        """به‌روزرسانی سکه‌های طلا انتخابی کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE user_settings
                SET selected_gold_coins = ?
                WHERE user_id = ?
            ''', (json.dumps(coins), user_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی سکه‌های طلا: {e}")
            return False

    def update_selected_gold_items(self, user_id: int, items: List[str]) -> bool:
        """به‌روزرسانی آیتم‌های طلا انتخابی کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE user_settings
                SET selected_gold_items = ?
                WHERE user_id = ?
            ''', (json.dumps(items), user_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی آیتم‌های طلا: {e}")
            return False

    def get_active_users_count(self) -> int:
        """تعداد کاربران فعال"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1')
            count = cursor.fetchone()['count']

            conn.close()
            return count
        except Exception as e:
            print(f"خطا در شمارش کاربران: {e}")
            return 0

    # توابع مدیریت ادمین‌ها

    def is_admin(self, user_id: int) -> bool:
        """چک کردن ادمین بودن کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()

            conn.close()
            return result is not None
        except Exception as e:
            print(f"خطا در چک ادمین: {e}")
            return False

    def add_admin(self, user_id: int, added_by: int = None) -> bool:
        """افزودن ادمین"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO admins (user_id, added_by)
                VALUES (?, ?)
            ''', (user_id, added_by))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در افزودن ادمین: {e}")
            return False

    def remove_admin(self, user_id: int) -> bool:
        """حذف ادمین"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در حذف ادمین: {e}")
            return False

    def get_admins(self) -> List[int]:
        """دریافت لیست ادمین‌ها"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT user_id FROM admins')
            admins = [row['user_id'] for row in cursor.fetchall()]

            conn.close()
            return admins
        except Exception as e:
            print(f"خطا در دریافت ادمین‌ها: {e}")
            return []

    # توابع آماری

    def get_total_users_count(self) -> int:
        """تعداد کل کاربران"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM users')
            count = cursor.fetchone()['count']

            conn.close()
            return count
        except Exception as e:
            print(f"خطا در شمارش کاربران: {e}")
            return 0

    def get_new_users_count(self, days: int = 7) -> int:
        """تعداد کاربران جدید در n روز اخیر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) as count FROM users
                WHERE created_at >= datetime('now', '-' || ? || ' days')
            ''', (days,))
            count = cursor.fetchone()['count']

            conn.close()
            return count
        except Exception as e:
            print(f"خطا در شمارش کاربران جدید: {e}")
            return 0

    def get_total_messages_count(self) -> int:
        """تعداد کل پیام‌ها"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM message_history')
            count = cursor.fetchone()['count']

            conn.close()
            return count
        except Exception as e:
            print(f"خطا در شمارش پیام‌ها: {e}")
            return 0

    def get_messages_by_type(self) -> Dict[str, int]:
        """تعداد پیام‌ها بر اساس نوع"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT message_type, COUNT(*) as count
                FROM message_history
                GROUP BY message_type
            ''')

            messages = {row['message_type']: row['count'] for row in cursor.fetchall()}

            conn.close()
            return messages
        except Exception as e:
            print(f"خطا در دریافت آمار پیام‌ها: {e}")
            return {}

    def get_active_notifications_count(self) -> int:
        """تعداد کاربران با نوتیفیکیشن فعال"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) as count FROM user_settings
                WHERE notification_enabled = 1
            ''')
            count = cursor.fetchone()['count']

            conn.close()
            return count
        except Exception as e:
            print(f"خطا در شمارش نوتیفیکیشن‌ها: {e}")
            return 0

    def get_popular_cryptos(self, limit: int = 10) -> Dict[str, int]:
        """محبوب‌ترین ارزهای انتخاب شده"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT selected_cryptos FROM user_settings')
            rows = cursor.fetchall()

            conn.close()

            # شمارش ارزها
            crypto_counts = {}
            for row in rows:
                if row['selected_cryptos']:
                    cryptos = json.loads(row['selected_cryptos'])
                    for crypto in cryptos:
                        crypto_counts[crypto] = crypto_counts.get(crypto, 0) + 1

            # مرتب‌سازی و محدود کردن
            sorted_cryptos = dict(sorted(crypto_counts.items(), key=lambda x: x[1], reverse=True)[:limit])

            return sorted_cryptos
        except Exception as e:
            print(f"خطا در دریافت ارزهای محبوب: {e}")
            return {}

    def get_recent_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """کاربران اخیر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, username, first_name, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

            users = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return users
        except Exception as e:
            print(f"خطا در دریافت کاربران اخیر: {e}")
            return []

    def get_user_activity_stats(self) -> Dict[str, int]:
        """آمار فعالیت کاربران"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # کاربران فعال در 24 ساعت اخیر
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as count FROM message_history
                WHERE sent_at >= datetime('now', '-1 day')
            ''')
            active_24h = cursor.fetchone()['count']

            # کاربران فعال در 7 روز اخیر
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as count FROM message_history
                WHERE sent_at >= datetime('now', '-7 days')
            ''')
            active_7d = cursor.fetchone()['count']

            # کاربران فعال در 30 روز اخیر
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as count FROM message_history
                WHERE sent_at >= datetime('now', '-30 days')
            ''')
            active_30d = cursor.fetchone()['count']

            conn.close()

            return {
                'active_24h': active_24h,
                'active_7d': active_7d,
                'active_30d': active_30d
            }
        except Exception as e:
            print(f"خطا در دریافت آمار فعالیت: {e}")
            return {}

    # توابع مدیریت زمان‌بندی اعلان‌ها

    def add_notification_schedule(self, user_id: int, notification_time: str) -> bool:
        """افزودن زمان‌بندی جدید برای کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO notification_schedules (user_id, notification_time, is_active)
                VALUES (?, ?, 1)
            ''', (user_id, notification_time))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در افزودن زمان‌بندی: {e}")
            return False

    def remove_notification_schedule(self, schedule_id: int) -> bool:
        """حذف زمان‌بندی"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM notification_schedules WHERE id = ?', (schedule_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در حذف زمان‌بندی: {e}")
            return False

    def get_bot_setting(self, key: str, default: str = '') -> str:
        """دریافت یک تنظیم عمومی ربات"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return row['value']
            return default
        except Exception as e:
            print(f"خطا در دریافت تنظیم {key}: {e}")
            return default

    def set_bot_setting(self, key: str, value: str, updated_by: int = None) -> bool:
        """ذخیره یک تنظیم عمومی ربات"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO bot_settings (key, value, updated_by, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
            ''', (key, value, updated_by))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در ذخیره تنظیم {key}: {e}")
            return False

    def get_footer_settings(self) -> Dict[str, str]:
        """دریافت تنظیمات footer"""
        return {
            'footer_text': self.get_bot_setting('footer_text', 'ارزَلان دستیار اطلاع‌رسانی قیمت‌ها'),
            'footer_username': self.get_bot_setting('footer_username', '@arzzalanbot')
        }

    def update_footer_settings(self, footer_text: str = None, footer_username: str = None, updated_by: int = None) -> bool:
        """به‌روزرسانی تنظیمات footer"""
        try:
            success = True
            if footer_text is not None:
                success = success and self.set_bot_setting('footer_text', footer_text, updated_by)
            if footer_username is not None:
                success = success and self.set_bot_setting('footer_username', footer_username, updated_by)
            return success
        except Exception as e:
            print(f"خطا در به‌روزرسانی footer: {e}")
            return False

    def get_user_schedules(self, user_id: int) -> List[Dict[str, Any]]:
        """دریافت لیست زمان‌بندی‌های کاربر"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, notification_time, is_active, created_at
                FROM notification_schedules
                WHERE user_id = ?
                ORDER BY notification_time
            ''', (user_id,))

            schedules = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return schedules
        except Exception as e:
            print(f"خطا در دریافت زمان‌بندی‌ها: {e}")
            return []

    def get_all_active_schedules(self) -> List[Dict[str, Any]]:
        """دریافت تمام زمان‌بندی‌های فعال"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ns.id, ns.user_id, ns.notification_time
                FROM notification_schedules ns
                JOIN users u ON ns.user_id = u.user_id
                WHERE ns.is_active = 1 AND u.is_active = 1
            ''')

            schedules = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return schedules
        except Exception as e:
            print(f"خطا در دریافت زمان‌بندی‌های فعال: {e}")
            return []

    def toggle_schedule_status(self, schedule_id: int) -> bool:
        """تغییر وضعیت فعال/غیرفعال زمان‌بندی"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # دریافت وضعیت فعلی
            cursor.execute('SELECT is_active FROM notification_schedules WHERE id = ?', (schedule_id,))
            row = cursor.fetchone()

            if row:
                new_status = 0 if row['is_active'] == 1 else 1
                cursor.execute('''
                    UPDATE notification_schedules
                    SET is_active = ?
                    WHERE id = ?
                ''', (new_status, schedule_id))

                conn.commit()
                conn.close()
                return True

            conn.close()
            return False
        except Exception as e:
            print(f"خطا در تغییر وضعیت زمان‌بندی: {e}")
            return False

    # ===== توابع سیستم هشدار سقف قیمتی =====

    def save_price_snapshot(self, asset_type: str, asset_id: str, price: float) -> bool:
        """
        ذخیره یک snapshot از قیمت در تاریخچه

        Args:
            asset_type: نوع دارایی ('usd', 'gold', 'crypto')
            asset_id: شناسه دارایی ('usd_irr', 'gol18', 'bitcoin')
            price: قیمت فعلی

        Returns:
            bool: موفقیت‌آمیز بودن عملیات
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO price_history (asset_type, asset_id, price)
                VALUES (?, ?, ?)
            ''', (asset_type, asset_id, price))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در ذخیره قیمت: {e}")
            return False

    def get_historical_price(self, asset_type: str, asset_id: str, hours_ago: int) -> Optional[float]:
        """
        دریافت قیمت تاریخی (مثلاً 24 ساعت، 7 روز یا 30 روز قبل)

        Args:
            asset_type: نوع دارایی
            asset_id: شناسه دارایی
            hours_ago: چند ساعت قبل

        Returns:
            float: قیمت تاریخی یا None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT price
                FROM price_history
                WHERE asset_type = ? AND asset_id = ?
                    AND recorded_at <= datetime('now', ? || ' hours')
                ORDER BY ABS(
                    (julianday(recorded_at) - julianday(datetime('now', ? || ' hours'))) * 24
                )
                LIMIT 1
            ''', (asset_type, asset_id, f'-{hours_ago}', f'-{hours_ago}'))

            row = cursor.fetchone()
            conn.close()

            return row['price'] if row else None
        except Exception as e:
            print(f"خطا در دریافت قیمت تاریخی: {e}")
            return None

    def get_price_ceiling(self, asset_type: str, asset_id: str) -> Optional[float]:
        """
        دریافت سقف قیمتی تاریخی

        Args:
            asset_type: نوع دارایی
            asset_id: شناسه دارایی

        Returns:
            float: سقف قیمتی یا None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ceiling_price
                FROM price_ceilings
                WHERE asset_type = ? AND asset_id = ?
            ''', (asset_type, asset_id))

            row = cursor.fetchone()
            conn.close()

            return row['ceiling_price'] if row else None
        except Exception as e:
            print(f"خطا در دریافت سقف قیمتی: {e}")
            return None

    def update_price_ceiling(self, asset_type: str, asset_id: str, new_ceiling: float) -> bool:
        """
        به‌روزرسانی سقف قیمتی

        Args:
            asset_type: نوع دارایی
            asset_id: شناسه دارایی
            new_ceiling: سقف قیمتی جدید

        Returns:
            bool: موفقیت‌آمیز بودن عملیات
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # ابتدا سقف قبلی را بگیر
            cursor.execute('''
                SELECT ceiling_price
                FROM price_ceilings
                WHERE asset_type = ? AND asset_id = ?
            ''', (asset_type, asset_id))

            row = cursor.fetchone()
            previous_ceiling = row['ceiling_price'] if row else 0

            # به‌روزرسانی سقف
            cursor.execute('''
                INSERT OR REPLACE INTO price_ceilings
                (asset_type, asset_id, ceiling_price, previous_ceiling, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (asset_type, asset_id, new_ceiling, previous_ceiling))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در به‌روزرسانی سقف قیمتی: {e}")
            return False

    def get_last_ceiling_alert_time(self, asset_type: str, asset_id: str) -> Optional[datetime]:
        """
        دریافت آخرین زمان ارسال هشدار سقف قیمتی

        Args:
            asset_type: نوع دارایی
            asset_id: شناسه دارایی

        Returns:
            datetime: زمان آخرین هشدار یا None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT alerted_at
                FROM ceiling_alerts
                WHERE asset_type = ? AND asset_id = ?
                ORDER BY alerted_at DESC
                LIMIT 1
            ''', (asset_type, asset_id))

            row = cursor.fetchone()
            conn.close()

            if row:
                return datetime.fromisoformat(row['alerted_at'])
            return None
        except Exception as e:
            print(f"خطا در دریافت زمان آخرین هشدار: {e}")
            return None

    def record_ceiling_alert(self, asset_type: str, asset_id: str,
                           ceiling_price: float, recipients_count: int) -> bool:
        """
        ثبت ارسال هشدار سقف قیمتی

        Args:
            asset_type: نوع دارایی
            asset_id: شناسه دارایی
            ceiling_price: قیمت سقف شکسته شده
            recipients_count: تعداد دریافت‌کنندگان

        Returns:
            bool: موفقیت‌آمیز بودن عملیات
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO ceiling_alerts
                (asset_type, asset_id, ceiling_price, recipients_count)
                VALUES (?, ?, ?, ?)
            ''', (asset_type, asset_id, ceiling_price, recipients_count))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"خطا در ثبت هشدار: {e}")
            return False

    # ===== توابع ارسال پیام هدفمند =====

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        دریافت لیست همه کاربران

        Returns:
            لیست دیکشنری کاربران
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users')
            users = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return users
        except Exception as e:
            print(f"خطا در دریافت لیست کاربران: {e}")
            return []

    def get_users_by_timeframe(self, timeframe: str) -> List[Dict[str, Any]]:
        """
        دریافت کاربران بر اساس بازه زمانی آخرین فعالیت

        Args:
            timeframe: بازه زمانی ('today', '48h', '3days', 'week', 'month')

        Returns:
            لیست کاربران فیلتر شده
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # تعیین شرط WHERE بر اساس timeframe
            if timeframe == 'today':
                # کاربرهای امروز
                condition = "DATE(last_interaction) = DATE('now', 'localtime')"
            elif timeframe == '48h':
                # کاربرهای 48 ساعت اخیر
                condition = "last_interaction >= datetime('now', '-2 days')"
            elif timeframe == '3days':
                # کاربرهای 3 روز اخیر
                condition = "last_interaction >= datetime('now', '-3 days')"
            elif timeframe == 'week':
                # کاربرهای هفته اخیر
                condition = "last_interaction >= datetime('now', '-7 days')"
            elif timeframe == 'month':
                # کاربرهای ماه اخیر
                condition = "last_interaction >= datetime('now', '-30 days')"
            else:
                # پیش‌فرض: همه کاربران فعال
                condition = "is_active = 1"

            query = f'''
                SELECT * FROM users
                WHERE {condition} AND is_active = 1
                ORDER BY last_interaction DESC
            '''

            cursor.execute(query)
            users = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return users

        except Exception as e:
            print(f"خطا در فیلتر کاربران بر اساس بازه زمانی: {e}")
            return []

    def get_users_count_by_timeframe(self, timeframe: str) -> int:
        """
        دریافت تعداد کاربران بر اساس بازه زمانی

        Args:
            timeframe: بازه زمانی

        Returns:
            تعداد کاربران
        """
        users = self.get_users_by_timeframe(timeframe)
        return len(users)
