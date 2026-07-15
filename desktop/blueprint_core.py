"""Public API for the offline Blueprint Ticker Maker generator."""

from __future__ import annotations

from dataclasses import asdict
import json

try:
    from .catalog import LAMP_COLORS, MODE_LABELS
    from .common import (
        decode_blueprint,
        encode_blueprint,
        max_wire_distance,
        validate_blueprint,
    )
    from .generators import generate
    from .models import BlueprintResult, TickerConfig
except ImportError:
    from catalog import LAMP_COLORS, MODE_LABELS
    from common import (
        decode_blueprint,
        encode_blueprint,
        max_wire_distance,
        validate_blueprint,
    )
    from generators import generate
    from models import BlueprintResult, TickerConfig


def config_as_json(config: TickerConfig) -> str:
    return json.dumps(
        asdict(config),
        indent=2,
        ensure_ascii=False,
    )


__all__ = [
    "BlueprintResult",
    "LAMP_COLORS",
    "MODE_LABELS",
    "TickerConfig",
    "config_as_json",
    "decode_blueprint",
    "encode_blueprint",
    "generate",
    "max_wire_distance",
    "validate_blueprint",
]
