Offline release package for PSTT_TOOL
===================================

Contents
- This package is designed to be created on an internet-connected PC and transferred
  to the offline server. It contains:
  - a Firefox legacy build (e.g. firefox-115.0esr.zip)
  - a `wheelhouse/` directory with .whl files (pip download output)
  - optional Python installer (python-3.11.x-amd64.exe)
  - helper scripts: `install_offline.ps1`, `run_firefox_portable.ps1`

How to prepare the package (on internet PC)
-------------------------------------------
1. Ensure you have a wheelhouse folder already created with:
     pip download -r requirements.txt -d C:\temp\pstt_wheelhouse

2. In the `release/` folder run:
     .\prepare_firefox_package.ps1 -WheelhousePath C:\temp\pstt_wheelhouse -PythonInstaller C:\temp\python-3.11.x-amd64.exe -OutDir C:\temp\pstt_release

   The script will call `download_firefox_legacy.ps1` to fetch the legacy Firefox archive
   and then create `pstt_firefox_legacy_release.zip` in the OutDir.

3. Transfer `pstt_firefox_legacy_release.zip` to the offline server (USB, SMB share).

How to install on the offline server
------------------------------------
1. Extract the ZIP to `C:\App\PSTT_TOOL\release_content` (or similar).
2. Run the helper to extract and start Firefox portable if needed:
     .\run_firefox_portable.ps1 -SourceFile .\firefox-115.0esr.zip -Dest C:\tools\FirefoxPortable

3. Install the app dependencies and create venv:
     .\install_offline.ps1 -Wheelhouse .\wheelhouse -PythonInstaller .\python-3.11.x-amd64.exe

   If Python is already installed, omit the `-PythonInstaller` parameter.

4. Start the app in foreground for testing:
     .\.venv\Scripts\python.exe main.py --host 127.0.0.1 --port 8000

5. (Optional) Install as a Windows service using `nssm.exe` (include nssm in the release):
     .\nssm.exe install PSTT_Tool "C:\App\PSTT_TOOL\release_content\.venv\Scripts\python.exe" "C:\App\PSTT_TOOL\release_content\main.py --host 127.0.0.1 --port 8000"

Notes and troubleshooting
- If a package in `requirements.txt` has no prebuilt wheel for Windows/Python 3.11, pip will try to compile from source and fail on the offline server. In that case build the wheel on a similar Windows machine and add it to the wheelhouse.
- If the Firefox package you downloaded is a `.paf.exe` that downloads at runtime, prefer to use the `.zip` from Mozilla archive or extract the EXE with 7-Zip on the internet machine and include the extracted files in the release ZIP.
