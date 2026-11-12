# Release 1.1.0 checklist / چک‌لیست نسخهٔ ۱٫۱٫۰ / قائمة الإصدار ١٫١٫٠

Recorded and implemented: 2026-11-13 · Asia/Tehran

**فارسی:** شش درخواست آپدیت قبلی و درخواست‌های جدید در کد و رابط نسخهٔ ۱٫۱٫۰ پیاده‌سازی شده‌اند. تیک‌ها وضعیت پیاده‌سازی نرم‌افزار را نشان می‌دهند؛ آزمون فیزیکی چاپگر، صحت ابعاد، برش و اتصال با دستگاه واقعی همچنان باید جدا انجام شود. محدودیت‌های مسیر درایور ویندوز در سه راهنما ثبت شده‌اند.

**English:** Checkmarks represent implemented software paths, not physical printer certification. Tests distinguish mock discovery, software simulation, Windows integration and real device acceptance. Model-specific driver limitations are explicit in all guides.

**العربية:** العلامات تخص تنفيذ مسارات البرنامج، ولا تعني اعتماد طابعة فعلية. اختبارات الأجهزة والقطع والأبعاد تبقى منفصلة، وحدود مسار برنامج تشغيل Windows موثقة.

## Accepted update requirements

- [x] **NU-01:** First wizard question in three languages, with simultaneous فارسی / English / العربية buttons. Mode/path questions appear only after selection. Built native wizard; native desktop visual/input verification remains unavailable on this host.
- [x] **NU-02:** Multi-sheet XLSX/XLS import, one/many sheet selection, unioned columns, `_sheet` identity, combined row limit. Two-sheet file exercised through API and web UI.
- [x] **NU-03:** Native Windows file picker, private linked source path, change path, fresh pre-preview/pre-job reads, missing/locked-file errors, saved dataset binding. Integration test modifies the original workbook and verifies fresh preview/job snapshot without uploading. Interactive native picker needs final desktop acceptance.
- [x] **NU-04:** Official GitHub Releases check, stable/preview selection, verified download, persistent progress/events/error/log page, backup and native update/restart helper. Integrity failures block execution. Windows update handoff tested separately from network download.
- [x] **NU-05:** Brother USB PnP model/hardware IDs independent of driver, installed queues/drivers, SNMP network identity, unknown states, installer detection option. USB/network identity tests use controlled fixtures; no physical model certification is implied.
- [x] **NU-06:** Model catalog, capability-based widths/resolutions/cuts, native Raster family plus official Windows-driver transport, generic driver option, official Brother download pages/direct-file downloads with progress/errors. Hardware/driver-dependent controls are disclosed rather than assumed.

## Additional requested changes

- [x] Creator **Amir Rahimi**, project link and free MIT license in installer, sidebar below version, footer on every app view and login screen.
- [x] Persian repository description including **نرم افزار پیشرفته طراحی و چاپ لیبل**; bilingual project README.
- [x] Local subnet MAC-to-IP discovery with progress, exact MAC matching and automatic resolution before printing; stale/mismatched addresses block printing.
- [x] Stable DNS hostname option and DHCP reservation guidance for changing IP addresses.
- [x] Separate Wireless Direct and router Infrastructure configuration guidance, Windows Wi-Fi settings action and official model documentation links.
- [x] Persian, English and Arabic guides updated and included in source/Windows packages; GitHub source/release publication tracked with release artifacts.

## Acceptance still required on real hardware

- [ ] Actual PT-E550W USB and Wi-Fi output, direct/router modes, changing DHCP lease, matching cassette, dimensions and cutter/quality combinations.
- [ ] Each additional physical model and official driver, media dimensions/cutter settings and supported special media.
- [ ] Real Access database import with the matching 64-bit ODBC driver.
- [ ] Native desktop appearance/input and file selection on the user's interactive Windows desktop; browser UI tests do not replace this.

See [فارسی](README.fa.md), [English](README.en.md), [العربية](README.ar.md) and [validation details](ACCEPTANCE.md).

Repository: https://github.com/aa70027/P-touch
