# Persian Apple Calendar · تقویم فارسی اپل

تقویم شمسی برای **Apple Calendar** روی iPhone، iPad و Mac؛ با لینک ثابت GitHub و به‌روزرسانی خودکار.

## فیدها

| فید | نمایش | کاربرد |
|---|---|---|
| **calendar-pro.ics** | یک رویداد تمیز مثل «۱۲ مهر» + جزئیات کامل | **پیشنهادی** |
| **calendar.ics** | فقط تاریخ شمسی | مینیمال |
| **calendar-full.ics** | تاریخ شمسی + نام روز به‌صورت دو رویداد | مشابه نمونه اینستاگرام |

### لینک پیشنهادی

```text
https://raw.githubusercontent.com/nemoresideo/persian-apple-calendar/main/calendar-pro.ics
```

### نسخه کامل

```text
https://raw.githubusercontent.com/nemoresideo/persian-apple-calendar/main/calendar-full.ics
```

## نصب روی iPhone / iPad

مسیر:

`Settings → Apps → Calendar → Calendar Accounts → Add Account → Other → Add Subscribed Calendar`

در **Server** یکی از لینک‌های Raw بالا را وارد کن.

تنظیم پیشنهادی:

- **Use SSL:** On
- **Remove Alerts:** On
- **User Name:** خالی
- **Password:** خالی

سپس **Save** را بزن.

## طراحی فید حرفه‌ای

نسخه `calendar-pro.ics` برای هر روز فقط یک All-Day Event می‌سازد:

**Title**
```text
۱۲ مهر
```

**Details**
```text
یکشنبه، ۱۲ مهر ۱۴۰۵
تاریخ میلادی: 2026-10-04
تقویم خورشیدی ایران
```

به این ترتیب نمای ماهانه Apple Calendar شلوغ نمی‌شود، ولی جزئیات کامل با لمس تاریخ در دسترس است.

## کیفیت و پایداری

- UID پایدار برای جلوگیری از Duplicate شدن Eventها
- UTF-8 و اعداد فارسی
- CRLF و line folding سازگار با RFC 5545
- Eventهای Transparent تا Busy Time ایجاد نکنند
- بدون Alert
- Refresh hint هر ۱۲ ساعت
- رنگ پیشنهادی Apple Calendar
- GitHub Actions برای Test، Generate، Validate و Commit
- بدون dependency خارجی Python
- تست تاریخ‌های مرجع برای جلوگیری از خطای تبدیل

## بازه فعلی

**۱۴۰۵ تا ۱۴۱۰**

برای تغییر بازه، `config.json` را ویرایش کن. Workflow به‌صورت خودکار فایل‌های تقویم را بازسازی می‌کند.

## اجرای دستی

```bash
python -m unittest discover -s tests -v
python generate_calendar.py
```

## Repository

https://github.com/nemoresideo/persian-apple-calendar
