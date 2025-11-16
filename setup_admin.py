"""
اسکریپت تنظیم اولیه ادمین برای ربات تلگرام
"""
from database import Database

def setup_admin():
    """تنظیم اولین ادمین"""
    db = Database()

    print("=" * 50)
    print("تنظیم ادمین اولیه ربات ارزَلان")
    print("=" * 50)
    print()

    # دریافت User ID از کاربر
    print("برای دریافت User ID خود:")
    print("1. به ربات @userinfobot در تلگرام پیام دهید")
    print("2. User ID خود را کپی کنید")
    print()

    try:
        user_id = input("User ID خود را وارد کنید: ").strip()

        # تبدیل به عدد
        user_id = int(user_id)

        # افزودن به عنوان ادمین
        if db.add_admin(user_id):
            print()
            print("✅ ادمین با موفقیت اضافه شد!")
            print(f"User ID: {user_id}")
            print()
            print("حالا می‌توانید با دستور /admin به پنل مدیریت دسترسی داشته باشید.")
        else:
            print()
            print("❌ خطا در افزودن ادمین!")

    except ValueError:
        print()
        print("❌ خطا: User ID باید یک عدد باشد!")
    except Exception as e:
        print()
        print(f"❌ خطا: {e}")

def list_admins():
    """نمایش لیست ادمین‌ها"""
    db = Database()
    admins = db.get_admins()

    print()
    print("=" * 50)
    print("لیست ادمین‌های فعلی")
    print("=" * 50)

    if admins:
        for i, admin_id in enumerate(admins, 1):
            print(f"{i}. User ID: {admin_id}")
    else:
        print("هیچ ادمینی ثبت نشده است.")
    print()

def remove_admin():
    """حذف ادمین"""
    db = Database()

    print("=" * 50)
    print("حذف ادمین")
    print("=" * 50)
    print()

    # نمایش لیست ادمین‌های فعلی
    admins = db.get_admins()
    if not admins:
        print("هیچ ادمینی برای حذف وجود ندارد.")
        return

    print("ادمین‌های فعلی:")
    for i, admin_id in enumerate(admins, 1):
        print(f"{i}. User ID: {admin_id}")
    print()

    try:
        user_id = input("User ID ادمینی که می‌خواهید حذف کنید را وارد کنید: ").strip()
        user_id = int(user_id)

        if db.remove_admin(user_id):
            print()
            print("✅ ادمین با موفقیت حذف شد!")
        else:
            print()
            print("❌ خطا در حذف ادمین!")

    except ValueError:
        print()
        print("❌ خطا: User ID باید یک عدد باشد!")
    except Exception as e:
        print()
        print(f"❌ خطا: {e}")

def main():
    """منوی اصلی"""
    while True:
        print()
        print("=" * 50)
        print("مدیریت ادمین‌های ربات ارزَلان")
        print("=" * 50)
        print()
        print("1. افزودن ادمین جدید")
        print("2. نمایش لیست ادمین‌ها")
        print("3. حذف ادمین")
        print("4. خروج")
        print()

        choice = input("انتخاب شما: ").strip()

        if choice == '1':
            setup_admin()
        elif choice == '2':
            list_admins()
        elif choice == '3':
            remove_admin()
        elif choice == '4':
            print()
            print("خروج...")
            break
        else:
            print()
            print("❌ انتخاب نامعتبر!")

if __name__ == '__main__':
    main()
