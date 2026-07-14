# Blueprint Ticker Maker

Generate importable scrolling **Nixie Tubes** banner blueprints for Factorio 2.1.

The browser version runs entirely client-side: enter a message, choose the scroll speed and edge spacing, then copy the generated blueprint string into Factorio. No server and no upload are involved.

The generated design has been tested in-game with the [Nixie Tubes mod](https://mods.factorio.com/mod/nixie-tubes).

## Browser tool

Open `index.html` locally in a modern browser, or publish the repository with GitHub Pages.

1. Enter the banner text.
2. Choose the number of seconds per character shift.
3. Choose the blank tubes added to each edge.
4. Select **Generate blueprint**.
5. Copy or download the blueprint string and import it into Factorio.

The browser needs support for `CompressionStream("deflate")`. Current Firefox, Chrome and Edge releases support it.

### GitHub Pages

After the initial pull request is merged:

1. Open **Settings → Pages** in the repository.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select `main` and `/ (root)`.
4. Save.

The root `index.html` will then become the hosted generator.

## Python command-line version

Python 3.10 or newer is recommended.

```powershell
python generator.py "GOAKILLER900 IS GAY"
```

Custom speed, padding and output files:

```powershell
python generator.py "THE FACTORY MUST GROW" `
  --seconds 0.35 `
  --edge-spaces 2 `
  --output factory-banner.txt `
  --json factory-banner.json
```

## Supported characters

- `A-Z`
- `0-9`
- spaces
- `. ? ! @ [ ] { } ( ) / * - + % :`

Lowercase input is converted to uppercase. Tabs and line breaks become spaces.

## Blueprint size

For a padded banner width of `N`, the proven layout currently uses:

- `N` alpha Nixie tubes
- `N²` frame-selection decider combinators
- 3 arithmetic combinators for the clock

This is intentionally brute-force. It creates a predictable non-overlapping grid and keeps all circuit-wire connections within range, but long messages produce large blueprints.

## Development

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

The project has no runtime Python dependencies outside the standard library.

## License

No license has been selected yet.
