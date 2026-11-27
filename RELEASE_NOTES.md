**1.2.0 · Amir Rahimi · Free / رایگان / مجاني · MIT**

### فارسی

- تنظیمات برش عمومی هنگام بازکردن چاپ خوانده می‌شوند؛ تغییرات برای هر فایل جدا ذخیره و در دفعات بعد فراخوانی می‌شوند.
- چهار تنظیم برش برای هر فایل در پنجرهٔ چاپ قابل ویرایش‌اند؛ دکمهٔ بازگشت به تنظیمات عمومی نیز وجود دارد.
- تیک اعداد فارسی برای پیش‌نمایش و چاپ متن، بدون تغییر دادهٔ اصلی، QR یا بارکد.
- دکمه‌های وسط عرض نوار و وسط صفحه/خانه با اندازه‌گیری واقعی؛ دکمهٔ رفع جابه‌جایی در پیام خطای محدودهٔ چاپ.
- انتخاب دوحالتهٔ رفتن به صف یا ماندن در صفحه؛ پیام کوتاه نتیجه و امکان تأیید رکورد بعد در همان طراح.

### English

Persistent per-file cut overrides and inheritance, editable per-file policies in Print, page-level Persian digits after formula/data binding, measured element/group centering and a stay-in-designer option with short outcome notifications and inline record confirmation. Unsaved/shared designs with changed cuts become private copies; existing owned-file cut updates preserve other layout edits.

### العربية

إعدادات قطع محفوظة لكل ملف مع وراثة الإعدادات العامة وتحريرها من نافذة الطباعة، وأرقام فارسية للنص، وتوسيط فعلي مع زر داخل رسالة الخطأ، وخيار البقاء في المصمم مع إشعارات النتيجة وتأكيد السجل التالي.

User data is preserved during upgrade. Physical-printer/cutter acceptance remains separate. For Windows-driver profiles, the driver's private properties still control actual media/cutting. Submission notifications do not certify physical completion. Centering on an automatically sized page fixes its current length; width-only centering preserves automatic length. Oversized content produces an actionable error rather than silent resizing.

The HTTPS runtime fix remains included. Affected 1.1.0 users can upgrade manually directly to this version; 1.1.1 users can use the in-app updater.

[فارسی](https://github.com/aa70027/P-touch/blob/main/README.fa.md) · [English](https://github.com/aa70027/P-touch/blob/main/README.en.md) · [العربية](https://github.com/aa70027/P-touch/blob/main/README.ar.md)

After an in-app upgrade, reload the browser page once (F5) to load the new interface. Inline record confirmation supports Ctrl+Enter.

Validation: 119 Python tests, 12 Node UI-logic tests, 10 frozen-application checks, 17 installer checks, 4 update-handoff checks and 3 Windows integration checks passed locally. Browser visual inspection and physical printing were not validated.
