# Blueprint Ticker Maker

Generate scrolling Factorio 2.1 banners as importable blueprint strings.

The project currently supports:

- **Vanilla lamps — compact:** a 5×7 dot-matrix ticker using bit-packed row masks. This is the recommended lamp design.
- **Vanilla lamps — compatibility:** the larger, simpler frame-memory design that was verified in-game first.
- **Nixie Tubes:** one alpha Nixie tube per character cell. Requires the `nixie-tubes` mod.

Everything runs locally. The browser page has no server and does not upload the message.

## Browser tool

Open `index.html` in a current Firefox, Chrome, or Edge release.

1. Choose an output mode.
2. Enter the message.
3. Configure the display.
4. Generate and copy the blueprint string.
5. Import it in Factorio.

The page uses the browser's standard `CompressionStream("deflate")` API to produce Factorio's zlib-compressed blueprint format.

## Configurable options

Shared options:

- message
- seconds per scroll step
- left or right scrolling
- display width

Lamp options:

- compact or compatibility architecture
- 5×7 font
- logical screen width
- pixel scale from 1×1 through 4×4 lamps
- character spacing
- repeat gap
- default, red, green, blue, yellow, pink, cyan, or white lamps
- compact-ROM block width, or automatic near-square packing

Nixie options:

- character-cell display width
- blank edge characters
- scroll direction and speed

## Why compact lamp mode is smaller

The original working lamp prototype stored seven complete output rows for every pixel frame:

```text
frames × 7 decider combinators
```

Compact mode packs each row into a 30-bit integer. One frame decider can therefore output all seven row masks at once. A small arithmetic decoder under every logical display column extracts the correct bit:

```text
frames × ceil(display_width / 30) frame deciders
+ display_width arithmetic decoders
```

For the original 24×7 `GOAKILLER900 IS GAY` test:

| Architecture | Lamps | Memory deciders | Column decoders | Total entities |
|---|---:|---:|---:|---:|
| Compatibility | 168 | 833 | 0 | 1,004 |
| Compact | 168 | 119 | 24 | 314 |

The exact frame count depends on the message, character spacing, and repeat gap.

## Python command line

Python 3.10 or newer is recommended.

Compact vanilla-lamp ticker:

```powershell
python generator.py "THE FACTORY MUST GROW" `
  --mode lamp-compact `
  --width 30 `
  --seconds 0.2 `
  --direction left `
  --character-spacing 1 `
  --repeat-gap 8 `
  --scale 1 `
  --color yellow `
  --output factory-ticker.txt `
  --json factory-ticker.json
```

Compatibility lamp mode:

```powershell
python generator.py "HELLO WORLD" --mode lamp-compatible --width 24
```

Nixie Tubes mode:

```powershell
python generator.py "HELLO WORLD" `
  --mode nixie `
  --width 13 `
  --edge-spaces 1 `
  --seconds 0.5
```

## Supported font characters

Lamp mode supports:

```text
A-Z  0-9  space  . , ! ? - + : / ( ) = _
```

Nixie mode supports letters, digits, spaces, and the virtual-signal punctuation mapped in `generator.py`.

Input is converted to uppercase and repeated whitespace is collapsed to one space.

## Size limits

- Compact lamp width: up to 150 logical pixel columns.
- Compatibility lamp width: up to 36 logical pixel columns.
- Nixie width: up to 100 character cells.
- Lamp pixel scale: 1 through 4.

Long messages still create many frames. Compact mode makes each frame much cheaper, but a large display with a long message can still produce a large blueprint.

## Testing

Run:

```powershell
python -m unittest discover -s tests -v
```

The tests verify:

- the original 21-tube Nixie structure
- compact and compatibility lamp generation
- multi-segment compact displays
- scaled pixels
- left/right frame generation
- circuit-wire distances
- Base64/zlib blueprint round trips

GitHub Actions runs the Python tests and checks the browser JavaScript syntax.
