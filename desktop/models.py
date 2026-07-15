"""Data models and low-level blueprint builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Mode = Literal["lamp-compact", "lamp-compatible", "nixie"]
Direction = Literal["left", "right"]


@dataclass(slots=True)
class TickerConfig:
    message: str = "THE FACTORY GROWS!!"
    mode: Mode = "lamp-compact"
    seconds_per_step: float = 0.2
    direction: Direction = "left"
    display_width: int = 24
    character_spacing: int = 1
    repeat_gap: int = 6
    pixel_scale: int = 1
    lamp_color: str = "yellow"
    rom_columns: int = 0
    nixie_edge_spaces: int = 1

    @property
    def ticks_per_step(self) -> int:
        return max(1, round(self.seconds_per_step * 60))


@dataclass(slots=True)
class BlueprintResult:
    blueprint: dict
    blueprint_string: str
    stats: dict[str, int | float | str]
    normalized_message: str
    preview_frames: list


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

    def wire(
        self,
        first: int,
        first_connector: int,
        second: int,
        second_connector: int,
    ) -> None:
        self.wires.append([first, first_connector, second, second_connector])
