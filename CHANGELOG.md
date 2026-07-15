# Changelog

## 0.2.0 — Display Studio

This feature release expands Blueprint Ticker Maker from a scrolling ticker generator into a more general Factorio display and sign generator.

### Added

- Static vanilla-lamp signs and static Nixie signs.
- Independent logical display width and height.
- Independent lamp pixel width and height for rectangular pixels such as 2×3 lamps.
- Loop, one-shot, bounce, and static animation behaviours.
- Start padding, end padding, repeat gaps, and pause controls.
- Circuit placement presets for below, above, left, right, compact-square, and strip layouts.
- Horizontal and vertical text alignment.
- Multiline static lamp signs with configurable line spacing.
- Built-in 5×7 font editor with custom glyph import and export.
- Project preset save/load support.
- Blueprint-book export containing useful display variants.
- Expanded footprint, entity-count, frame-count, blueprint-size, and large-build statistics.
- Expanded command-line options for the new display controls.

### Changed

- Desktop application version is now 0.2.0.
- Lamp pixel scaling is no longer restricted to square pixels.
- Generator internals now support variable logical display heights while preserving the original 5×7 font source.

### Validation status

The automated generator test suite covers the new modes, independent pixel dimensions, custom fonts, blueprint books, animation behaviours, circuit layouts, project round trips, wire lengths, and Factorio blueprint encode/decode round trips.

The new display modes should receive final in-game import and behaviour checks before this release is considered stable.
