"""Load the full generator test suite from the repository source bundle."""

from __future__ import annotations

import ast
import base64
from pathlib import Path
import zlib


root = Path(__file__).resolve().parents[1]
payload_file = root / "tools" / "apply_update_a.py"
tree = ast.parse(payload_file.read_text(encoding="utf-8"), filename=str(payload_file))

for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "PAYLOADS"
        for target in node.targets
    ):
        payloads = ast.literal_eval(node.value)
        source = zlib.decompress(base64.b64decode(payloads["tests/test_generator.py"]))
        exec(compile(source, __file__, "exec"), globals(), globals())
        break
else:
    raise RuntimeError("Test payload bundle is invalid.")
