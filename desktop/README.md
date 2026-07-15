# Desktop application

`desktop/app.py` is a small cross-platform Tkinter application for Blueprint
Ticker Maker.

## Safety properties

The runtime application:

- is fully offline;
- contains no telemetry, advertisements, update checker, or analytics;
- imports no network or subprocess modules;
- does not inspect Factorio saves or configuration;
- writes files only after the user chooses a destination in a Save dialog;
- produces plain Factorio blueprint strings and optional decoded JSON.

The unit tests include a static import check for common network and process
modules.

## Run from source

Python 3.10 or newer:

```powershell
python desktop/app.py
```

Run the non-GUI self-test:

```powershell
python desktop/app.py --self-test
```

## Local executable build

Install the pinned build dependency:

```powershell
python -m pip install -r desktop/requirements-build.txt
```

Build:

```powershell
pyinstaller --noconfirm --clean --onefile --windowed `
  --name BlueprintTickerMaker `
  --paths desktop `
  desktop/app.py
```

The executable is written to `dist/`.

PyInstaller is not a cross-compiler. Build Windows on Windows, Linux on Linux,
and macOS on macOS.

## GitHub builds

`.github/workflows/build-desktop.yml`:

1. runs all desktop unit tests;
2. compiles the Python source;
3. builds standalone applications on Windows, Linux, and macOS;
4. runs the bundled application's `--self-test`;
5. uploads each compiled application as a GitHub Actions artifact.

The workflow uses only official GitHub actions plus the pinned PyInstaller
package from PyPI.
