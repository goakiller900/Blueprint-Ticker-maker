#!/usr/bin/env python3
"""Generate a scrolling Nixie Tubes banner blueprint for Factorio 2.1."""

from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path
import sys
import zlib

FACTORIO_VERSION = 562954249109505  # 2.1.11.1, copied from a working blueprint.
MAX_WIDTH = 100

SIGNAL_NAMES = {
    ".": "signal-letter-dot",
    "?": "signal-question-mark",
    "!": "signal-exclamation-mark",
    "@": "signal-at",
    "[": "signal-left-square-bracket",
    "]": "signal-right-square-bracket",
    "{": "signal-curopen",
    "}": "signal-curclose",
    "(": "signal-left-parenthesis",
    ")": "signal-right-parenthesis",
    "/": "signal-slash",
    "*": "signal-multiplication",
    "-": "signal-minus",
    "+": "signal-plus",
    "%": "signal-percent",
    ":": "signal-colon",
}


def signal_name_for(character: str) -> str | None:
    if len(character) == 1 and character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        return f"signal-{character}"
    return SIGNAL_NAMES.get(character)


def normalize_message(raw: str, edge_spaces: int) -> str:
    single_line = " ".join(raw.upper().split())
    if not single_line:
        raise ValueError("The message cannot be empty.")

    for character in single_line:
        if character != " " and signal_name_for(character) is None:
            raise ValueError(f"Unsupported character: {character!r}")

    message = (" " * edge_spaces) + single_line + (" " * edge_spaces)
    if len(message) > MAX_WIDTH:
        raise ValueError(
            f"The padded message is {len(message)} characters; "
            f"this version is limited to {MAX_WIDTH}."
        )
    return message


def build_blueprint(message: str, ticks_per_step: int) -> dict:
    width = len(message)
    frames = width
    entities: list[dict] = []
    wires: list[list[int]] = []
    next_entity = 1

    def add_entity(entity: dict) -> int:
        nonlocal next_entity
        result = dict(entity)
        result["entity_number"] = next_entity
        entities.append(result)
        next_entity += 1
        return result["entity_number"]

    tube_numbers = []
    for column in range(width):
        tube_numbers.append(
            add_entity(
                {
                    "name": "nixie-tube-alpha",
                    "position": {"x": column + 0.5, "y": 0},
                    "always_on": True,
                }
            )
        )

    counter = add_entity(
        {
            "name": "arithmetic-combinator",
            "position": {"x": 0, "y": 2.5},
            "direction": 4,
            "control_behavior": {
                "arithmetic_conditions": {
                    "first_signal": {"type": "virtual", "name": "signal-T"},
                    "operation": "+",
                    "second_constant": 1,
                    "output_signal": {"type": "virtual", "name": "signal-T"},
                }
            },
        }
    )

    divider = add_entity(
        {
            "name": "arithmetic-combinator",
            "position": {"x": 2, "y": 2.5},
            "direction": 4,
            "control_behavior": {
                "arithmetic_conditions": {
                    "first_signal": {"type": "virtual", "name": "signal-T"},
                    "operation": "/",
                    "second_constant": ticks_per_step,
                    "output_signal": {"type": "virtual", "name": "signal-I"},
                }
            },
        }
    )

    modulo = add_entity(
        {
            "name": "arithmetic-combinator",
            "position": {"x": 4, "y": 2.5},
            "direction": 4,
            "control_behavior": {
                "arithmetic_conditions": {
                    "first_signal": {"type": "virtual", "name": "signal-I"},
                    "operation": "%",
                    "second_constant": frames,
                    "output_signal": {"type": "virtual", "name": "signal-I"},
                }
            },
        }
    )

    wires.extend(
        [
            [counter, 3, counter, 1],
            [counter, 4, divider, 2],
            [divider, 4, modulo, 2],
        ]
    )

    matrix: list[list[int]] = [[0] * width for _ in range(frames)]

    for frame in range(frames):
        displayed = message[frame:] + message[:frame]
        for column, character in enumerate(displayed):
            blank = character == " "
            output_signal = "signal-A" if blank else signal_name_for(character)
            if output_signal is None:
                raise ValueError(f"No signal mapping for {character!r}")

            matrix[frame][column] = add_entity(
                {
                    "name": "decider-combinator",
                    "position": {
                        "x": column + 0.5,
                        "y": 5.5 + frame * 2,
                    },
                    "direction": 0,
                    "control_behavior": {
                        "decider_conditions": {
                            "conditions": [
                                {
                                    "first_signal": {
                                        "type": "virtual",
                                        "name": "signal-I",
                                    },
                                    "comparator": "=",
                                    "constant": -1 if blank else frame,
                                }
                            ],
                            "outputs": [
                                {
                                    "signal": {
                                        "type": "virtual",
                                        "name": output_signal,
                                    },
                                    "copy_count_from_input": False,
                                    "constant": 1,
                                }
                            ],
                        }
                    },
                }
            )

    for frame in range(frames):
        for column in range(width - 1):
            wires.append(
                [matrix[frame][column], 2, matrix[frame][column + 1], 2]
            )

    for frame in range(frames - 1):
        wires.append([matrix[frame][0], 2, matrix[frame + 1][0], 2])

    wires.append([modulo, 4, matrix[0][0], 2])

    for column in range(width):
        wires.append([tube_numbers[column], 1, matrix[0][column], 3])
        for frame in range(frames - 1):
            wires.append(
                [matrix[frame][column], 3, matrix[frame + 1][column], 3]
            )

    return {
        "blueprint": {
            "item": "blueprint",
            "label": f"{message.strip()} — Scrolling Nixie Banner",
            "description": (
                f"Generated {width}-tube cyclic Nixie banner. "
                f"Shifts one character every {ticks_per_step} ticks."
            ),
            "icons": [
                {
                    "signal": {"type": "item", "name": "nixie-tube-alpha"},
                    "index": 1,
                }
            ],
            "entities": entities,
            "wires": wires,
            "version": FACTORIO_VERSION,
        }
    }


def encode_blueprint(blueprint: dict) -> str:
    raw = json.dumps(
        blueprint, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "0" + base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def validate_structure(blueprint: dict) -> None:
    data = blueprint["blueprint"]
    entity_by_number = {
        entity["entity_number"]: entity for entity in data["entities"]
    }
    if len(entity_by_number) != len(data["entities"]):
        raise ValueError("Duplicate entity numbers detected.")

    max_distance = 0.0
    for first, _, second, _ in data["wires"]:
        if first not in entity_by_number or second not in entity_by_number:
            raise ValueError("Wire references a missing entity.")
        a = entity_by_number[first]["position"]
        b = entity_by_number[second]["position"]
        max_distance = max(
            max_distance,
            math.hypot(a["x"] - b["x"], a["y"] - b["y"]),
        )

    if max_distance > 5.5 + 1e-9:
        raise ValueError(f"Unexpected long circuit wire: {max_distance:.2f} tiles.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a scrolling Nixie Tubes Factorio blueprint."
    )
    parser.add_argument("message", help="Text to show on the banner.")
    parser.add_argument(
        "--seconds",
        type=float,
        default=0.5,
        help="Seconds between character shifts (default: 0.5).",
    )
    parser.add_argument(
        "--edge-spaces",
        type=int,
        default=1,
        help="Blank tubes placed on each edge (default: 1).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("nixie-scrolling-banner-blueprint.txt"),
        help="Output text file.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        type=Path,
        help="Optionally also write the decoded blueprint JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.seconds <= 0:
        print("error: --seconds must be greater than zero", file=sys.stderr)
        return 2
    if not 0 <= args.edge_spaces <= 10:
        print("error: --edge-spaces must be between 0 and 10", file=sys.stderr)
        return 2

    try:
        message = normalize_message(args.message, args.edge_spaces)
        ticks = max(1, round(args.seconds * 60))
        blueprint = build_blueprint(message, ticks)
        validate_structure(blueprint)
        blueprint_string = encode_blueprint(blueprint)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    args.output.write_text(blueprint_string + "\n", encoding="utf-8")
    if args.json_output:
        args.json_output.write_text(
            json.dumps(blueprint, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    width = len(message)
    print(f"Wrote {args.output}")
    print(f"Tubes: {width}")
    print(f"Frame deciders: {width * width}")
    print(f"Total entities: {len(blueprint['blueprint']['entities'])}")
    print(f"Ticks per shift: {ticks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
