"""Data models and low-level blueprint builder."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Mode = Literal[
    "lamp-compact",
    "lamp-compatible",
    "lamp-static",
    "nixie",
    "nixie-static",
]
Direction = Literal["left", "right"]
Animation = Literal["loop", "once", "bounce", "static"]
CircuitLayout = Literal["below", "above", "left", "right", "compact-square", "strip"]
HorizontalAlign = Literal["left", "center", "right"]
VerticalAlign = Literal["top", "middle", "bottom"]


@dataclass(slots=True)
class TickerConfig:
    message: str = "THE FACTORY GROWS!!"
    mode: Mode = "lamp-compact"
    seconds_per_step: float = 0.2
    direction: Direction = "left"
    animation: Animation = "loop"
    display_width: int = 24
    display_height: int = 7
    character_spacing: int = 1
    repeat_gap: int = 6
    start_padding: int = 0
    end_padding: int = 0
    pixel_width: int = 1
    pixel_height: int = 1
    lamp_color: str = "yellow"
    rom_columns: int = 0
    nixie_edge_spaces: int = 1
    pause_seconds: float = 0.0
    full_message_pause_seconds: float = 0.0
    circuit_layout: CircuitLayout = "compact-square"
    horizontal_align: HorizontalAlign = "center"
    vertical_align: VerticalAlign = "middle"
    line_spacing: int = 1
    custom_font: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ticks_per_step(self) -> int:
        return max(1, round(self.seconds_per_step * 60))

    @property
    def pause_steps(self) -> int:
        if self.pause_seconds <= 0:
            return 0
        return max(1, round(self.pause_seconds / self.seconds_per_step))

    @property
    def full_message_pause_steps(self) -> int:
        if self.full_message_pause_seconds <= 0:
            return 0
        return max(1, round(self.full_message_pause_seconds / self.seconds_per_step))

    # Backward-compatible alias used by older callers/project files.
    @property
    def pixel_scale(self) -> int:
        return self.pixel_width if self.pixel_width == self.pixel_height else 1


@dataclass(slots=True)
class BlueprintResult:
    blueprint: dict
    blueprint_string: str
    stats: dict[str, int | float | str]
    normalized_message: str
    preview_frames: list
    warnings: list[str] = field(default_factory=list)


class BlueprintBuilder:
    def __init__(self) -> None:
        self.entities: list[dict] = []
        self.wires: list[list[int]] = []
        self._next_entity = 1

    def entity(self, **entity: object) -> int:
        entity_number = self._next_entity
        self._next_entity += 1
        record = dict(entity)
        record["entity_number"] = entity_number
        self.entities.append(record)
        return entity_number

    def wire(self, first: int, first_connector: int, second: int, second_connector: int) -> None:
        self.wires.append([first, first_connector, second, second_connector])
