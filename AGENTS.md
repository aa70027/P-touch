# Project instructions

Read NEXT_UPDATE.md and all three README guides before planning a release. The six original next-update requirements are implemented in 1.1.0; preserve them and the creator, project link and free MIT attribution in future releases.

Keep Persian, English and Arabic guides synchronized locally and on GitHub. Read the pending physical-acceptance checklist before claiming model support is hardware-tested. Native Raster support is limited to documented models. Windows-driver transport leaves private media/cutter properties to that driver; do not promise direct RAW Wi-Fi or app-controlled cutter behavior for those profiles.

Never publish runtime databases, external linked Excel paths, raw logs, credentials or machine-specific test directories. Source packaging is allowlisted. Keep software tests, loopback/mock tests, Windows integration and real physical printing clearly separated.

For 1.1.1 and future packages, preserve required_runtime_files() in build.py and exercise a real HTTPS request from the frozen executable. Source-only HTTPS tests do not validate the standalone TLS runtime. Do not remove certificate policy or weaken TLS verification to fix packaging failures.

For 1.2.0 and later, preserve per-document cut_settings=None inheritance and snapshot the displayed effective cut policies into each queued job. Keep digit conversion at rendering time without changing source rows, rules or encoded payloads. Run both Python and Node print-dialog tests. Preserve inline record confirmation and distinguish submission from physical completion.

For 1.2.1 and later, do not wrap individual native Raster labels in Windows StartPagePrinter/EndPagePrinter calls. The Raster stream owns its FF/Control-Z boundaries; one continuous or confirmed-record segment uses one RAW document. Keep five-copy USB/TCP stream regression and short-write abort coverage. A software trace cannot prove physical cutter behavior or identify the user's fault without device evidence.

Keep final-strip no-chain feed/cut separate from per-label auto-full-cut; ESC i A cut-each-one belongs only to explicit intermediate full cuts. Verify both USB and TCP five-copy streams and preserve no-cut and intermediate full-cut behavior.

For 1.3.0 and later, preserve original-workbook edit guards and CSV three-way conflict checks. Native LBX output is experimental static images, not a dynamic database template. Never report a prepared package or opened Brother tool as transferred, and never report file-mediated CSV import as automatic printer database readback. Keep all three Node behavior suites and frozen status/native package smoke tests.

For 1.3.1 and later, keep editor-only icon commands in the top toolbar, localized accessible titles, per-account collapsed panels and pane scroll restoration on rerenders. Run all four Node suites. Direct memory transfer without Brother tools is still incomplete; do not equate native image preparation with a field-bound template/database compiler or verified transfer.
