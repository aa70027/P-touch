**1.2.1 · Amir Rahimi · Free / رایگان / مجاني · MIT**

### فارسی

در موتور مشترک USB/وای‌فای، برش نهایی از برش خودکار هر لیبل جدا شد؛ پایان زنجیره دیگر فرمان برش کاملِ تک‌تک لیبل‌ها را فعال نمی‌کند.

ارسال USB پیوسته دیگر برای هر لیبل صفحهٔ Windows جدا باز و بسته نمی‌کند؛ همهٔ نسخه‌های هر بخش در یک سند RAW می‌مانند. لاگ فنی، برش و مرزهای واقعی هر صفحهٔ ارسال‌شده را بدون متن لیبل ثبت می‌کند. آزمون پنج نسخه، چهار فرمان نیم‌برش و فقط یک برش کامل در پایان را بررسی می‌کند. علت قطعی و رفع فیزیکی برش اضافهٔ گزارش‌شده هنوز نیازمند تأیید دستگاه است.

### English

Separate final-strip feed/cut from full-cut-each-label in the shared USB/Wi-Fi encoder. Emit cut-each-one only for explicit intermediate full cuts.

Remove per-label Windows page wrappers from continuous USB RAW transmission. Preserve one document per continuous or confirmed-record segment, and add per-page cut diagnostics without label text. Five-copy stream regression verifies four half-cut policies and only one final full cut. The exact physical cause and resolution of reported extra cuts remain unverified on hardware. Windows-driver media/cutter properties remain controlled by the official driver.

### العربية

فصل القطع الكامل الأخير عن القطع التلقائي لكل ملصق في مرمّز USB/Wi-Fi المشترك.

إزالة حدود صفحات Windows الإضافية لكل ملصق من إرسال USB RAW المتواصل، مع الاحتفاظ بمستند واحد لكل مقطع وإضافة تشخيص القطع دون نص الملصق. يتحقق اختبار خمس نسخ من أربع سياسات نصف قطع وقطع كامل أخير. يبقى سبب القطع الزائد الفعلي وحله بحاجة إلى تأكيد الجهاز.

All 1.2.0 features and the HTTPS updater fix are preserved. User data is preserved during upgrade. Reload the browser page once after upgrading.

[فارسی](https://github.com/aa70027/P-touch/blob/main/README.fa.md) · [English](https://github.com/aa70027/P-touch/blob/main/README.en.md) · [العربية](https://github.com/aa70027/P-touch/blob/main/README.ar.md)

Protocol references: [Brother Raster v1.02, cutter controls](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf), [Microsoft RAW page boundaries](https://learn.microsoft.com/en-us/windows/win32/printdocs/startdocprinter).

Validation: 129 Python tests, 12 Node UI-logic tests, 11 frozen-application checks and 17 installer checks passed locally. Native maintenance integration remains separately validated (4 handoff and 3 registration/shortcut checks). Physical cutter output remains unverified.
