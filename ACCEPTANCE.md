# Requirements and verification — Cable Label Studio 1.0.0

Prepared 2026-11-13 (Asia/Tehran). **Software implementation and hardware acceptance are separate.** The build machine has only Microsoft Print to PDF, no installed Brother PT-E550W driver, no attached PT-E550W and no Microsoft Access ODBC driver. Those missing devices/drivers are reported by the application, not replaced by a success indicator.

## Requirements coverage

The user's repeated numbering is retained where useful. “Implemented” means an executable code path and UI exist; it is not a statement that the physical printer was tested.

| Request | Implementation | Verification/limit |
|---|---|---|
| 1. USB/Wi-Fi selection | Settings; Windows RAW and TCP transports | Local TCP receiver tested; physical device pending |
| 2. Configurable IP | Validated target IP and TCP port | Target only; does not change printer's own IP |
| 3. Online/offline | USB device enumeration, queue error flags, TCP reachability | Mechanical readiness remains unconfirmed |
| 3. Driver status | Brother queue/driver detection and official download link | Missing on build host; never reports installed falsely |
| 4. Tape width | TZe widths 3.5/6/9/12/18/24 mm | Printable pin geometry enforced; cassette must match |
| 5 and 15. Manual/automatic length | Per-page millimetres or content measurement | Minimum mechanical margins included; isolated short-label feed limit disclosed |
| 6. Full/half/no cut | Page/copy, record, file and final job policies | Final > file > record > page priority; physical combinations pending |
| 7. Standard/high quality | 180×180 / 180×360 raster | Header, feed scaling and pixel geometry tested; device output pending |
| 8. Page/file repetitions | Per-page repeat, dialog copies, complete file copies | Ordered print-plan tests |
| 9. Mirror | Final raster mirror | Pixel-level test; no second mirror command |
| 10. Flag | Repeated design on both sides | Single-data-field repetition tested |
| 11. Save files/templates | SQLite resource library and multi-page documents | Persistence and access checks; `.label.json` interchange |
| 12. Excel/Access | XLSX/XLSM/XLS/CSV/TSV/MDB/ACCDB; sheet/table selection | Excel/CSV tested; Access needs 64-bit driver and real-file acceptance |
| 13. Cable repetition/separator | Flag sides, cable gap, separator text/line; wrap count | Renderer and preview; physical fit pending |
| 14. Formulas/process | Ordered rules, conditions, output field bindings and expression functions | Sandbox, lazy IF and dependent rule tests |
| 16. Before/after blank space | Separate optional margins including zero | 2 mm mechanical minimum remains; displayed in preview |
| 17. Font/style/Persian | Font, pt size, bold, underline, direction, rotation, Arabic/Persian shaping | Mixed-text raster tests and UI preview; physical output pending |
| 18. Images | Image elements with reusable asset IDs | Upload validation and rendering path |
| 19. Uploaded image library | Durable image resources | Ownership and visibility enforced |
| 20. Add fonts | TTF/OTF upload and selection | Font parsing and reusable resource; glyph coverage depends on font |
| 21. Three UI languages | Persian/English/Arabic, RTL/LTR | Browser navigation and locale review |
| 22. Three README guides | README.fa.md / README.en.md / README.ar.md | Bundled with source, executable and installer |
| 23–24. Installer/wizard | Offline x64 WinForms wizard, language switch, custom path | Built and exercised; see verification files |
| 25. Browser port | Persisted port 1024–65535 and restart action | Settings validation and instance controls |
| 26. Setup logs | Live wizard output and saved UTF-8 setup log | File extraction, SHA verification and operation progress |
| 27. Automatic execution | Per-user Windows sign-in startup toggle | HKCU Run integration; off by default |
| 28. App logs | Persistent audit, rotating technical logs, Settings view | Admin-only log access |
| 29. Optional login | Initially no login, optional administrator activation | Password precondition, sessions, CSRF/origin protection |
| 30. User count | No contractual user-count cap | Capacity limited by hardware/resources |
| 31. Per-user sharing | Category defaults; resource private/shared/inherit override | Private/shared tests; shared originals owner-editable only |
| 32. Continuous/key-confirmed | Serial queue, Enter/Space or Next record gate | Automated gate/cancel test and browser 3-record simulation |
| 33. Label formats | General, cable flag/wrap, patch panel, faceplate, die-cut flag layout, terminal block | Die-cut is layout on continuous tape, not shaped cutting; optional heat-shrink is simulation only |
| 34. Usage reports | Per user/date, requested/submitted/confirmed/simulated/failure/cancel/interruption | Simulation never counted as submission; true device-confirmed count stays separate |
| 35. Install/repair/uninstall/update | Installer modes; Start menu maintenance; rollback on copy failure | User data preserved; manual update by newer installer |
| 36. Custom install path | Dedicated empty or recognized product folder | Refuses unrelated nonempty destination; safe extraction paths |

## Verification artifacts

- `tests/test_core.py`: formulas, bilingual text, dimensions, seed layouts, raster protocol, data import, auth/access, CSRF/origin, full preflight, queue gates/cancel, simulation counters, uploads/backup and loopback transport.
- `tests/verify_installer.py`: isolated install, executable health, file repair, update, uninstall, SHA manifest checks and unrelated-file preservation. No physical print is issued.
- `verification/`: public test summaries and a screenshot. Raw logs and machine-specific test directories remain local and are not published.
- `release/SHA256SUMS.txt`: release installer and portable-package checksums.

The native setup window exposed its Persian text, operation selector, path selector and wizard actions through accessibility inspection. Native desktop screenshot/input capture was unavailable on this host (`CreateForMonitor` / `GetCursorPos` access errors); its graphical appearance was not screenshot-verified. The installer engine itself was exercised through all four modes. Browser screenshots and interactions were available for the web interface, including desktop and narrow-window layouts.

## Physical acceptance still required

Connect the user's PT-E550W; install its official driver for USB and configure its Wi-Fi IP. Use a matching TZe cassette. Print a known 60 mm test label in standard/high quality, verify orientation and measured length, then test full/half/no cut in single-page and multi-record batches. Check Persian/Arabic joining with the selected font, flag/wrap alignment, and the next-record keyboard gate. Compare paper output to the PNG simulation. Validate Access with a real database after installing its 64-bit driver.

The package is not represented as physically certified. Windows spool success and TCP send success are submission acknowledgements. This E550W transport does not provide a reliable per-label completion counter; `confirmed` remains zero without such evidence. Cancelling cannot recall data already submitted to the OS/printer. No automatic resend is performed after failure or process interruption.

The supplied executable is unsigned; no code-signing identity was available. Native P-touch `.lbx` import/export, remote-LAN hosting, and printer firmware/network reconfiguration were not requested as supported deliverables and are not implemented.
