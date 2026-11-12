# Cable Label Studio — 1.1.0

An offline Windows application with a browser interface for designing and submitting Brother PT-E550W labels. The local engine stores templates, files, uploads, accounts, rules and reports on this computer.

## Installation and maintenance

Run `CableLabelStudio-1.1.0-Setup.exe`. Choose English, Persian or Arabic, select New installation and choose a dedicated installation folder. The wizard displays progress, SHA-256 verification and a saved operation log. Launch the desktop or Start menu shortcut. The default URL is `http://127.0.0.1:8765` and no login is required initially.

The package targets Windows 10/11 x64 and bundles Python. The wizard uses Windows .NET Framework 4.7.2 or later. Installation is per Windows user; choosing a protected installation folder may require appropriate Windows permissions. The application binds only to loopback, not the LAN.

Re-run Setup or use the Start menu Maintenance shortcut for repair, update or uninstall. Repair replaces application files from the installer package. Upgrade by running a newer installer. An interrupted overlay restores previous application files. User data remains separate and is preserved during repair, update and uninstall. The portable ZIP runs by extracting it into a dedicated directory and opening `CableLabelStudio.exe`.

## Printer connection

In Settings choose USB and an installed Brother PT-E550W queue, or Wi-Fi and the printer IP address/TCP port (default 9100). USB requires the official Brother Windows driver. The application refuses RAW jobs for unrelated printer models. Changing the target IP in this application does not reconfigure the printer's own network interface.

Driver installation, USB device presence, Windows queue state and TCP reachability are separate signals. A reachable TCP port does not establish tape readiness or prove physical print completion. No unsupported status-polling command is sent to the E550W.

[Official Brother downloads](https://support.brother.com/g/b/downloadtop.aspx?c=us&lang=en&prod=e550weus)

## Design and layout

Layouts include general, cable flag, cable wrap, patch panel, faceplate, die-cut flag layout and terminal block. An additional heat-shrink layout is available for simulation; physical HSe tube printing is blocked until an appropriate media profile is validated.

Select the actual installed tape width: 3.5, 6, 9, 12, 18 or 24 mm for TZe tape. A 24 mm tape has about 18 mm of printable width. Keep content inside the printable area; overflowing elements are rejected during preview and full preflight.

Length may be manual or calculated from content. The requested length includes at least 2 mm of mechanical blank margin at each end; optional before/after margins may be set to zero but cannot remove that mechanical requirement. For auto length, each record can have a different physical length. Very short isolated labels may feed out to 24.5 mm because of cutter position. Length values are in millimetres; the rendered layout range is 4.4–1000 mm. The preview separately shows a conservative isolated-label output estimate.

Choose standard 180×180 dpi or high 180×360 dpi. High mode improves one axis only. Mirror printing reverses the final raster once. Full-device tests are required to establish tape/firmware-specific dimensional accuracy and cutter behavior.

Add text, images, lines, frames, QR codes or Code 128. Text settings include font, point size, bold, underline, alignment, direction and rotation. Persian/Arabic joining and bidirectional text are processed before rasterizing. Select a font with the required glyphs. Code 128 supports ASCII; use QR for Unicode content.

Drag elements, use the numeric X/Y/W/H fields, or press arrow keys to move the selected element by 0.1 mm (Shift: 1 mm). Width zero automatically fits text. Increase the element frame or reduce font size if text overflows; the renderer does not silently clip text.

Cable flag repeats the same data on two sides from one field. Configure the cable gap, separator text and separator line. Cable wrap repeats vertically according to the repetition count. Patch-panel and terminal-block layouts use cell count and pitch; `{#cell}` resolves to the one-based cell number. Die-cut flag is a printed layout on continuous tape: this cutter cannot create a shaped die-cut outline.

In flag layouts the manual length field specifies each flag side; the preview shows the total including both sides and the cable gap. Manual patch-panel/terminal length must accommodate all cells and end margins; a longer manual length adds trailing blank space without changing cell pitch.

Documents can contain multiple pages, each with its own elements, dimensions and page repetition. Save documents or reusable templates in the application. Export/import uses the project's `.label.json` format, not Brother's native `.lbx` format. Saved datasets are independent resources selected at printing time. Template and document files store layouts, rules and sample variables.

## Images and fonts

Upload PNG/JPG/JPEG/BMP/WEBP images or TTF/OTF fonts in Images & fonts. They remain in the library across restarts and can be selected in element properties. Each upload is limited to 50 MB. Only use fonts and images for which you have appropriate rights.

## Excel, CSV and Access

Upload XLSX, XLSM, XLS, CSV, TSV, MDB or ACCDB. Choose one or more worksheets, or an Access table, text encoding and delimiter as applicable, then read the source. The first spreadsheet/CSV row supplies column names; duplicate/blank column names are made unique. Excel formulas use the saved calculated values: recalculate and save the workbook in Excel before import. Macros are not executed.

Access requires a 64-bit Microsoft Access Database Engine or Access Runtime ODBC driver. Diagnostics identifies missing drivers. The application does not silently install this prerequisite. Excel and CSV do not need Access or Microsoft Office installed.

Uploaded source files are snapshots; linked Windows paths are refreshed as described in the 1.1.0 section below. Re-upload the original file to capture external changes. Reload source re-reads the stored snapshot with the chosen sheet/table settings. Save a dataset, use it in the designer and bind text with `{Rack}`, `{Port}` or any exact column name. Manual JSON arrays and inline record editing are also available. A dataset may contain up to 100,000 nonempty records; larger input is rejected rather than truncated. The grid shows a bounded preview; the complete imported dataset remains available to printing and export.

## Rules and expressions

Rules run from top to bottom. Each rule has an output field, condition, value expression and optional otherwise expression. Subsequent rules can reference previous output fields. Example: target `B`, condition `not EMPTY(COL("X"))`, value `'A'`; bind the desired text element to `{B}`.

```text
IF(EMPTY(COL("X")), "", "A")
CONCAT(COL("Rack"), "-", PAD(COL("Port"), 2))
COL("Type") == "Fiber"
CONTAINS(LOWER(COL("Description")), "fiber")
```

Available functions: `COL`, `IF`, `EMPTY`, `CONCAT`, `PAD`, `UPPER`, `LOWER`, `TRIM`, `TEXT`, `NUMBER`, `LEN`, `REPLACE`, `CONTAINS`, `ROUND`, `AND`, `OR`, `NOT`. Arithmetic, comparisons and conditional expressions are supported. An element expression starts with `=`. Escape literal braces with `{{` and `}}`. The evaluator disallows arbitrary Python execution, attribute access, file access and loops.

## Printing and cutting

The Print dialog chooses copies of each page, copies of the complete files, all records or a record range, and optional additional saved files. The current design is first, followed by selected saved files. The per-page repetition setting multiplies the dialog's page-copy count. Each file copy traverses all selected documents and their records in order.

Continuous mode submits all records without a manual gate. Confirm-each-record mode keeps the next record local until you click Next record or press Enter/Space on the Print queue page. The gate follows submission of the previous record, not a hardware-confirmed completion signal. USB gated records are separate spool jobs.

Settings provides full, half or no cut between pages/copies, at record boundaries, between files and at the end of the final file. Priority is final-job boundary, file boundary, record boundary, then page boundary. Tape material and printer firmware may constrain the resulting combination; validate with your real cassette before production.

Simulation is an explicit option and sends no data to a printer. It writes PNG and, for native Raster models, printer-specific PRN output, available in job details. Simulation never increases the real submission counter. A job is fully preflighted before queueing, including all record-dependent formulas and layouts. A single job is limited to 100,000 labels; split larger runs into batches.

Cancel stops future sends; data already handed to Windows/the printer may still print. A connection failure never causes an automatic resend. After a crash, active jobs become Interrupted and require review before reprinting to avoid duplicates. History supports reprinting the saved job request after explicit review.

## Accounts and visibility

The initial local account is the administrator. Open its profile to set a username/password, then enable authentication in Settings. Passwords require at least eight characters and use Argon2 hashes. At least one active password-protected administrator is required before enabling login. The built-in account retains administrator capability for the no-login mode.

There is no contractual user-count cap; practical capacity depends on the PC. Administrators manage users. Each user controls default sharing for templates, saved documents, images, fonts, datasets and uploaded sources. A resource may override that setting with Only me, All users or User default. Other users open shared resources as editable copies; only the owner can overwrite/delete the original.

Administrators see all print jobs and aggregate reports. Ordinary users see their own jobs/reports. Private design resources are not automatically exposed just because another user is an administrator. Account password resets invalidate that account's sessions. Authentication-mode changes invalidate existing sessions.

## Settings, logs, reports and backup

Configure browser port, default language/width/quality, printer timeout, audit-retention days and startup at Windows sign-in. Save before restarting to apply a changed port. Startup uses the current Windows account's Run registry value, not a pre-login Windows service.

Reports separate requested, submitted, simulated, failed, cancelled and interrupted activity by user/date range and export to CSV. Device-confirmed counts remain distinct and are not incremented without a reliable hardware signal.

The application stores data in `%LOCALAPPDATA%\CableLabelStudio`, with logs in `logs`. Settings shows persistent audit events and technical log output. Full backup downloads a ZIP containing the SQLite database and uploaded assets. For restore: stop the app, back up the existing data directory, then extract the ZIP into the data directory. Backups contain account hashes and print data; keep them appropriately protected.

## Validation status

See `ACCEPTANCE.md` for software and installer checks. A physical PT-E550W and its Brother driver were unavailable on the build machine. Physical USB/Wi-Fi printing, actual sizes, half-cut/full-cut combinations and high-resolution results still require acceptance with the user's device. Access import needs verification with a real database and the matching driver. The program does not represent simulations or spool submission as verified physical output.

## Version 1.1.0 features

Creator: **Amir Rahimi**. Advanced label design and printing software, free and open source under the [MIT license](LICENSE.txt). Project, editable source and Windows releases: https://github.com/aa70027/P-touch . Every application page, login screen and installer includes the creator, free license and project link.

### Installation and online updates

The first wizard question is “زبان را انتخاب کنید / Select your language / اختر لغتك”, with three simultaneous buttons: فارسی, English and العربية. Only after language selection are installation mode and destination shown. New install, repair, update, uninstall and custom paths remain available. “Detect Brother printers” in the installer distinguishes USB PnP hardware from installed queues/drivers. Maintenance preserves user data.

Open Settings → Updates & downloads and check GitHub releases. The same page shows installed/release versions, download/install progress, events, errors and the persistent installer log. Preview releases are optional; save the setting or press Check to apply it. Online installation requires the packaged Windows app. Downloads come from this repository's Releases and must pass its SHA-256 checksum before installation. This is transfer-integrity verification, not a publisher code signature. A database backup precedes installation; the installer rolls back previous application files if copying fails. Active print jobs block installation. The local service stops briefly during installation; this page reconnects automatically and displays the result/log. Use the downloadable offline installer if an internet update is unavailable.

### Multi-sheet Excel and a live Windows path

In Data sources, either upload a workbook or choose Link Windows Excel file to open the real Windows file picker. Linked mode stores the original path privately without creating an uploaded copy. All sheets appear as checkboxes; select one or several and press Reload source. Columns are unioned and `_sheet` preserves each record's source worksheet for rules and text bindings. An existing `_sheet` column is preserved as `_sheet_value`. The aggregate limit is 100,000 selected records.

Edit and **save** the workbook in Excel. Preview and creation of a new print job reread the original file without reuploading. Each queued job holds a fresh, fixed record snapshot so later external edits cannot change a running job. Reload source refreshes the visible table and record count. Manual cell editing in the application detaches automatic reads until the next source reload. Change linked file path replaces the original path through another native selection. Missing, inaccessible or exclusively locked files produce an error rather than silently printing stale data. Unsaved Excel changes and formula recalculation are not available; save Excel's calculated values first. Save a dataset to retain the source binding for later sessions. Backups retain linked paths, not external workbook contents; back up those files separately.

### Connections, detection and changing IP addresses

Settings → Connection & discovery configures model, USB/Wi-Fi, Windows queue, IP/port, hostname, MAC and local subnet. Save before identifying. USB model detection uses PnP names/hardware IDs even when the driver is absent; installed driver/queue state is separate. Network model identification uses a read-only SNMP query. With SNMP disabled or blocked, the model stays unknown. TCP reachability alone does not prove model identity or physical completion.

Prefer a stable printer DNS hostname or a DHCP reservation on the router. Alternatively, enter the printer's **Wi-Fi MAC**, enable Find current IP by MAC before printing and choose the local adapter subnet. Search local network displays progress and matching IP/MAC/model candidates. Select the correct result and save. Resolution also runs before a print job starts; a missing/mismatched MAC blocks printing. MAC lookup is limited to the same local link. Routed networks, different VLANs and client isolation need valid DNS/router configuration. Discovery accepts only an explicitly selected local IPv4 subnet of at most 1024 addresses. Unknown model results remain unknown.

**PT-E550W direct mode:** select `Menu → WLAN → Network Mode → Direct Mode` on the printer. Read its network/IP information at `WLAN → Network Status → Direct Mode`; obtain the SSID/key from the printer or official Printer Setting Tool. Open Windows Wi-Fi settings from the app and join the printer's SSID. Enter the displayed IP or search its Wi-Fi MAC. The PC may lose internet access while directly connected, so download updates first.

**Through the router:** select `Menu → WLAN → Network Mode → Infrastructure Mode`, then `WLAN → Network Setting → Infrastructure Mode → Setup Wizard`. Join the router SSID and enter its key on the printer. Connect Windows to the same router over Ethernet or Wi-Fi. Avoid guest networks/client isolation. Save the hostname/IP and MAC in the app. The app does not collect the Wi-Fi password or silently reconfigure the printer. E550W Direct and Infrastructure modes are not simultaneous.

### Other Brother models and official downloads

PT-E550W, PT-P750W and PT-P710BT have documented Raster profiles. E550W/P750W offer USB and Wi-Fi, full/half/no-cut policies. P710BT uses USB here and supports full/no cut, not Wi-Fi or half-cut. These profiles support 3.5–24 mm TZe media and 180×180 / 180×360 rendering.

PT-P700, PT-P900W, PT-P950NW, QL-800, QL-810W and QL-820NWB use an installed official Brother Windows driver, with a USB or network queue. P900/P950 render up to 36 mm at 360×360 / 360×720; the listed QL profiles up to 62 mm at 300×300 / 300×600. A generic Brother Windows driver profile permits additional models after their actual media is configured and verified in the driver. For driver transport, media size, orientation, final quality and physical cuts are controlled by the driver's private properties. App cut policies do not synthesize RAW commands for these models. Incompatible media dimensions are rejected instead of silently scaled. Driver-free direct RAW Wi-Fi is not supported for this group. Their simulation produces PNG; PRN is available only for Raster profiles.

On Updates & downloads, select a model and open its official Brother download page. Choose the Windows version/software on Brother's site, then paste the direct `.exe`, `.msi` or `.zip` download URL into the app. Progress, errors, the downloaded file and SHA-256 appear on the same page. Only HTTPS links on brother.com/subdomains are accepted. Open the downloaded file to install it; drivers are not executed automatically. Brother controls its own driver versions and license terms.

Software and simulation tests do not certify physical printers. Actual USB/Wi-Fi output, dimensions, special media, cutting and resolution require acceptance on each device. Access requires the matching 64-bit ODBC driver and a real database test. See [ACCEPTANCE.md](ACCEPTANCE.md) and [NEXT_UPDATE.md](NEXT_UPDATE.md).

Official references: [E550W network guide](https://download.brother.com/welcome/docp100010/pte550w_eng_net_01.pdf), [E550W/P750W/P710BT Raster reference](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf), [P900W specifications](https://support.brother.com/g/b/spec.aspx?c=my&lang=en&prod=p900weas).
