# راه حل مشکل Python 3.14

اگر با خطای زیر مواجه شدید:
```
AttributeError: 'Updater' object has no attribute '_Updater__polling_cleanup_cb'
```

این مشکل به دلیل عدم سازگاری کامل `python-telegram-bot` با Python 3.14 است.

## راه حل‌های پیشنهادی:

### راه حل 1: استفاده از Python 3.13 (توصیه می‌شود)

Python 3.14 هنوز نسخه آزمایشی است و با بسیاری از کتابخانه‌ها سازگار نیست.

1. Python 3.13 را نصب کنید
2. محیط مجازی جدید با Python 3.13 بسازید:
```bash
py -3.13 -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### راه حل 2: نصب نسخه Development

```bash
pip uninstall python-telegram-bot
pip install -r requirements-py314.txt
```

### راه حل 3: نصب مستقیم از GitHub

```bash
pip uninstall python-telegram-bot
pip install git+https://github.com/python-telegram-bot/python-telegram-bot.git@master#egg=python-telegram-bot[job-queue]
```

### راه حل 4: Downgrade کردن Python-Telegram-Bot

```bash
pip install python-telegram-bot[job-queue]==20.8
```

## بررسی نسخه Python

برای بررسی نسخه Python:
```bash
python --version
```

یا:
```bash
py --version
```

## توصیه نهایی

استفاده از **Python 3.11** یا **Python 3.13** برای این پروژه توصیه می‌شود، چون کاملاً تست شده و پایدار هستند.
