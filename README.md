# تقویم فارسی برای Apple Calendar

این پروژه دو فید `.ics` برای Apple Calendar تولید می‌کند:

- `calendar.ics` — فقط تاریخ شمسی. ظاهر تمیزتر.
- `calendar-full.ics` — تاریخ شمسی + نام روز فارسی. نزدیک به نمونه‌ای که در اینستاگرام دیدی.

بازه فعلی: **۱۴۰۵ تا ۱۴۱۰**

## لینک‌های Subscription

**نسخه تمیز**
```text
https://raw.githubusercontent.com/nemoresideo/persian-apple-calendar/main/calendar.ics
```

**نسخه کامل**
```text
https://raw.githubusercontent.com/nemoresideo/persian-apple-calendar/main/calendar-full.ics
```

> Repository باید Public باشد تا Apple Calendar بتواند فایل Raw را بدون Login بخواند.

## نصب روی iPhone

مسیر در iOS:

`Settings → Apps → Calendar → Calendar Accounts → Add Account → Other → Add Subscribed Calendar`

سپس یکی از لینک‌های Raw بالا را در قسمت **Server** وارد کن.

پیشنهاد تنظیمات:
- **Use SSL:** On
- **Remove Alerts:** On
- **User Name / Password:** خالی
- سپس **Save**

بعد داخل Apple Calendar از بخش **Calendars** می‌توانی رنگ و نمایش Subscription را تنظیم کنی.

## تغییر بازه سال‌ها

فایل `config.json` را ویرایش کن:

```json
{
  "start_jalali_year": 1405,
  "end_jalali_year": 1410,
  "owner_tag": "nemoresideo.github.io",
  "calendar_name": "تقویم فارسی"
}
```

بعد در GitHub از تب **Actions**، Workflow با نام `Update Persian Apple Calendar` را با **Run workflow** اجرا کن.

## تولید دستی

Python 3.10 یا جدیدتر کافی است و هیچ کتابخانه خارجی لازم نیست:

```bash
python generate_calendar.py
```

## نکته درباره Apple Calendar

Apple Calendar همچنان از تقویم Gregorian برای ساختار اصلی استفاده می‌کند. این پروژه تاریخ شمسی را به شکل **All-Day Event** وارد می‌کند. به همین دلیل تاریخ فارسی در نمای ماهانه و Calendar Widget دیده می‌شود.

فایل `calendar-full.ics` برای هر روز دو Event می‌سازد:
- `۱۱ مهر`
- `شنبه`

فایل `calendar.ics` فقط Event اول را می‌سازد و خلوت‌تر است.
