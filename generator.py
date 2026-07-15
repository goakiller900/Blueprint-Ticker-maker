#!/usr/bin/env python3
"""Command-line interface for Blueprint Ticker Maker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from desktop.blueprint_core import TickerConfig, generate, generate_blueprint_book


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Factorio display and ticker blueprints.")
    parser.add_argument("message", help="Message to display. Use a quoted multiline value for static signs.")
    parser.add_argument("--mode", choices=("lamp-compact", "lamp-compatible", "lamp-static", "nixie", "nixie-static"), default="lamp-compact")
    parser.add_argument("--animation", choices=("loop", "once", "bounce", "static"), default="loop")
    parser.add_argument("--seconds", type=float, default=0.2, help="Seconds per animation step.")
    parser.add_argument("--direction", choices=("left", "right"), default="left")
    parser.add_argument("--width", type=int, default=24, help="Logical display width.")
    parser.add_argument("--height", type=int, default=7, help="Logical lamp display height.")
    parser.add_argument("--pixel-width", type=int, default=1, help="Physical lamps per logical pixel horizontally.")
    parser.add_argument("--pixel-height", type=int, default=1, help="Physical lamps per logical pixel vertically.")
    parser.add_argument("--character-spacing", type=int, default=1)
    parser.add_argument("--repeat-gap", type=int, default=6)
    parser.add_argument("--start-padding", type=int, default=0)
    parser.add_argument("--end-padding", type=int, default=0)
    parser.add_argument("--pause", type=float, default=0.0, help="Pause at the end of an animation cycle in seconds.")
    parser.add_argument("--full-message-pause", type=float, default=0.0, help="Pause on a centered full message when it fits.")
    parser.add_argument("--color", default="yellow")
    parser.add_argument("--layout", choices=("compact-square", "below", "above", "left", "right", "strip"), default="compact-square")
    parser.add_argument("--rom-columns", type=int, default=0)
    parser.add_argument("--horizontal-align", choices=("left", "center", "right"), default="center")
    parser.add_argument("--vertical-align", choices=("top", "middle", "bottom"), default="middle")
    parser.add_argument("--line-spacing", type=int, default=1)
    parser.add_argument("--edge-spaces", type=int, default=1)
    parser.add_argument("--font-json", type=Path, help="Optional custom 5×7 font JSON file.")
    parser.add_argument("--book", action="store_true", help="Write a blueprint book containing useful variants.")
    parser.add_argument("-o", "--output", type=Path, default=Path("factorio-display-blueprint.txt"))
    parser.add_argument("--json", dest="json_output", type=Path, help="Also write decoded blueprint JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    custom_font: dict[str, list[str]] = {}
    if args.font_json:
        try:
            custom_font = json.loads(args.font_json.read_text(encoding="utf-8"))
        except Exception as error:
            print(f"error: could not read font JSON: {error}", file=sys.stderr)
            return 2

    config = TickerConfig(
        message=args.message, mode=args.mode, animation=args.animation, seconds_per_step=args.seconds,
        direction=args.direction, display_width=args.width, display_height=args.height,
        pixel_width=args.pixel_width, pixel_height=args.pixel_height,
        character_spacing=args.character_spacing, repeat_gap=args.repeat_gap,
        start_padding=args.start_padding, end_padding=args.end_padding,
        pause_seconds=args.pause, full_message_pause_seconds=args.full_message_pause,
        lamp_color=args.color, circuit_layout=args.layout, rom_columns=args.rom_columns,
        horizontal_align=args.horizontal_align, vertical_align=args.vertical_align,
        line_spacing=args.line_spacing, nixie_edge_spaces=args.edge_spaces, custom_font=custom_font,
    )

    try:
        if args.book:
            decoded, encoded = generate_blueprint_book(config)
            stats = {"mode": "Blueprint book", "entities": "multiple", "frames": "multiple", "max_wire_distance": "varies"}
        else:
            result = generate(config)
            decoded, encoded, stats = result.blueprint, result.blueprint_string, result.stats
    except (ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    args.output.write_text(encoded + "\n", encoding="utf-8")
    if args.json_output is not None:
        args.json_output.write_text(json.dumps(decoded, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Mode: {stats['mode']}")
    print(f"Entities: {stats['entities']}")
    print(f"Frames: {stats['frames']}")
    print(f"Max wire distance: {stats['max_wire_distance']} tiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
