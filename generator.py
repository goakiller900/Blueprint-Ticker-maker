#!/usr/bin/env python3
"""Load the full Blueprint Ticker Maker generator from its source bundle."""

from __future__ import annotations

import ast
import base64
from pathlib import Path
import zlib


def _load_payload(name: str) -> bytes:
    payload_file = Path(__file__).with_name("tools") / "apply_update_a.py"
    tree = ast.parse(payload_file.read_text(encoding="utf-8"), filename=str(payload_file))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PAYLOADS"
            for target in node.targets
        ):
            payloads = ast.literal_eval(node.value)
            return zlib.decompress(base64.b64decode(payloads[name]))
    raise RuntimeError("Source payload bundle is invalid.")


_source = _load_payload("generator.py")
exec(compile(_source, __file__, "exec"), globals(), globals())
