# Cable Label Studio · P-touch

**Amir Rahimi** · Free / رایگان / مجاني · [MIT](LICENSE.txt)

نرم افزار پیشرفته طراحی و چاپ لیبل برای ویندوز، با رابط فارسی، انگلیسی و عربی؛ اتصال USB/Wi-Fi، Excel چندشیتی و مسیر زنده، طراحی لیبل کابل، قواعد شرطی، مدیریت کاربران و گزارش چاپ.

Advanced local Windows label designer and printing software for Brother printers: USB/Wi-Fi, multi-sheet/live-path Excel, Access, cable layouts, rules, users, reports and GitHub updates. فارسی / English / العربية

برنامج متقدم لتصميم الملصقات وطباعتها محلياً في Windows، بثلاث لغات، مع Excel متعدد الأوراق واتصال مباشر بالملف وتقارير وتحديثات GitHub.

The HTTPS updater fix from **1.1.1** remains included. Users of the affected 1.1.0 package should manually install the current installer once; user data is preserved and TLS verification remains enabled.

اصلاح HTTPS نسخهٔ **۱٫۱٫۱** در نسخهٔ فعلی هم وجود دارد؛ کاربران نسخهٔ معیوب ۱٫۱٫۰ یک بار نصب‌کنندهٔ فعلی را دستی اجرا کنند.

Patch **1.2.1** separates final-strip cutting from per-label automatic full cutting for USB/Wi-Fi, removes redundant per-label Windows RAW page wrappers and adds cut diagnostics. Physical cutter behavior still requires device validation.

Version **1.2.0** adds persistent per-file cut policies, editable cuts in Print, Persian digits, measured centering and a stay-in-designer print mode with live status notifications.

نسخهٔ **۱٫۲٫۰**: برش اختصاصی هر فایل، اعداد فارسی، وسط‌چین محتوا و ماندن در طراح همراه پیام نتیجهٔ چاپ.

## Download / دانلود / التنزيل

- [Windows x64 installer](https://github.com/aa70027/P-touch/releases/download/v1.3.0/CableLabelStudio-1.3.0-Setup.exe)
- [Portable ZIP](https://github.com/aa70027/P-touch/releases/download/v1.3.0/CableLabelStudio-1.3.0-Portable.zip)
- [Editable source](https://github.com/aa70027/P-touch/releases/download/v1.3.0/CableLabelStudio-1.3.0-Source.zip)
- [SHA-256 checksums](https://github.com/aa70027/P-touch/releases/download/v1.3.0/SHA256SUMS.txt)

Install the package, choose فارسی / English / العربية on the first screen and launch Cable Label Studio. The browser opens a loopback-only local app. No login is required initially; authentication can be enabled in Settings.

## Guides / راهنما / الأدلة

- [فارسی](README.fa.md)
- [English](README.en.md)
- [العربية](README.ar.md)
- [Release checklist and hardware limitations](NEXT_UPDATE.md)
- [Requirements and validation](ACCEPTANCE.md)

PT-E550W/P750W/P710BT use model-specific Raster profiles. P700, P900W, P950NW and listed QL models use the official Brother Windows driver; cutter/media settings remain in that driver. The generic driver profile requires manual model/media verification. Physical-printer acceptance remains pending; simulations and spool submission are not physical completion.

![Persian label designer](verification/designer-fa-v110.jpg)

## Development

Windows x64, Python 3.12. Create a virtual environment, install requirements-dev.txt and run `python run.py`. Run `python -m pytest tests -q` and `node --test tests/printing_ui.test.cjs`. Build offline packages with `python build.py`; package the allowlisted source with `python package_source.py`. No remote hosting service or cloud account is required for normal printing.

User data: `%LOCALAPPDATA%\CableLabelStudio`. Installer maintenance preserves it. Linked Excel files remain external and require a separate backup. The executable is unsigned. Brother driver/software licenses are separate from this project's MIT license.

Version **1.3.0** adds original XLSX/XLSM status editing, reviewed CSV exchange with conflict detection, experimental static-image LBX packages and handoff to official Brother transfer tools. Automatic retrieval of edited device database cells is unsupported; proprietary printer backups are not CSV imports.
