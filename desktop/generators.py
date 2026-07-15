"""Factorio display and ticker blueprint architectures."""
from __future__ import annotations

import math
from dataclasses import replace

try:
    from .catalog import COMPAT_COLUMN_SIGNALS, FACTORIO_VERSION, LAMP_COLORS, MODE_LABELS, ROW_SIGNALS
    from .common import (
        add_clock, blueprint_book, build_pixel_timeline, chain, decode_blueprint, encode_blueprint,
        entity_footprint, lamp_entity, max_wire_distance, merged_font, nixie_signal_name,
        render_message_columns, render_static_canvas, signal_id, validate_blueprint, validate_config,
        visible_text_frame,
    )
    from .models import BlueprintBuilder, BlueprintResult, TickerConfig
except ImportError:
    from catalog import COMPAT_COLUMN_SIGNALS, FACTORIO_VERSION, LAMP_COLORS, MODE_LABELS, ROW_SIGNALS
    from common import (
        add_clock, blueprint_book, build_pixel_timeline, chain, decode_blueprint, encode_blueprint,
        entity_footprint, lamp_entity, max_wire_distance, merged_font, nixie_signal_name,
        render_message_columns, render_static_canvas, signal_id, validate_blueprint, validate_config,
        visible_text_frame,
    )
    from models import BlueprintBuilder, BlueprintResult, TickerConfig


def _lamp_positions(config: TickerConfig):
    for logical_column in range(config.display_width):
        for logical_row in range(config.display_height):
            for sy in range(config.pixel_height):
                for sx in range(config.pixel_width):
                    yield logical_column, logical_row, sx, sy


def _memory_geometry(config: TickerConfig, frames: int, segment_start: int, segment_width: int, decoder_y: float):
    screen_w = config.display_width * config.pixel_width
    screen_h = config.display_height * config.pixel_height
    if config.circuit_layout == "strip":
        columns = min(frames, max(1, frames))
    else:
        auto = max(1, min(max(1, segment_width * config.pixel_width), math.ceil(math.sqrt(frames))))
        columns = config.rom_columns or auto
        columns = max(1, min(columns, 60, frames))

    if config.circuit_layout in ("compact-square", "below", "strip"):
        origin_x = segment_start * config.pixel_width + 0.5
        origin_y = decoder_y + 4
        x_sign, y_sign = 1, 1
    elif config.circuit_layout == "above":
        origin_x = segment_start * config.pixel_width + 0.5
        origin_y = -6.5
        x_sign, y_sign = 1, -1
    elif config.circuit_layout == "left":
        origin_x = segment_start * config.pixel_width - 2.5
        origin_y = screen_h + 2.5
        x_sign, y_sign = -1, 1
    else:  # right
        origin_x = (segment_start + segment_width) * config.pixel_width + 2.5
        origin_y = screen_h + 2.5
        x_sign, y_sign = 1, 1
    return columns, origin_x, origin_y, x_sign, y_sign


def _decoder_y(config: TickerConfig) -> float:
    if config.circuit_layout == "above":
        return -2.5
    return config.display_height * config.pixel_height + 2.5


def _entity_position(builder: BlueprintBuilder, entity_number: int) -> tuple[float, float]:
    entity = builder.entities[entity_number - 1]
    return float(entity["position"]["x"]), float(entity["position"]["y"])


def _route_red_via_left(builder: BlueprintBuilder, first: int, first_connector: int, second: int, second_connector: int) -> None:
    """Route a long red circuit connection down a safe corridor left of the display."""
    ax, ay = _entity_position(builder, first)
    bx, by = _entity_position(builder, second)
    if math.hypot(ax - bx, ay - by) <= 8.5:
        builder.wire(first, first_connector, second, second_connector)
        return
    corridor_x = min(-1.5, ax - 1.0, bx - 1.0)
    points: list[int] = []
    # First horizontal/diagonal hop to the corridor at the first entity's height.
    current_x, current_y = ax, ay
    if math.hypot(current_x - corridor_x, 0) > 0.1:
        steps = max(1, math.ceil(abs(current_x - corridor_x) / 7.5))
        for step in range(1, steps + 1):
            x = current_x + (corridor_x - current_x) * step / steps
            points.append(builder.entity(name="small-electric-pole", position={"x": x, "y": ay}))
    distance_y = by - ay
    steps_y = max(1, math.ceil(abs(distance_y) / 7.5)) if abs(distance_y) > 0.1 else 0
    for step in range(1, steps_y + 1):
        y = ay + distance_y * step / steps_y
        points.append(builder.entity(name="small-electric-pole", position={"x": corridor_x, "y": y}))
    # Final horizontal hop toward the target.
    if math.hypot(corridor_x - bx, 0) > 0.1:
        steps = max(1, math.ceil(abs(corridor_x - bx) / 7.5))
        for step in range(1, steps):
            x = corridor_x + (bx - corridor_x) * step / steps
            points.append(builder.entity(name="small-electric-pole", position={"x": x, "y": by}))
    chain_ids = [first, *points, second]
    connectors = [first_connector, *([1] * len(points)), second_connector]
    for i in range(len(chain_ids) - 1):
        builder.wire(chain_ids[i], connectors[i], chain_ids[i + 1], connectors[i + 1])


def build_compact_lamps(config: TickerConfig, message: str) -> tuple[dict, list]:
    font = merged_font(config)
    stream = render_message_columns(
        message, config.character_spacing, config.repeat_gap, config.display_height,
        config.vertical_align, config.start_padding, config.end_padding, font,
    )
    timeline = build_pixel_timeline(stream, config)
    frames = len(timeline)
    width, height = config.display_width, config.display_height
    px, py = config.pixel_width, config.pixel_height
    color = LAMP_COLORS[config.lamp_color]
    builder = BlueprintBuilder()

    lamp_columns: list[list[int]] = []
    for logical_column in range(width):
        column_lamps: list[int] = []
        for logical_row in range(height):
            for sy in range(py):
                for sx in range(px):
                    column_lamps.append(lamp_entity(
                        builder,
                        logical_column * px + sx + 0.5,
                        logical_row * py + sy + 0.5,
                        ROW_SIGNALS[logical_row], color,
                    ))
        lamp_columns.append(column_lamps)

    decoder_y = _decoder_y(config)
    decoders: list[int] = []
    for logical_column in range(width):
        local_bit = logical_column % 30
        decoder = builder.entity(
            name="arithmetic-combinator",
            position={"x": logical_column * px + 0.5, "y": decoder_y},
            direction=0,
            control_behavior={"arithmetic_conditions": {
                "first_signal": signal_id("signal-each"),
                "first_signal_networks": {"red": True, "green": False},
                "operation": "AND", "second_constant": 1 << local_bit,
                "output_signal": signal_id("signal-each"),
            }},
        )
        decoders.append(decoder)
        lamps_for_column = lamp_columns[logical_column]
        lamp_anchor = lamps_for_column[0] if config.circuit_layout == "above" else lamps_for_column[-1]
        builder.wire(decoder, 3, lamp_anchor, 1)
        chain(builder, lamps_for_column, 1)

    clock_x = -6 if config.circuit_layout != "above" else -6
    _, _, clock_output = add_clock(
        builder, frames, config.ticks_per_step, clock_x, decoder_y,
        once=config.animation == "once",
    )
    builder.wire(clock_output, 4 if config.animation != "once" else 3, decoders[0], 2)
    chain(builder, decoders, 2)

    segment_count = math.ceil(width / 30)
    for segment in range(segment_count):
        segment_start = segment * 30
        segment_width = min(30, width - segment_start)
        block_columns, ox, oy, x_sign, y_sign = _memory_geometry(
            config, frames, segment_start, segment_width, decoder_y
        )
        memory_positions: list[tuple[int, int, int]] = []
        for frame, visible in enumerate(timeline):
            outputs = []
            for row, row_signal in enumerate(ROW_SIGNALS[:height]):
                mask = 0
                for local_column in range(segment_width):
                    if visible[segment_start + local_column][row]:
                        mask |= 1 << local_column
                outputs.append({
                    "signal": signal_id(row_signal), "copy_count_from_input": False, "constant": mask,
                })
            row_index, column_index = divmod(frame, block_columns)
            memory = builder.entity(
                name="decider-combinator",
                position={
                    "x": ox + x_sign * column_index,
                    "y": oy + y_sign * row_index * 2,
                },
                direction=0,
                control_behavior={"decider_conditions": {
                    "conditions": [{"first_signal": signal_id("signal-I"), "comparator": "=", "constant": frame}],
                    "outputs": outputs,
                }},
            )
            memory_positions.append((row_index, column_index, memory))

        snake: list[int] = []
        rows = math.ceil(frames / block_columns)
        for row_index in range(rows):
            row_items = [(column_index, entity) for row, column_index, entity in memory_positions if row == row_index]
            row_items.sort(reverse=bool(row_index % 2))
            snake.extend(entity for _, entity in row_items)
        chain(builder, snake, 3)
        chain(builder, snake, 2)

        if config.circuit_layout == "right":
            decoder_edge = decoders[segment_start + segment_width - 1]
        else:
            decoder_edge = decoders[segment_start]
        builder.wire(snake[0], 3, decoder_edge, 1)
        segment_decoders = decoders[segment_start:segment_start + segment_width]
        chain(builder, segment_decoders, 1)
        builder.wire(decoder_edge, 2, snake[0], 2)

    blueprint = {
        "blueprint": {
            "item": "blueprint",
            "label": f"{message} — Compact Lamp Display",
            "description": (
                f"Offline-generated {width}×{height} logical display, {px}×{py} lamps per pixel, "
                f"{config.animation} animation, {config.circuit_layout} circuit layout."
            ),
            "icons": [{"signal": {"type": "item", "name": "small-lamp"}, "index": 1}],
            "entities": builder.entities, "wires": builder.wires, "version": FACTORIO_VERSION,
        }
    }
    return blueprint, timeline


def build_compatible_lamps(config: TickerConfig, message: str) -> tuple[dict, list]:
    font = merged_font(config)
    stream = render_message_columns(
        message, config.character_spacing, config.repeat_gap, config.display_height,
        config.vertical_align, config.start_padding, config.end_padding, font,
    )
    timeline = build_pixel_timeline(stream, config)
    frames = len(timeline)
    width, height = config.display_width, config.display_height
    px, py = config.pixel_width, config.pixel_height
    color = LAMP_COLORS[config.lamp_color]
    builder = BlueprintBuilder()
    column_signals = COMPAT_COLUMN_SIGNALS[:width]

    lamp_rows: list[list[int]] = []
    for logical_row in range(height):
        row_lamps: list[int] = []
        for logical_column in range(width):
            for sy in range(py):
                for sx in range(px):
                    row_lamps.append(lamp_entity(
                        builder,
                        logical_column * px + sx + 0.5,
                        logical_row * py + sy + 0.5,
                        column_signals[logical_column], color,
                    ))
        lamp_rows.append(row_lamps)
        chain(builder, row_lamps, 1)

    clock_y = _decoder_y(config)
    _, _, clock_output = add_clock(
        builder, frames, config.ticks_per_step, -6, clock_y,
        once=config.animation == "once",
    )
    rom_y = (config.display_height * py + 1.5) if config.circuit_layout != "above" else -4.5
    rom: list[list[int]] = [[0] * height for _ in range(frames)]
    for frame, visible in enumerate(timeline):
        for row in range(height):
            outputs = [
                {"signal": signal_id(column_signals[column]), "copy_count_from_input": False, "constant": 1}
                for column in range(width) if visible[column][row]
            ] or [{"signal": signal_id("signal-check"), "copy_count_from_input": False, "constant": 0}]
            rom[frame][row] = builder.entity(
                name="decider-combinator",
                position={"x": row + 0.5, "y": rom_y + (-frame * 2 if config.circuit_layout == "above" else frame * 2)}, direction=0,
                control_behavior={"decider_conditions": {
                    "conditions": [{"first_signal": signal_id("signal-I"), "comparator": "=", "constant": frame}],
                    "outputs": outputs,
                }},
            )
    for frame in range(frames):
        chain(builder, rom[frame], 2)
    for frame in range(frames - 1):
        builder.wire(rom[frame][0], 2, rom[frame + 1][0], 2)
    builder.wire(clock_output, 4 if config.animation != "once" else 3, rom[0][0], 2)
    for row in range(height):
        _route_red_via_left(builder, rom[0][row], 3, lamp_rows[row][0], 1)
        for frame in range(frames - 1):
            builder.wire(rom[frame][row], 3, rom[frame + 1][row], 3)

    blueprint = {"blueprint": {
        "item": "blueprint", "label": f"{message} — Compatibility Lamp Display",
        "description": f"Offline-generated {width}×{height} compatibility lamp display.",
        "icons": [{"signal": {"type": "item", "name": "small-lamp"}, "index": 1}],
        "entities": builder.entities, "wires": builder.wires, "version": FACTORIO_VERSION,
    }}
    return blueprint, timeline


def build_static_lamps(config: TickerConfig, message: str) -> tuple[dict, list]:
    canvas = render_static_canvas(message, config)
    builder = BlueprintBuilder()
    color = LAMP_COLORS[config.lamp_color]
    source = builder.entity(
        name="constant-combinator", position={"x": -2.5, "y": 0.5},
        control_behavior={"sections": {"sections": [{"index": 1, "filters": [{
            "index": 1, "type": "virtual", "name": "signal-A", "quality": "normal",
            "comparator": "=", "count": 1,
        }]}]}},
    )
    physical_rows: list[list[int]] = [[] for _ in range(config.display_height * config.pixel_height)]
    for logical_row in range(config.display_height):
        for logical_column in range(config.display_width):
            lit = bool(canvas[logical_row][logical_column])
            for sy in range(config.pixel_height):
                for sx in range(config.pixel_width):
                    lamp = builder.entity(
                        name="small-lamp",
                        position={
                            "x": logical_column * config.pixel_width + sx + 0.5,
                            "y": logical_row * config.pixel_height + sy + 0.5,
                        },
                        color=dict(color), always_on=True,
                        control_behavior={
                            "circuit_enabled": True, "use_colors": False,
                            "circuit_condition": {
                                "first_signal": signal_id("signal-A"),
                                "comparator": ">" if lit else "<", "constant": 0,
                            },
                        },
                    )
                    physical_rows[logical_row * config.pixel_height + sy].append(lamp)
    snake: list[int] = []
    for row_index, row in enumerate(physical_rows):
        snake.extend(reversed(row) if row_index % 2 else row)
    chain(builder, snake, 1)
    builder.wire(source, 1, snake[0], 1)
    preview = [[tuple(canvas[y][x] for y in range(config.display_height)) for x in range(config.display_width)]]
    blueprint = {"blueprint": {
        "item": "blueprint", "label": f"{message.splitlines()[0]} — Static Lamp Sign",
        "description": (
            f"Offline-generated static {config.display_width}×{config.display_height} logical lamp sign, "
            f"{config.pixel_width}×{config.pixel_height} lamps per pixel."
        ),
        "icons": [{"signal": {"type": "item", "name": "small-lamp"}, "index": 1}],
        "entities": builder.entities, "wires": builder.wires, "version": FACTORIO_VERSION,
    }}
    return blueprint, preview


def _nixie_frames(config: TickerConfig, message: str) -> list[str]:
    ring = (" " * config.nixie_edge_spaces) + message + (" " * config.nixie_edge_spaces)
    ring = ring or " "
    frames = [visible_text_frame(ring, frame, config.display_width, config.direction) for frame in range(len(ring))]
    if config.animation == "bounce" and len(frames) > 2:
        frames = frames + frames[-2:0:-1]
    if config.full_message_pause_steps and len(message) <= config.display_width:
        left = max(0, (config.display_width - len(message)) // 2)
        held = (" " * left + message).ljust(config.display_width)
        frames = [held] * config.full_message_pause_steps + frames
    if config.pause_steps:
        frames.extend([frames[-1]] * config.pause_steps)
    return frames


def build_nixie(config: TickerConfig, message: str) -> tuple[dict, list]:
    frames_data = _nixie_frames(config, message)
    frames = len(frames_data)
    width = config.display_width
    builder = BlueprintBuilder()
    tubes = [builder.entity(name="nixie-tube-alpha", position={"x": column + 0.5, "y": 0}, always_on=True) for column in range(width)]
    _, _, clock_output = add_clock(builder, frames, config.ticks_per_step, 0, 2.5, once=config.animation == "once")
    matrix: list[list[int]] = [[0] * width for _ in range(frames)]
    for frame, displayed in enumerate(frames_data):
        for column, character in enumerate(displayed):
            blank = character == " "
            matrix[frame][column] = builder.entity(
                name="decider-combinator", position={"x": column + 0.5, "y": 5.5 + frame * 2}, direction=0,
                control_behavior={"decider_conditions": {
                    "conditions": [{"first_signal": signal_id("signal-I"), "comparator": "=", "constant": -1 if blank else frame}],
                    "outputs": [{
                        "signal": signal_id("signal-A" if blank else nixie_signal_name(character)),
                        "copy_count_from_input": False, "constant": 1,
                    }],
                }},
            )
    for frame in range(frames):
        chain(builder, matrix[frame], 2)
    for frame in range(frames - 1):
        builder.wire(matrix[frame][0], 2, matrix[frame + 1][0], 2)
    builder.wire(clock_output, 4 if config.animation != "once" else 3, matrix[0][0], 2)
    for column in range(width):
        builder.wire(tubes[column], 1, matrix[0][column], 3)
        for frame in range(frames - 1):
            builder.wire(matrix[frame][column], 3, matrix[frame + 1][column], 3)
    blueprint = {"blueprint": {
        "item": "blueprint", "label": f"{message} — Nixie Ticker",
        "description": f"Offline-generated {width}-cell alpha Nixie ticker. Requires nixie-tubes.",
        "icons": [{"signal": {"type": "item", "name": "nixie-tube-alpha"}, "index": 1}],
        "entities": builder.entities, "wires": builder.wires, "version": FACTORIO_VERSION,
    }}
    return blueprint, frames_data


def build_static_nixie(config: TickerConfig, message: str) -> tuple[dict, list]:
    width = config.display_width
    if config.horizontal_align == "left":
        text = message[:width].ljust(width)
    elif config.horizontal_align == "right":
        text = message[-width:].rjust(width)
    else:
        clipped = message[:width]
        left = max(0, (width - len(clipped)) // 2)
        text = (" " * left + clipped).ljust(width)
    builder = BlueprintBuilder()
    for column, character in enumerate(text):
        tube = builder.entity(name="nixie-tube-alpha", position={"x": column + 0.5, "y": 0}, always_on=True)
        if character != " ":
            source = builder.entity(
                name="constant-combinator", position={"x": column + 0.5, "y": 2},
                control_behavior={"sections": {"sections": [{"index": 1, "filters": [{
                    "index": 1, "type": "virtual", "name": nixie_signal_name(character),
                    "quality": "normal", "comparator": "=", "count": 1,
                }]}]}},
            )
            builder.wire(source, 1, tube, 1)
    blueprint = {"blueprint": {
        "item": "blueprint", "label": f"{message} — Static Nixie Sign",
        "description": "Offline-generated static alpha Nixie sign. Requires nixie-tubes.",
        "icons": [{"signal": {"type": "item", "name": "nixie-tube-alpha"}, "index": 1}],
        "entities": builder.entities, "wires": builder.wires, "version": FACTORIO_VERSION,
    }}
    return blueprint, [text]


def _warnings(config: TickerConfig, stats: dict[str, int | float | str]) -> list[str]:
    warnings: list[str] = []
    entities = int(stats["entities"])
    bp_chars = int(stats["blueprint_characters"])
    if entities >= 10000:
        warnings.append("Very large blueprint: more than 10,000 entities. Importing and placing it may be slow.")
    elif entities >= 3000:
        warnings.append("Large blueprint: more than 3,000 entities.")
    if bp_chars >= 1_000_000:
        warnings.append("Blueprint string exceeds one million characters.")
    physical_w = config.display_width * (config.pixel_width if config.mode.startswith("lamp-") else 1)
    physical_h = config.display_height * config.pixel_height if config.mode.startswith("lamp-") else 1
    if physical_w * physical_h >= 5000:
        warnings.append("The physical display contains at least 5,000 lamp positions.")
    return warnings


def generate(config: TickerConfig) -> BlueprintResult:
    message = validate_config(config)
    if config.mode == "lamp-compact":
        blueprint, previews = build_compact_lamps(config, message)
    elif config.mode == "lamp-compatible":
        blueprint, previews = build_compatible_lamps(config, message)
    elif config.mode == "lamp-static":
        blueprint, previews = build_static_lamps(config, message)
    elif config.mode == "nixie-static":
        blueprint, previews = build_static_nixie(config, message)
    else:
        blueprint, previews = build_nixie(config, message)

    validate_blueprint(blueprint)
    encoded = encode_blueprint(blueprint)
    if decode_blueprint(encoded) != blueprint:
        raise RuntimeError("Blueprint encoding round-trip failed.")
    entities = blueprint["blueprint"]["entities"]
    names: dict[str, int] = {}
    for entity in entities:
        names[entity["name"]] = names.get(entity["name"], 0) + 1
    footprint_w, footprint_h = entity_footprint(blueprint)
    stats: dict[str, int | float | str] = {
        "mode": MODE_LABELS[config.mode], "entities": len(entities),
        "wires": len(blueprint["blueprint"].get("wires", [])),
        "lamps": names.get("small-lamp", 0), "nixie_tubes": names.get("nixie-tube-alpha", 0),
        "deciders": names.get("decider-combinator", 0), "arithmetic": names.get("arithmetic-combinator", 0),
        "constants": names.get("constant-combinator", 0), "frames": len(previews),
        "blueprint_characters": len(encoded), "max_wire_distance": round(max_wire_distance(blueprint), 2),
        "footprint_width": footprint_w, "footprint_height": footprint_h,
        "display_lamps_wide": config.display_width * config.pixel_width if config.mode.startswith("lamp-") else config.display_width,
        "display_lamps_high": config.display_height * config.pixel_height if config.mode.startswith("lamp-") else 1,
    }
    return BlueprintResult(
        blueprint=blueprint, blueprint_string=encoded, stats=stats, normalized_message=message,
        preview_frames=previews, warnings=_warnings(config, stats),
    )


def generate_blueprint_book(config: TickerConfig) -> tuple[dict, str]:
    """Generate a useful variant book for the current message/configuration."""
    configs: list[TickerConfig] = []
    if config.mode.startswith("lamp-"):
        configs.append(replace(config, mode="lamp-static", animation="static"))
        configs.append(replace(config, mode="lamp-compact", animation="loop" if config.animation == "static" else config.animation))
        if config.display_width <= 36:
            configs.append(replace(config, mode="lamp-compatible", animation="loop" if config.animation == "static" else config.animation))
    else:
        configs.append(replace(config, mode="nixie-static", animation="static"))
        configs.append(replace(config, mode="nixie", animation="loop" if config.animation == "static" else config.animation))
    blueprints = [generate(item).blueprint for item in configs]
    book = blueprint_book(blueprints, f"{normalize_label(config.message)} — Display Variants")
    return book, encode_blueprint(book)


def normalize_label(message: str) -> str:
    return " ".join(message.split())[:80] or "Display"
