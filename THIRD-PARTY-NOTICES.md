# Third-party notices

Cable Label Studio is independent of Brother Industries. Brother and P-touch are their owners' marks. No Brother logo, driver, proprietary font or vendor SDK is redistributed in this package.

Runtime dependencies are pinned in `requirements.txt`. The build copies installed distribution license/notice metadata into `third-party-licenses/`. Important components include:

| Component | Purpose | Project |
|---|---|---|
| CPython | Bundled interpreter | https://www.python.org/psf/license/ |
| FastAPI, Starlette, Uvicorn, Pydantic | Local web server and validation | https://github.com/fastapi/fastapi |
| Pillow, FreeType | Raster graphics and font rendering | https://github.com/python-pillow/Pillow |
| arabic-reshaper | Arabic/Persian contextual forms | https://github.com/mpcabd/python-arabic-reshaper |
| python-bidi | Unicode bidirectional ordering | https://github.com/MeirKriheli/python-bidi |
| openpyxl, xlrd | Spreadsheet import | https://openpyxl.readthedocs.io/ |
| pyodbc | Access ODBC connectivity | https://github.com/mkleehammer/pyodbc |
| pywin32 | Windows printing and process integration | https://github.com/mhammond/pywin32 |
| argon2-cffi | Password hashing | https://github.com/hynek/argon2-cffi |
| fontTools | Uploaded font validation | https://github.com/fonttools/fonttools |
| qrcode | QR generation | https://github.com/lincolnloop/python-qrcode |
| PyInstaller | Executable packaging | https://pyinstaller.org/ |

The WinForms installer is original source in `installer/Setup.cs` and uses Windows framework libraries. System fonts are referenced from the user's Windows installation; users supply any additional fonts.

Printer protocol reference: [Brother PT-E550W/P750W/P710BT Raster Command Reference v1.02](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf). Raster code is implemented in this repository; it does not embed an external printer library. Device constraints and physical validation limits are documented in `ACCEPTANCE.md`.
