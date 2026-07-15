"""Public API for the offline Blueprint Ticker Maker generator."""
from __future__ import annotations

from dataclasses import asdict, fields
import json

try:
    from .catalog import ANIMATION_LABELS, BUILTIN_PRESETS, CIRCUIT_LAYOUT_LABELS, LAMP_COLORS, MODE_LABELS
    from .common import decode_blueprint, encode_blueprint, max_wire_distance, validate_blueprint
    from .generators import generate, generate_blueprint_book
    from .models import BlueprintResult, TickerConfig
except ImportError:
    from catalog import ANIMATION_LABELS, BUILTIN_PRESETS, CIRCUIT_LAYOUT_LABELS, LAMP_COLORS, MODE_LABELS
    from common import decode_blueprint, encode_blueprint, max_wire_distance, validate_blueprint
    from generators import generate, generate_blueprint_book
    from models import BlueprintResult, TickerConfig


def config_as_json(config: TickerConfig) -> str:
    return json.dumps(asdict(config), indent=2, ensure_ascii=False)


def config_from_dict(data: dict) -> TickerConfig:
    allowed = {field.name for field in fields(TickerConfig)}
    clean = {key: value for key, value in data.items() if key in allowed}
    # Upgrade old project files that had one square pixel_scale option.
    if "pixel_scale" in data:
        clean.setdefault("pixel_width", data["pixel_scale"])
        clean.setdefault("pixel_height", data["pixel_scale"])
    return TickerConfig(**clean)


def project_as_json(config: TickerConfig) -> str:
    return json.dumps({"format": "blueprint-ticker-maker-project", "version": 1, "config": asdict(config)}, indent=2, ensure_ascii=False)


def project_from_json(text: str) -> TickerConfig:
    data = json.loads(text)
    if isinstance(data, dict) and "config" in data:
        return config_from_dict(data["config"])
    if isinstance(data, dict):
        return config_from_dict(data)
    raise ValueError("Project file does not contain a configuration object.")


__all__ = [
    "ANIMATION_LABELS", "BUILTIN_PRESETS", "BlueprintResult", "CIRCUIT_LAYOUT_LABELS",
    "LAMP_COLORS", "MODE_LABELS", "TickerConfig", "config_as_json", "config_from_dict",
    "decode_blueprint", "encode_blueprint", "generate", "generate_blueprint_book",
    "max_wire_distance", "project_as_json", "project_from_json", "validate_blueprint",
]
