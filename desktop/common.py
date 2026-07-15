"""Shared validation, rendering, encoding, and circuit helpers."""

from __future__ import annotations

import base64
import json
import math
import re
import zlib
from typing import Iterable

try:
    from .catalog import (
        FONT_5X7,
        LAMP_COLORS,
        MODE_LABELS,
        NIXIE_SIGNAL_NAMES,
    )
    from .models import BlueprintBuilder, Direction, Mode, TickerConfig
except ImportError:
    from catalog import FONT_5X7, LAMP_COLORS, MODE_LABELS, NIXIE_SIGNAL_NAMES
    from models import BlueprintBuilder, Direction, Mode, TickerConfig


def normalize_message(raw: str, mode: Mode) -> str:
    message = re.sub(r"\s+", " ", raw.upper()).strip()
    if not message:
        raise ValueError("Enter a message.")

    for character in message:
        if mode == "nixie":
            if character == " ":
                continue
            if character.isascii() and (character.isalpha() or character.isdigit()):
                continue
            if character in NIXIE_SIGNAL_NAMES:
                continue
            raise ValueError(f"Nixie mode does not support {character!r}.")
        elif character not in FONT_5X7:
            raise ValueError(f"Lamp font does not support {character!r}.")
    return message


def validate_config(config: TickerConfig) -> str:
    if config.mode not in MODE_LABELS:
        raise ValueError("Unknown output mode.")
    if config.direction not in ("left", "right"):
        raise ValueError("Direction must be left or right.")
    if not (1 / 60 <= config.seconds_per_step <= 60):
        raise ValueError("Seconds per step must be between 1/60 and 60.")
    if config.character_spacing not in range(0, 6):
        raise ValueError("Character spacing must be from 0 through 5.")
    if config.repeat_gap not in range(0, 61):
        raise ValueError("Repeat gap must be from 0 through 60.")
    if config.pixel_scale not in range(1, 5):
        raise ValueError("Pixel scale must be from 1 through 4.")
    if config.lamp_color not in LAMP_COLORS:
        raise ValueError("Unknown lamp colour.")
    if config.rom_columns not in range(0, 31):
        raise ValueError("ROM columns must be automatic (0) or 1 through 30.")
    if config.nixie_edge_spaces not in range(0, 11):
        raise ValueError("Nixie edge spaces must be from 0 through 10.")

    if config.mode == "lamp-compact" and not (1 <= config.display_width <= 150):
        raise ValueError("Compact lamp width must be from 1 through 150.")
    if config.mode == "lamp-compatible" and not (1 <= config.display_width <= 36):
        raise ValueError("Compatibility lamp width must be from 1 through 36.")
    if config.mode == "nixie" and not (1 <= config.display_width <= 100):
        raise ValueError("Nixie width must be from 1 through 100.")

    return normalize_message(config.message, config.mode)


def signal_id(name: str) -> dict[str, str]:
    return {"type": "virtual", "name": name}


def nixie_signal_name(character: str) -> str:
    if character.isascii() and (character.isalpha() or character.isdigit()):
        return f"signal-{character}"
    result = NIXIE_SIGNAL_NAMES.get(character)
    if result is None:
        raise ValueError(f"No Nixie signal mapping for {character!r}.")
    return result


def render_message_columns(
    message: str,
    character_spacing: int,
    repeat_gap: int,
) -> list[tuple[int, ...]]:
    columns: list[tuple[int, ...]] = []
    for index, character in enumerate(message):
        glyph = FONT_5X7[character]
        for x in range(5):
            columns.append(tuple(int(glyph[y][x]) for y in range(7)))
        if index != len(message) - 1:
            columns.extend([(0,) * 7] * character_spacing)
    columns.extend([(0,) * 7] * repeat_gap)
    return columns or [(0,) * 7]


def visible_pixel_frame(
    stream: list[tuple[int, ...]],
    frame: int,
    width: int,
    direction: Direction,
) -> list[tuple[int, ...]]:
    # Direction changes the scrolling offset, not the left-to-right order of
    # the display columns. Using a negative column step mirrors the text.
    offset = frame if direction == "left" else -frame
    return [
        stream[(offset + column) % len(stream)]
        for column in range(width)
    ]


def visible_text_frame(
    ring: str,
    frame: int,
    width: int,
    direction: Direction,
) -> str:
    # Preserve normal character order while moving the viewport in the
    # opposite direction for right-scrolling text.
    offset = frame if direction == "left" else -frame
    return "".join(
        ring[(offset + column) % len(ring)]
        for column in range(width)
    )


def add_clock(
    builder: BlueprintBuilder,
    frames: int,
    ticks: int,
    x: float,
    y: float,
) -> tuple[int, int, int]:
    counter = builder.entity(
        name="arithmetic-combinator",
        position={"x": x, "y": y},
        direction=4,
        control_behavior={
            "arithmetic_conditions": {
                "first_signal": signal_id("signal-T"),
                "operation": "+",
                "second_constant": 1,
                "output_signal": signal_id("signal-T"),
            }
        },
    )
    divider = builder.entity(
        name="arithmetic-combinator",
        position={"x": x + 2, "y": y},
        direction=4,
        control_behavior={
            "arithmetic_conditions": {
                "first_signal": signal_id("signal-T"),
                "operation": "/",
                "second_constant": ticks,
                "output_signal": signal_id("signal-I"),
            }
        },
    )
    modulo = builder.entity(
        name="arithmetic-combinator",
        position={"x": x + 4, "y": y},
        direction=4,
        control_behavior={
            "arithmetic_conditions": {
                "first_signal": signal_id("signal-I"),
                "operation": "%",
                "second_constant": frames,
                "output_signal": signal_id("signal-I"),
            }
        },
    )
    builder.wire(counter, 3, counter, 1)
    builder.wire(counter, 4, divider, 2)
    builder.wire(divider, 4, modulo, 2)
    return counter, divider, modulo


def lamp_entity(
    builder: BlueprintBuilder,
    x: float,
    y: float,
    row_signal: str,
    color: dict[str, float],
) -> int:
    return builder.entity(
        name="small-lamp",
        position={"x": x, "y": y},
        color=dict(color),
        always_on=True,
        control_behavior={
            "circuit_enabled": True,
            "use_colors": False,
            "circuit_condition": {
                "first_signal": signal_id(row_signal),
                "comparator": ">",
                "constant": 0,
            },
        },
    )


def chain(
    builder: BlueprintBuilder,
    entities: Iterable[int],
    connector: int,
) -> None:
    items = list(entities)
    for first, second in zip(items, items[1:]):
        builder.wire(first, connector, second, connector)


def encode_blueprint(blueprint: dict) -> str:
    raw = json.dumps(
        blueprint,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "0" + base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def decode_blueprint(blueprint_string: str) -> dict:
    text = blueprint_string.strip()
    if not text.startswith("0"):
        raise ValueError("Factorio blueprint strings must start with 0.")
    return json.loads(zlib.decompress(base64.b64decode(text[1:])))


def max_wire_distance(blueprint: dict) -> float:
    data = blueprint["blueprint"]
    entities = {
        entity["entity_number"]: entity
        for entity in data["entities"]
    }
    maximum = 0.0
    for first, _, second, _ in data.get("wires", []):
        if first not in entities or second not in entities:
            raise ValueError("A circuit wire references a missing entity.")
        a = entities[first]["position"]
        b = entities[second]["position"]
        maximum = max(
            maximum,
            math.hypot(a["x"] - b["x"], a["y"] - b["y"]),
        )
    return maximum


def validate_blueprint(
    blueprint: dict,
    maximum_wire: float = 9.0,
) -> None:
    data = blueprint.get("blueprint")
    if not isinstance(data, dict):
        raise ValueError("Missing blueprint object.")
    entities = data.get("entities")
    if not isinstance(entities, list) or not entities:
        raise ValueError("Generated blueprint has no entities.")

    ids = [entity["entity_number"] for entity in entities]
    if len(ids) != len(set(ids)):
        raise ValueError("Generated blueprint contains duplicate entity numbers.")

    distance = max_wire_distance(blueprint)
    if distance > maximum_wire + 1e-9:
        raise ValueError(
            f"Generated circuit wire is too long: {distance:.2f} tiles."
        )