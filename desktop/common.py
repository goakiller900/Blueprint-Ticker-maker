"""Shared validation, rendering, encoding, timeline, and circuit helpers."""
from __future__ import annotations

import base64
from dataclasses import asdict
import json
import math
import re
import zlib
from typing import Iterable

try:
    from .catalog import FONT_5X7, LAMP_COLORS, MODE_LABELS, NIXIE_SIGNAL_NAMES, ROW_SIGNALS
    from .models import BlueprintBuilder, Direction, TickerConfig
except ImportError:
    from catalog import FONT_5X7, LAMP_COLORS, MODE_LABELS, NIXIE_SIGNAL_NAMES, ROW_SIGNALS
    from models import BlueprintBuilder, Direction, TickerConfig


def merged_font(config: TickerConfig) -> dict[str, tuple[str, ...]]:
    font = dict(FONT_5X7)
    for raw_character, raw_rows in config.custom_font.items():
        character = str(raw_character).upper()[:1]
        rows = tuple(str(row) for row in raw_rows)
        if len(rows) != 7 or any(len(row) != 5 or set(row) - {"0", "1"} for row in rows):
            raise ValueError(f"Custom glyph {character!r} must be exactly 5×7 binary pixels.")
        if character:
            font[character] = rows
    return font


def normalize_message(raw: str, mode: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").upper()
    if mode == "lamp-static":
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.split("\n")]
        message = "\n".join(lines).strip("\n")
    else:
        message = re.sub(r"\s+", " ", raw).strip()
    if not message:
        raise ValueError("Enter a message.")
    return message


def validate_config(config: TickerConfig) -> str:
    if config.mode not in MODE_LABELS:
        raise ValueError("Unknown output mode.")
    if config.direction not in ("left", "right"):
        raise ValueError("Direction must be left or right.")
    if config.animation not in ("loop", "once", "bounce", "static"):
        raise ValueError("Unknown animation mode.")
    if not (1 / 60 <= config.seconds_per_step <= 60):
        raise ValueError("Seconds per step must be between 1/60 and 60.")
    if not (0 <= config.pause_seconds <= 120) or not (0 <= config.full_message_pause_seconds <= 120):
        raise ValueError("Pause durations must be between 0 and 120 seconds.")
    if config.character_spacing not in range(0, 11):
        raise ValueError("Character spacing must be from 0 through 10.")
    if config.repeat_gap not in range(0, 121):
        raise ValueError("Repeat gap must be from 0 through 120.")
    if config.start_padding not in range(0, 301) or config.end_padding not in range(0, 301):
        raise ValueError("Start/end padding must be from 0 through 300 columns.")
    if config.pixel_width not in range(1, 9) or config.pixel_height not in range(1, 9):
        raise ValueError("Pixel width and height must be from 1 through 8 lamps.")
    if config.display_width not in range(1, 151):
        raise ValueError("Display width must be from 1 through 150 logical pixels/cells.")
    if config.display_height not in range(1, 31):
        raise ValueError("Lamp display height must be from 1 through 30 logical rows.")
    if config.mode == "lamp-compatible" and config.display_width > 36:
        raise ValueError("Compatibility lamp width is limited to 36 logical columns.")
    if config.mode.startswith("lamp-") and config.display_height > len(ROW_SIGNALS) and config.mode == "lamp-compact":
        raise ValueError(f"Compact lamp height is limited to {len(ROW_SIGNALS)} logical rows.")
    if config.lamp_color not in LAMP_COLORS:
        raise ValueError("Unknown lamp colour.")
    if config.rom_columns not in range(0, 61):
        raise ValueError("ROM columns must be automatic (0) or 1 through 60.")
    if config.nixie_edge_spaces not in range(0, 51):
        raise ValueError("Nixie edge spaces must be from 0 through 50.")
    if config.line_spacing not in range(0, 11):
        raise ValueError("Line spacing must be from 0 through 10.")

    message = normalize_message(config.message, config.mode)
    font = merged_font(config)
    for character in message:
        if character == "\n" and config.mode == "lamp-static":
            continue
        if config.mode.startswith("nixie"):
            if character == " ":
                continue
            if character.isascii() and (character.isalpha() or character.isdigit()):
                continue
            if character in NIXIE_SIGNAL_NAMES:
                continue
            raise ValueError(f"Nixie mode does not support {character!r}.")
        if character not in font:
            raise ValueError(f"Lamp font does not support {character!r}. Add it in the font editor.")
    return message


def signal_id(name: str) -> dict[str, str]:
    return {"type": "virtual", "name": name}


def nixie_signal_name(character: str) -> str:
    if character.isascii() and (character.isalpha() or character.isdigit()):
        return f"signal-{character}"
    result = NIXIE_SIGNAL_NAMES.get(character)
    if result is None:
        raise ValueError(f"No Nixie signal mapping for {character!r}.")
    return result


def fit_glyph_rows(glyph: tuple[str, ...], height: int, align: str) -> tuple[str, ...]:
    if height == len(glyph):
        return glyph
    if height < len(glyph):
        missing = len(glyph) - height
        if align == "top":
            start = 0
        elif align == "bottom":
            start = missing
        else:
            start = missing // 2
        return glyph[start:start + height]
    extra = height - len(glyph)
    if align == "top":
        top = 0
    elif align == "bottom":
        top = extra
    else:
        top = extra // 2
    bottom = extra - top
    blank = "0" * 5
    return (blank,) * top + glyph + (blank,) * bottom


def render_message_columns(
    message: str,
    character_spacing: int,
    repeat_gap: int,
    height: int = 7,
    vertical_align: str = "middle",
    start_padding: int = 0,
    end_padding: int = 0,
    font: dict[str, tuple[str, ...]] | None = None,
) -> list[tuple[int, ...]]:
    font = font or FONT_5X7
    columns: list[tuple[int, ...]] = [(0,) * height for _ in range(start_padding)]
    for index, character in enumerate(message):
        glyph = fit_glyph_rows(font[character], height, vertical_align)
        for x in range(5):
            columns.append(tuple(int(glyph[y][x]) for y in range(height)))
        if index != len(message) - 1:
            columns.extend([(0,) * height] * character_spacing)
    columns.extend([(0,) * height] * end_padding)
    columns.extend([(0,) * height] * repeat_gap)
    return columns or [(0,) * height]


def visible_pixel_frame(stream: list[tuple[int, ...]], frame: int, width: int, direction: Direction) -> list[tuple[int, ...]]:
    offset = frame if direction == "left" else -frame
    return [stream[(offset + column) % len(stream)] for column in range(width)]


def visible_text_frame(ring: str, frame: int, width: int, direction: Direction) -> str:
    offset = frame if direction == "left" else -frame
    return "".join(ring[(offset + column) % len(ring)] for column in range(width))


def center_frame(stream: list[tuple[int, ...]], width: int) -> list[tuple[int, ...]]:
    height = len(stream[0]) if stream else 7
    content = list(stream)
    while content and not any(content[0]):
        content.pop(0)
    while content and not any(content[-1]):
        content.pop()
    if len(content) > width:
        return content[:width]
    left = max(0, (width - len(content)) // 2)
    right = max(0, width - len(content) - left)
    return [(0,) * height] * left + content + [(0,) * height] * right


def build_pixel_timeline(stream: list[tuple[int, ...]], config: TickerConfig) -> list[list[tuple[int, ...]]]:
    base = [visible_pixel_frame(stream, frame, config.display_width, config.direction) for frame in range(len(stream))]
    if config.animation == "static" or config.mode == "lamp-static":
        return [center_frame(stream, config.display_width)]
    if config.animation == "bounce" and len(base) > 2:
        base = base + base[-2:0:-1]
    if config.full_message_pause_steps and len(stream) <= config.display_width:
        held = center_frame(stream, config.display_width)
        base = [held] * config.full_message_pause_steps + base
    if config.pause_steps:
        base.extend([base[-1]] * config.pause_steps)
    return base or [[(0,) * config.display_height] * config.display_width]


def render_static_canvas(message: str, config: TickerConfig) -> list[list[int]]:
    """Render multiline 5×7 text into a fixed logical lamp canvas."""
    font = merged_font(config)
    lines = message.split("\n")
    line_bitmaps: list[list[list[int]]] = []
    for line in lines:
        cols = render_message_columns(line or " ", config.character_spacing, 0, 7, "top", 0, 0, font)
        bitmap = [[cols[x][y] for x in range(len(cols))] for y in range(7)]
        line_bitmaps.append(bitmap)

    content_height = len(line_bitmaps) * 7 + max(0, len(line_bitmaps) - 1) * config.line_spacing
    if config.vertical_align == "top":
        y0 = 0
    elif config.vertical_align == "bottom":
        y0 = config.display_height - content_height
    else:
        y0 = (config.display_height - content_height) // 2

    canvas = [[0 for _ in range(config.display_width)] for _ in range(config.display_height)]
    current_y = y0
    for bitmap in line_bitmaps:
        line_width = len(bitmap[0]) if bitmap else 0
        if config.horizontal_align == "left":
            x0 = 0
        elif config.horizontal_align == "right":
            x0 = config.display_width - line_width
        else:
            x0 = (config.display_width - line_width) // 2
        for y, row in enumerate(bitmap):
            target_y = current_y + y
            if not (0 <= target_y < config.display_height):
                continue
            for x, value in enumerate(row):
                target_x = x0 + x
                if 0 <= target_x < config.display_width:
                    canvas[target_y][target_x] = value
        current_y += 7 + config.line_spacing
    return canvas


def add_clock(builder: BlueprintBuilder, frames: int, ticks: int, x: float, y: float, once: bool = False) -> tuple[int, int, int]:
    counter = builder.entity(
        name="arithmetic-combinator", position={"x": x, "y": y}, direction=4,
        control_behavior={"arithmetic_conditions": {
            "first_signal": signal_id("signal-T"), "operation": "+", "second_constant": 1,
            "output_signal": signal_id("signal-T"),
        }},
    )
    divider = builder.entity(
        name="arithmetic-combinator", position={"x": x + 2, "y": y}, direction=4,
        control_behavior={"arithmetic_conditions": {
            "first_signal": signal_id("signal-T"), "operation": "/", "second_constant": ticks,
            "output_signal": signal_id("signal-I"),
        }},
    )
    builder.wire(counter, 3, counter, 1)
    builder.wire(counter, 4, divider, 2)
    if not once:
        modulo = builder.entity(
            name="arithmetic-combinator", position={"x": x + 4, "y": y}, direction=4,
            control_behavior={"arithmetic_conditions": {
                "first_signal": signal_id("signal-I"), "operation": "%", "second_constant": max(1, frames),
                "output_signal": signal_id("signal-I"),
            }},
        )
        builder.wire(divider, 4, modulo, 2)
        return counter, divider, modulo

    pass_through = builder.entity(
        name="decider-combinator", position={"x": x + 4, "y": y}, direction=4,
        control_behavior={"decider_conditions": {
            "conditions": [{"first_signal": signal_id("signal-I"), "comparator": "<", "constant": max(1, frames)}],
            "outputs": [{"signal": signal_id("signal-I"), "copy_count_from_input": True}],
        }},
    )
    clamp = builder.entity(
        name="decider-combinator", position={"x": x + 6, "y": y}, direction=4,
        control_behavior={"decider_conditions": {
            "conditions": [{"first_signal": signal_id("signal-I"), "comparator": "≥", "constant": max(1, frames)}],
            "outputs": [{"signal": signal_id("signal-I"), "copy_count_from_input": False, "constant": max(0, frames - 1)}],
        }},
    )
    builder.wire(divider, 4, pass_through, 2)
    builder.wire(divider, 4, clamp, 2)
    builder.wire(pass_through, 3, clamp, 3)
    return counter, divider, pass_through


def lamp_entity(builder: BlueprintBuilder, x: float, y: float, signal: str | None, color: dict[str, float], lit: bool | None = None) -> int:
    entity: dict = {
        "name": "small-lamp", "position": {"x": x, "y": y}, "color": dict(color),
    }
    if lit is not None:
        entity["always_on"] = bool(lit)
    elif signal is not None:
        entity["always_on"] = True
        entity["control_behavior"] = {
            "circuit_enabled": True,
            "use_colors": False,
            "circuit_condition": {"first_signal": signal_id(signal), "comparator": ">", "constant": 0},
        }
    return builder.entity(**entity)


def chain(builder: BlueprintBuilder, entities: Iterable[int], connector: int) -> None:
    items = list(entities)
    for first, second in zip(items, items[1:]):
        builder.wire(first, connector, second, connector)


def encode_blueprint(blueprint: dict) -> str:
    raw = json.dumps(blueprint, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "0" + base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def decode_blueprint(blueprint_string: str) -> dict:
    text = blueprint_string.strip()
    if not text.startswith("0"):
        raise ValueError("Factorio blueprint strings must start with 0.")
    return json.loads(zlib.decompress(base64.b64decode(text[1:])))


def blueprint_book(blueprints: list[dict], label: str) -> dict:
    entries = []
    for index, blueprint in enumerate(blueprints):
        entries.append({"index": index, "blueprint": blueprint["blueprint"]})
    version = blueprints[0]["blueprint"]["version"] if blueprints else 562954249109505
    return {"blueprint_book": {"item": "blueprint-book", "label": label, "active_index": 0, "blueprints": entries, "version": version}}


def max_wire_distance(blueprint: dict) -> float:
    data = blueprint.get("blueprint") or {}
    entities = {entity["entity_number"]: entity for entity in data.get("entities", [])}
    maximum = 0.0
    for first, _, second, _ in data.get("wires", []):
        if first not in entities or second not in entities:
            raise ValueError("A circuit wire references a missing entity.")
        a = entities[first]["position"]
        b = entities[second]["position"]
        maximum = max(maximum, math.hypot(a["x"] - b["x"], a["y"] - b["y"]))
    return maximum


def entity_footprint(blueprint: dict) -> tuple[float, float]:
    entities = blueprint.get("blueprint", {}).get("entities", [])
    if not entities:
        return 0.0, 0.0
    xs = [float(e["position"]["x"]) for e in entities]
    ys = [float(e["position"]["y"]) for e in entities]
    return round(max(xs) - min(xs) + 1, 1), round(max(ys) - min(ys) + 1, 1)


def validate_blueprint(blueprint: dict, maximum_wire: float = 9.0) -> None:
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
        raise ValueError(f"Generated circuit wire is too long: {distance:.2f} tiles.")


def config_as_json(config: TickerConfig) -> str:
    return json.dumps(asdict(config), indent=2, ensure_ascii=False)
