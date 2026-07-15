# Blueprint Ticker Maker

Generate Factorio 2.1 lamp displays, scrolling tickers, static signs, Nixie displays, and blueprint books as importable blueprint strings.

Everything in the desktop application and Python generator runs locally. There is no telemetry and messages are never uploaded.

## Display modes

- **Vanilla lamps — scrolling compact:** bit-packed memory and per-column decoders; recommended for animated lamp displays.
- **Vanilla lamps — scrolling compatibility:** larger frame-memory architecture kept as a simple fallback.
- **Vanilla lamps — static sign:** no animation clock; supports multiline signs.
- **Nixie Tubes — scrolling:** alpha Nixie ticker; requires the `nixie-tubes` mod.
- **Nixie Tubes — static sign:** fixed Nixie text with a tiny per-cell signal source.

## Desktop Display Studio

The cross-platform Tkinter application in `desktop/` includes:

- continuous, one-shot, and bouncing scrolling;
- left/right direction without mirroring the text;
- configurable repeat pauses and full-message pauses;
- independent logical **display width and height**;
- independent **pixel width and pixel height** from 1 to 8 lamps per logical pixel;
- character spacing, start padding, end padding, and loop gap;
- top/middle/bottom and left/center/right alignment;
- multiline static lamp signs;
- compact, above, below, left, right, and strip circuit/ROM layouts;
- live animated preview;
- entity count, footprint, frame count, blueprint size, and large-build warnings;
- built-in presets;
- save/load project files;
- a clickable 5×7 custom-font editor with JSON import/export;
- variant blueprint-book export;
- plain blueprint string and decoded JSON export.

Run from source:

```powershell
python desktop/app.py
```

Compiled Windows, Linux, and macOS builds are produced by `.github/workflows/build-desktop.yml`. Successful `main` builds update the rolling **Latest automatic build** GitHub Release, while `v*` tags create permanent versioned releases.

## Variable display and lamp dimensions

Logical display dimensions and physical pixel dimensions are separate. For example:

```text
Logical display: 40 × 14 pixels
Pixel size:       2 × 3 lamps
Physical screen:  80 × 42 lamps
```

This allows very wide, very tall, stretched, or oversized billboard pixels without forcing square pixels.

## Animation behaviour

Scrolling modes support:

- continuous loop;
- scroll once and stop;
- bounce back and forth;
- blank start/end padding;
- a pause at the end of the animation cycle;
- an optional centered full-message pause when the complete message fits on screen.

## Static signs

Lamp static mode can render multiple lines into any configured logical width/height. Alignment and line spacing control where the 5×7 text is placed. A single constant signal drives the finished matrix, so there is no frame memory or clock.

## Custom fonts

The built-in font is 5×7, but any character can be overridden or added with the desktop font editor. Custom glyphs are stored inside project files and can also be imported/exported as JSON.

A font JSON object maps one character to seven five-bit rows:

```json
{
  "€": [
    "11111",
    "10000",
    "11110",
    "10000",
    "11111",
    "00000",
    "00000"
  ]
}
```

## Project files and presets

Project JSON saves the complete generator configuration, including custom glyphs. Built-in presets provide quick starting points for common ticker, billboard, warning-sign, station-sign, and Nixie layouts.

## Blueprint books

The desktop app and CLI can export a Factorio blueprint book containing useful variants of the current configuration. Lamp projects include static, compact scrolling, and—when the width allows it—compatibility scrolling variants. Nixie projects include static and scrolling variants.

## Python command line

Python 3.10 or newer is recommended.

```powershell
python generator.py "THE FACTORY MUST GROW" `
  --mode lamp-compact `
  --animation bounce `
  --width 40 `
  --height 14 `
  --pixel-width 2 `
  --pixel-height 3 `
  --direction left `
  --start-padding 40 `
  --end-padding 40 `
  --pause 1.5 `
  --layout compact-square `
  --output factory-display.txt
```

Static multiline sign:

```powershell
python generator.py "ASSEMBLY\nAREA 4" `
  --mode lamp-static `
  --animation static `
  --width 40 `
  --height 16 `
  --pixel-width 2 `
  --pixel-height 2
```

Add `--book` to export a variant blueprint book instead of a single blueprint.

## Browser tool

`index.html` remains a lightweight standalone browser generator for the original ticker workflows. The desktop application and CLI contain the complete Display Studio feature set described above.

## Testing

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s desktop/tests -v
python desktop/app.py --self-test
```

Tests cover known compact/compatibility structures, static and Nixie modes, variable physical pixel dimensions, all compact circuit layouts, animation behaviours, right-scroll orientation, custom fonts, project round trips, blueprint books, Base64/zlib round trips, wire distances, and offline-runtime import restrictions.

## Safety

The desktop runtime has no network, subprocess, telemetry, advertisement, or automatic-update code. It does not inspect Factorio saves. Files are written only when the user explicitly chooses a destination in a Save dialog.

See `PRIVACY.md`, `SECURITY.md`, and `desktop/README.md` for more details.

## Licence

MIT. See `LICENSE`.
