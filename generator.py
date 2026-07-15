#!/usr/bin/env python3
"""Command-line interface for Blueprint Ticker Maker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from desktop.blueprint_core import TickerConfig, generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate scrolling Factorio ticker blueprints.",
    )
    parser.add_argument("message", help="Message to display.")
    parser.add_argument(
        "--mode",
        choices=("lamp-compact", "lamp-compatible", "nixie"),
        default="lamp-compact",
        help="Ticker architecture (default: lamp-compact).",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=0.2,
        help="Seconds per scroll step (default: 0.2).",
    )
    parser.add_argument(
        "--direction",
        choices=("left", "right"),
        default="left",
        help="Scroll direction (default: left).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=24,
        help="Display width in logical columns/cells (default: 24).",
    )
    parser.add_argument(
        "--character-spacing",
        type=int,
        default=1,
        help="Blank pixel columns between lamp-font characters (default: 1).",
    )
    parser.add_argument(
        "--repeat-gap",
        type=int,
        default=6,
        help="Blank pixel columns between message repetitions (default: 6).",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Lamp pixel scale from 1 through 4 (default: 1).",
    )
    parser.add_argument(
        "--color",
        default="yellow",
        help="Lamp colour name (default: yellow).",
    )
    parser.add_argument(
        "--rom-columns",
        type=int,
        default=0,
        help="Compact ROM block width; 0 selects automatic layout.",
    )
    parser.add_argument(
        "--edge-spaces",
        type=int,
        default=1,
        help="Blank edge characters for Nixie mode (default: 1).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("factorio-ticker-blueprint.txt"),
        help="Blueprint-string output file.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        type=Path,
        help="Optionally also write decoded blueprint JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = TickerConfig(
        message=args.message,
        mode=args.mode,
        seconds_per_step=args.seconds,
        direction=args.direction,
        display_width=args.width,
        character_spacing=args.character_spacing,
        repeat_gap=args.repeat_gap,
        pixel_scale=args.scale,
        lamp_color=args.color,
        rom_columns=args.rom_columns,
        nixie_edge_spaces=args.edge_spaces,
    )

    try:
        result = generate(config)
    except (ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    args.output.write_text(result.blueprint_string + "\n", encoding="utf-8")
    if args.json_output is not None:
        args.json_output.write_text(
            json.dumps(result.blueprint, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"Wrote {args.output}")
    print(f"Mode: {result.stats['mode']}")
    print(f"Entities: {result.stats['entities']}")
    print(f"Frames: {result.stats['frames']}")
    print(f"Max wire distance: {result.stats['max_wire_distance']} tiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())