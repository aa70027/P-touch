**1.1.1 · Amir Rahimi · Free / رایگان / مجاني · MIT**

### فارسی

خطای `[Errno 2] No such file or directory` هنگام بررسی آپدیت از بستهٔ اجرایی ۱٫۱٫۰ رفع شد. علت، جاافتادن فایل سیاست گواهی موردنیاز HTTPS در بستهٔ نصبی بود. بررسی گواهی و نام میزبان همچنان فعال است. گزارش خطا شامل نوع، مرحله و جزئیات فنی در همان صفحه ذخیره می‌شود.

**اگر ۱٫۱٫۰ همین خطا را می‌دهد، این بار نصب‌کنندهٔ ۱٫۱٫۱ را دستی دانلود و در حالت ارتقا اجرا کنید.** اطلاعات کاربران حفظ می‌شود؛ سپس آپدیت‌های بعدی را از داخل برنامه بررسی کنید.

### English

Fix the frozen 1.1.0 updater failing before contacting GitHub because a required HTTPS certificate-policy file was omitted. Preserve the runtime's certificate policy and keep certificate/hostname verification enabled. Persist exception type, stage and technical diagnostics on the update page. Release verification now performs a real GitHub HTTPS check from the standalone executable.

Affected 1.1.0 users must download this installer manually once and choose Upgrade. User data is preserved. Subsequent updates can be checked through the repaired application.

### العربية

إصلاح خطأ فحص التحديث في حزمة ١٫١٫٠ بسبب غياب ملف سياسة شهادات HTTPS المطلوب. يبقى التحقق من الشهادة واسم المضيف مفعّلاً. تعرض صفحة التحديث نوع الخطأ ومرحلة العملية والتفاصيل التقنية المحفوظة.

إذا ظهر الخطأ في ١٫١٫٠، نزّل مثبّت ١٫١٫١ يدوياً مرة واحدة واختر الترقية؛ تُحفظ بيانات المستخدم، ثم يمكن فحص التحديثات اللاحقة من داخل التطبيق.

96 software tests and the local Windows package/maintenance checks passed. The release build additionally checks GitHub HTTPS from its own frozen executable. Physical-printer acceptance remains separate. Executables are unsigned.

[فارسی](https://github.com/aa70027/P-touch/blob/main/README.fa.md) · [English](https://github.com/aa70027/P-touch/blob/main/README.en.md) · [العربية](https://github.com/aa70027/P-touch/blob/main/README.ar.md)
