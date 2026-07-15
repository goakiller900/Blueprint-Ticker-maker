# Desktop application

`desktop/app.py` is the full Blueprint Ticker Maker Display Studio.

## Features

- static and animated vanilla-lamp displays;
- static and animated alpha Nixie displays;
- continuous, one-shot, and bouncing animation;
- independent logical display width/height;
- independent physical pixel width/height from 1 through 8 lamps;
- multiline static text, alignment, spacing, and padding;
- selectable compact circuit/ROM placement;
- live preview and detailed size/entity statistics;
- presets and save/load project files;
- 5×7 custom-font editor with JSON import/export;
- blueprint-book export.

## Safety properties

The runtime application:

- is fully offline;
- contains no telemetry, advertisements, update checker, or analytics;
- imports no network or subprocess modules;
- does not inspect Factorio saves or configuration;
- writes files only after the user chooses a destination in a Save dialog;
- produces plain Factorio blueprint strings, blueprint books, project JSON, font JSON, and optional decoded blueprint JSON.

The unit tests include a static import check for common network and process modules.

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

```powershell
python -m pip install -r desktop/requirements-build.txt
pyinstaller --noconfirm --clean --onefile --windowed `
  --name BlueprintTickerMaker `
  --paths desktop `
  desktop/app.py
```

The executable is written to `dist/`. PyInstaller is not a cross-compiler, so each operating system is built on its matching GitHub runner.

## GitHub builds and Releases

`.github/workflows/build-desktop.yml` runs tests, compiles the source, builds Windows/Linux/macOS applications, runs each bundled `--self-test`, uploads Actions artifacts, updates the rolling **Latest automatic build** release on successful `main` builds, and creates permanent releases for `v*` tags.
