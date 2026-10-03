راه‌اندازی ربات Free Fire Store روی Render

1) این فایل‌ها را در یک GitHub repository قرار بده:
   bot.py
   requirements.txt
   .python-version
   render.yaml

2) در Render:
   New -> Web Service -> repository را انتخاب کن.
   اگر render.yaml را استفاده کنی، تنظیمات سرویس از همان فایل خوانده می‌شود.

3) در Environment Variables مقدار زیر را بساز:
   BOT_TOKEN = توکن ربات از BotFather

4) اگر دستی تنظیم می‌کنی:
   Build Command:
   pip install -r requirements.txt

   Start Command:
   python bot.py

نکته:
- توکن داخل کد ذخیره نشده و باید در Environment Variables باشد.
- این پروژه از python-telegram-bot 13.15 استفاده می‌کند چون کد فعلی با Updater/Filters نوشته شده است.
- Render Free برای 24/7 بودن دائمی تضمین نمی‌دهد و فایل database.json روی فضای دائمی ذخیره نمی‌شود.
