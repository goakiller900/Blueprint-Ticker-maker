"""Factorio ticker blueprint architectures."""

from __future__ import annotations

import math

try:
    from .catalog import (
        COMPAT_COLUMN_SIGNALS,
        FACTORIO_VERSION,
        LAMP_COLORS,
        MODE_LABELS,
        ROW_SIGNALS,
    )
    from .common import (
        add_clock,
        chain,
        decode_blueprint,
        encode_blueprint,
        lamp_entity,
        max_wire_distance,
        nixie_signal_name,
        render_message_columns,
        signal_id,
        validate_blueprint,
        validate_config,
        visible_pixel_frame,
        visible_text_frame,
    )
    from .models import BlueprintBuilder, BlueprintResult, TickerConfig
except ImportError:
    from catalog import (
        COMPAT_COLUMN_SIGNALS,
        FACTORIO_VERSION,
        LAMP_COLORS,
        MODE_LABELS,
        ROW_SIGNALS,
    )
    from common import (
        add_clock,
        chain,
        decode_blueprint,
        encode_blueprint,
        lamp_entity,
        max_wire_distance,
        nixie_signal_name,
        render_message_columns,
        signal_id,
        validate_blueprint,
        validate_config,
        visible_pixel_frame,
        visible_text_frame,
    )
    from models import BlueprintBuilder, BlueprintResult, TickerConfig


def build_compact_lamps(
    config: TickerConfig,
    message: str,
) -> tuple[dict, list]:
    stream = render_message_columns(
        message,
        config.character_spacing,
        config.repeat_gap,
    )
    frames = len(stream)
    width = config.display_width
    scale = config.pixel_scale
    color = LAMP_COLORS[config.lamp_color]
    builder = BlueprintBuilder()

    lamp_columns: list[list[int]] = []
    for logical_column in range(width):
        column_lamps: list[int] = []
        for logical_row in range(7):
            for sy in range(scale):
                for sx in range(scale):
                    column_lamps.append(
                        lamp_entity(
                            builder,
                            logical_column * scale + sx + 0.5,
                            logical_row * scale + sy + 0.5,
                            ROW_SIGNALS[logical_row],
                            color,
                        )
                    )
        lamp_columns.append(column_lamps)

    screen_height = 7 * scale
    decoder_y = screen_height + 2.5

    decoders: list[int] = []
    for logical_column in range(width):
        local_bit = logical_column % 30
        decoder = builder.entity(
            name="arithmetic-combinator",
            position={
                "x": logical_column * scale + 0.5,
                "y": decoder_y,
            },
            direction=0,
            control_behavior={
                "arithmetic_conditions": {
                    "first_signal": signal_id("signal-each"),
                    "first_signal_networks": {
                        "red": True,
                        "green": False,
                    },
                    "operation": "AND",
                    "second_constant": 1 << local_bit,
                    "output_signal": signal_id("signal-each"),
                }
            },
        )
        decoders.append(decoder)
        builder.wire(
            decoder,
            3,
            lamp_columns[logical_column][-1],
            1,
        )
        chain(builder, lamp_columns[logical_column], 1)

    _, _, modulo = add_clock(
        builder,
        frames,
        config.ticks_per_step,
        -6,
        decoder_y,
    )

    builder.wire(modulo, 4, decoders[0], 2)
    for first, second in zip(decoders, decoders[1:]):
        builder.wire(first, 2, second, 2)

    segment_count = math.ceil(width / 30)
    memory_y = decoder_y + 4

    for segment in range(segment_count):
        segment_start = segment * 30
        segment_width = min(30, width - segment_start)
        auto_columns = max(
            1,
            min(
                segment_width * scale,
                math.ceil(math.sqrt(frames)),
            ),
        )
        block_columns = config.rom_columns or auto_columns
        block_columns = max(
            1,
            min(
                block_columns,
                30,
                max(1, segment_width * scale),
            ),
        )

        memory_positions: list[tuple[int, int, int]] = []
        for frame in range(frames):
            visible = visible_pixel_frame(
                stream,
                frame,
                width,
                config.direction,
            )
            outputs = []
            for row, row_signal in enumerate(ROW_SIGNALS):
                mask = 0
                for local_column in range(segment_width):
                    if visible[segment_start + local_column][row]:
                        mask |= 1 << local_column
                outputs.append(
                    {
                        "signal": signal_id(row_signal),
                        "copy_count_from_input": False,
                        "constant": mask,
                    }
                )

            row_index, column_index = divmod(
                frame,
                block_columns,
            )
            memory = builder.entity(
                name="decider-combinator",
                position={
                    "x": (
                        segment_start * scale
                        + column_index
                        + 0.5
                    ),
                    "y": memory_y + row_index * 2,
                },
                direction=0,
                control_behavior={
                    "decider_conditions": {
                        "conditions": [
                            {
                                "first_signal": signal_id("signal-I"),
                                "comparator": "=",
                                "constant": frame,
                            }
                        ],
                        "outputs": outputs,
                    }
                },
            )
            memory_positions.append(
                (row_index, column_index, memory)
            )

        snake: list[int] = []
        rows = math.ceil(frames / block_columns)
        for row_index in range(rows):
            row_items = [
                (column_index, entity)
                for row, column_index, entity in memory_positions
                if row == row_index
            ]
            row_items.sort(reverse=bool(row_index % 2))
            snake.extend(entity for _, entity in row_items)

        chain(builder, snake, 3)
        builder.wire(
            snake[0],
            3,
            decoders[segment_start],
            1,
        )
        segment_decoders = decoders[
            segment_start : segment_start + segment_width
        ]
        for first, second in zip(
            segment_decoders,
            segment_decoders[1:],
        ):
            builder.wire(first, 1, second, 1)

        builder.wire(
            decoders[segment_start],
            2,
            snake[0],
            2,
        )
        chain(builder, snake, 2)

    blueprint = {
        "blueprint": {
            "item": "blueprint",
            "label": f"{message} — Compact Lamp Ticker",
            "description": (
                f"Offline-generated {width}×7 compact vanilla "
                f"lamp ticker. One pixel-column step every "
                f"{config.ticks_per_step} ticks."
            ),
            "icons": [
                {
                    "signal": {
                        "type": "item",
                        "name": "small-lamp",
                    },
                    "index": 1,
                }
            ],
            "entities": builder.entities,
            "wires": builder.wires,
            "version": FACTORIO_VERSION,
        }
    }
    previews = [
        visible_pixel_frame(
            stream,
            frame,
            width,
            config.direction,
        )
        for frame in range(frames)
    ]
    return blueprint, previews


def build_compatible_lamps(
    config: TickerConfig,
    message: str,
) -> tuple[dict, list]:
    stream = render_message_columns(
        message,
        config.character_spacing,
        config.repeat_gap,
    )
    frames = len(stream)
    width = config.display_width
    scale = config.pixel_scale
    color = LAMP_COLORS[config.lamp_color]
    builder = BlueprintBuilder()
    column_signals = COMPAT_COLUMN_SIGNALS[:width]

    lamp_rows: list[list[int]] = []
    for logical_row in range(7):
        row_lamps: list[int] = []
        for logical_column in range(width):
            for sy in range(scale):
                for sx in range(scale):
                    row_lamps.append(
                        lamp_entity(
                            builder,
                            logical_column * scale + sx + 0.5,
                            logical_row * scale + sy + 0.5,
                            column_signals[logical_column],
                            color,
                        )
                    )
        lamp_rows.append(row_lamps)
        chain(builder, row_lamps, 1)

    screen_height = 7 * scale
    clock_y = screen_height + 1.5
    _, _, modulo = add_clock(
        builder,
        frames,
        config.ticks_per_step,
        -6,
        clock_y,
    )

    rom_y = screen_height + 1.5
    rom: list[list[int]] = [[0] * 7 for _ in range(frames)]

    for frame in range(frames):
        visible = visible_pixel_frame(
            stream,
            frame,
            width,
            config.direction,
        )
        for row in range(7):
            outputs = [
                {
                    "signal": signal_id(
                        column_signals[column]
                    ),
                    "copy_count_from_input": False,
                    "constant": 1,
                }
                for column in range(width)
                if visible[column][row]
            ]
            if not outputs:
                outputs = [
                    {
                        "signal": signal_id("signal-check"),
                        "copy_count_from_input": False,
                        "constant": 0,
                    }
                ]

            rom[frame][row] = builder.entity(
                name="decider-combinator",
                position={
                    "x": row + 0.5,
                    "y": rom_y + frame * 2,
                },
                direction=0,
                control_behavior={
                    "decider_conditions": {
                        "conditions": [
                            {
                                "first_signal": signal_id("signal-I"),
                                "comparator": "=",
                                "constant": frame,
                            }
                        ],
                        "outputs": outputs,
                    }
                },
            )

    for frame in range(frames):
        for row in range(6):
            builder.wire(
                rom[frame][row],
                2,
                rom[frame][row + 1],
                2,
            )
    for frame in range(frames - 1):
        builder.wire(
            rom[frame][0],
            2,
            rom[frame + 1][0],
            2,
        )
    builder.wire(modulo, 4, rom[0][0], 2)

    for row in range(7):
        builder.wire(
            rom[0][row],
            3,
            lamp_rows[row][0],
            1,
        )
        for frame in range(frames - 1):
            builder.wire(
                rom[frame][row],
                3,
                rom[frame + 1][row],
                3,
            )

    blueprint = {
        "blueprint": {
            "item": "blueprint",
            "label": (
                f"{message} — Compatibility Lamp Ticker"
            ),
            "description": (
                f"Offline-generated {width}×7 compatibility "
                f"lamp ticker. One pixel-column step every "
                f"{config.ticks_per_step} ticks."
            ),
            "icons": [
                {
                    "signal": {
                        "type": "item",
                        "name": "small-lamp",
                    },
                    "index": 1,
                }
            ],
            "entities": builder.entities,
            "wires": builder.wires,
            "version": FACTORIO_VERSION,
        }
    }
    previews = [
        visible_pixel_frame(
            stream,
            frame,
            width,
            config.direction,
        )
        for frame in range(frames)
    ]
    return blueprint, previews


def build_nixie(
    config: TickerConfig,
    message: str,
) -> tuple[dict, list]:
    ring = (
        (" " * config.nixie_edge_spaces)
        + message
        + (" " * config.nixie_edge_spaces)
    )
    ring = ring or " "
    frames = len(ring)
    width = config.display_width
    builder = BlueprintBuilder()

    tubes = [
        builder.entity(
            name="nixie-tube-alpha",
            position={"x": column + 0.5, "y": 0},
            always_on=True,
        )
        for column in range(width)
    ]

    _, _, modulo = add_clock(
        builder,
        frames,
        config.ticks_per_step,
        0,
        2.5,
    )
    matrix: list[list[int]] = [
        [0] * width
        for _ in range(frames)
    ]
    previews: list[str] = []

    for frame in range(frames):
        displayed = visible_text_frame(
            ring,
            frame,
            width,
            config.direction,
        )
        previews.append(displayed)
        for column, character in enumerate(displayed):
            blank = character == " "
            matrix[frame][column] = builder.entity(
                name="decider-combinator",
                position={
                    "x": column + 0.5,
                    "y": 5.5 + frame * 2,
                },
                direction=0,
                control_behavior={
                    "decider_conditions": {
                        "conditions": [
                            {
                                "first_signal": signal_id("signal-I"),
                                "comparator": "=",
                                "constant": (
                                    -1
                                    if blank
                                    else frame
                                ),
                            }
                        ],
                        "outputs": [
                            {
                                "signal": signal_id(
                                    "signal-A"
                                    if blank
                                    else nixie_signal_name(
                                        character
                                    )
                                ),
                                "copy_count_from_input": False,
                                "constant": 1,
                            }
                        ],
                    }
                },
            )

    for frame in range(frames):
        for column in range(width - 1):
            builder.wire(
                matrix[frame][column],
                2,
                matrix[frame][column + 1],
                2,
            )
    for frame in range(frames - 1):
        builder.wire(
            matrix[frame][0],
            2,
            matrix[frame + 1][0],
            2,
        )
    builder.wire(modulo, 4, matrix[0][0], 2)

    for column in range(width):
        builder.wire(
            tubes[column],
            1,
            matrix[0][column],
            3,
        )
        for frame in range(frames - 1):
            builder.wire(
                matrix[frame][column],
                3,
                matrix[frame + 1][column],
                3,
            )

    blueprint = {
        "blueprint": {
            "item": "blueprint",
            "label": f"{message} — Nixie Ticker",
            "description": (
                f"Offline-generated {width}-cell alpha Nixie "
                f"ticker. Requires the nixie-tubes mod."
            ),
            "icons": [
                {
                    "signal": {
                        "type": "item",
                        "name": "nixie-tube-alpha",
                    },
                    "index": 1,
                }
            ],
            "entities": builder.entities,
            "wires": builder.wires,
            "version": FACTORIO_VERSION,
        }
    }
    return blueprint, previews


def generate(config: TickerConfig) -> BlueprintResult:
    message = validate_config(config)

    if config.mode == "lamp-compact":
        blueprint, previews = build_compact_lamps(
            config,
            message,
        )
    elif config.mode == "lamp-compatible":
        blueprint, previews = build_compatible_lamps(
            config,
            message,
        )
    else:
        blueprint, previews = build_nixie(
            config,
            message,
        )

    validate_blueprint(blueprint)
    encoded = encode_blueprint(blueprint)
    if decode_blueprint(encoded) != blueprint:
        raise RuntimeError(
            "Blueprint encoding round-trip failed."
        )

    entities = blueprint["blueprint"]["entities"]
    names: dict[str, int] = {}
    for entity in entities:
        name = entity["name"]
        names[name] = names.get(name, 0) + 1

    stats: dict[str, int | float | str] = {
        "mode": MODE_LABELS[config.mode],
        "entities": len(entities),
        "wires": len(
            blueprint["blueprint"].get("wires", [])
        ),
        "lamps": names.get("small-lamp", 0),
        "nixie_tubes": names.get(
            "nixie-tube-alpha",
            0,
        ),
        "deciders": names.get(
            "decider-combinator",
            0,
        ),
        "arithmetic": names.get(
            "arithmetic-combinator",
            0,
        ),
        "frames": len(previews),
        "blueprint_characters": len(encoded),
        "max_wire_distance": round(
            max_wire_distance(blueprint),
            2,
        ),
    }

    return BlueprintResult(
        blueprint=blueprint,
        blueprint_string=encoded,
        stats=stats,
        normalized_message=message,
        preview_frames=previews,
    )
