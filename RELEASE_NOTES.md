**1.3.1 · Amir Rahimi · Free / رایگان / مجاني · MIT**

## نسخهٔ ۱٫۳٫۱ — فضای طراحی ثابت و ابزارهای بالای صفحه

ثبت نتیجهٔ آپدیت نیز در برابر قفل کوتاه‌مدت فایل در Windows اصلاح شد: جایگزینی اتمی با تلاش مجدد محدود انجام می‌شود و نصب موفق به‌خاطر خواندن هم‌زمان فایل، بی‌دلیل خطا گزارش نمی‌شود. خطای ماندگار همچنان نمایش داده می‌شود.

در نمایش دسکتاپ، ستون تنظیمات اسکرول مستقل دارد؛ پیش‌نمایش و منابع داده در ستون مرکزی می‌مانند و با اسکرول تنظیمات ناپدید نمی‌شوند. ستون مرکزی برای داده‌های زیاد اسکرول جداگانه دارد. پس از تغییر عرض، نوع لیبل یا سایر تنظیمات، محل اسکرول هر دو ستون حفظ می‌شود. در نمایش موبایل، چیدمان به جریان طبیعی صفحه برمی‌گردد.

با کلیک روی عنوان «تنظیمات لیبل»، «اجزای طرح» و «جزء انتخاب‌شده»، باکس جمع یا باز می‌شود. عنوان با صفحه‌کلید هم قابل استفاده است. وضعیت باکس‌ها برای هر حساب در همین مرورگر نگهداری می‌شود و با تغییر تنظیمات باقی می‌ماند.

پنج فرمان چاپ لیبل، چاپ مستقل با دستگاه، ذخیره قالب، ذخیره فایل و جدید، به صورت آیکون در نوار بالایی کنار انتخاب زبان قرار دارند. مکث موس روی آیکون، توضیح همان زبان را نشان می‌دهد و نام قابل‌دسترسی برای صفحه‌خوان وجود دارد. عنوان بزرگ «طراحی لیبل» و توضیح زیر آن حذف شده و طراحی بالاتر آمده است. نوار بالا هنگام اسکرول در دسترس می‌ماند.

**مورد تکمیل‌نشده: ارسال مستقیم قالب و CSV بدون هیچ نرم‌افزار دیگر.** این نسخه چنین قابلیتی اضافه نمی‌کند. خروجی LBX تصویری آزمایشی و مسیر انتقال با ابزار رسمی Brother همان محدودیت نسخهٔ ۱٫۳٫۰ را دارد؛ CSV به قالب تصویری متصل نیست. مستند رسمی SDK موبایل، انتقال را برای BLF/PDZ ساخته‌شده با Transfer Manager تعریف می‌کند؛ این مستند، مبدل قالب ویندوز یا پروتکل ساخت بستهٔ فیلددار را ارائه نمی‌کند. ساخت و انتقال مستقل، به پیاده‌سازی معتبر قالب/دیتابیس و آزمون واقعی دستگاه نیاز دارد. ارسال فایل به پورت چاپ یا آماده‌کردن ZIP به معنی ذخیرهٔ قالب و دیتابیس در حافظه نیست. خواندن خودکار وضعیت دستگاه هم پشتیبانی نمی‌شود.

پس از ارتقا **Ctrl+F5** بزنید. آزمون‌های نرم‌افزاری با تأیید بصری یا سخت‌افزاری یکسان نیستند؛ بررسی بصری این انتشار به دلیل توقف ابزار کنترل مرورگر کامل نشده است.


## Version 1.3.1 — persistent designer panes and top toolbar

Update completion now retries atomic state replacement across brief Windows sharing locks. Readers retain the complete previous state until replacement succeeds; persistent failures remain explicit.

On desktop, the properties column scrolls independently while the central preview and data remain available. The center has its own scrolling for large datasets. Rerendering label settings preserves both pane scroll positions. Narrow screens use normal page flow.

Click the Label properties, Elements or Selected element header to collapse/expand that card. Native summary controls support keyboard access. Each account's panel choices persist in this browser across rerenders.

Print labels, Standalone printing, Save template, Save file and New are icon buttons beside the language selector. Hover shows the localized title; each has an accessible name. The large designer heading/description have been removed to raise the work area. The top toolbar remains visible while scrolling.

**Incomplete requirement: direct template and CSV transfer with no other software.** This release does not implement it. Experimental static-image LBX preparation and official Brother tool handoff retain the 1.3.0 limits: CSV is not dynamically bound to the image templates. The official mobile SDK documents transfer of BLF/PDZ created by Transfer Manager; it does not provide a Windows compiler or a specification for creating field-bound binary packages. Independent compilation/transfer requires a validated implementation and actual device testing. A print-port write or prepared ZIP is not storage of a template/database in printer memory. Automatic device status readback is also unsupported.

Reload with **Ctrl+F5** after upgrading. Software checks do not establish browser or hardware acceptance. Visual inspection could not be completed because browser control was stopped by the automation tool.


## الإصدار ١٫٣٫١ — أعمدة تصميم مستقلة وشريط أدوات علوي

أُصلح تسجيل نتيجة التحديث عند قفل ملف الحالة مؤقتاً في Windows، باستبدال ذري ومحاولات محدودة. تبقى الحالة السابقة كاملة وتُعرض الأخطاء المستمرة.

في سطح المكتب يتمرر عمود الخصائص مستقلاً وتبقى المعاينة ومصادر البيانات في العمود الأوسط، وله تمرير خاص للبيانات الطويلة. تبقى مواضع التمرير بعد تغيير إعدادات الملصق. تستخدم الشاشات الصغيرة تدفق الصفحة الطبيعي.

انقر عنوان خصائص الملصق أو عناصر التصميم أو العنصر المحدد لطي البطاقة وفتحها. تدعم العناوين لوحة المفاتيح، وتُحفظ اختيارات كل حساب في المتصفح وتبقى بعد تحديث العرض.

انتقلت أوامر طباعة الملصقات والطباعة المستقلة وحفظ القالب وحفظ الملف وجديد إلى أيقونات بجانب اختيار اللغة. يعرض مرور المؤشر شرحاً باللغة الحالية ولها أسماء لقارئ الشاشة. أُزيل العنوان الكبير والوصف لرفع مساحة التصميم ويبقى الشريط العلوي متاحاً أثناء التمرير.

**متطلب غير مكتمل: نقل القالب وCSV مباشرة دون أي برنامج آخر.** لا ينفذه هذا الإصدار. تبقى حدود LBX المصوّر التجريبي وفتح أدوات Brother كما في ١٫٣٫٠؛ CSV غير مرتبط بصور القوالب ديناميكياً. يوثق SDK المحمول نقل BLF/PDZ المنشأة ببرنامج Transfer Manager ولا يقدم مترجماً لـ Windows أو مواصفة لإنشاء الحزم الثنائية المرتبطة بالحقول. يلزم تنفيذ موثوق واختبار الجهاز الفعلي. إرسال ملف إلى منفذ الطباعة أو تجهيز ZIP لا يعني تخزين القالب وقاعدة البيانات في الذاكرة. لا يُدعم استرجاع حالة الجهاز آلياً.

حدّث المتصفح بـ **Ctrl+F5** بعد الترقية. اختبارات البرمجيات ليست اعتماداً بصرياً أو عتادياً؛ لم يكتمل الفحص البصري بسبب إيقاف أداة التحكم بالمتصفح.


[Brother transfer API](https://support.brother.com/g/s/es/htmldoc/mobilesdk/reference/android/printer.html#transfer) · [Brother file creation](https://support.brother.com/g/s/es/dev/en/setting/transfer_file/index.html)
