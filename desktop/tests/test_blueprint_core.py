from __future__ import annotations

import ast
import sys
from pathlib import Path
import unittest

DESKTOP = Path(__file__).resolve().parents[1]
if str(DESKTOP) not in sys.path:
    sys.path.insert(0, str(DESKTOP))

from blueprint_core import (  # noqa: E402
    TickerConfig,
    decode_blueprint,
    generate,
    max_wire_distance,
)
from common import visible_pixel_frame, visible_text_frame  # noqa: E402


class BlueprintCoreTests(unittest.TestCase):
    def test_compact_known_structure(self) -> None:
        result = generate(TickerConfig())
        self.assertEqual(result.stats["lamps"], 168)
        self.assertEqual(result.stats["deciders"], 119)
        self.assertEqual(result.stats["arithmetic"], 27)
        self.assertEqual(result.stats["entities"], 314)
        self.assertLessEqual(result.stats["max_wire_distance"], 9.0)

    def test_compatibility_known_structure(self) -> None:
        result = generate(
            TickerConfig(mode="lamp-compatible", display_width=24)
        )
        self.assertEqual(result.stats["lamps"], 168)
        self.assertEqual(result.stats["deciders"], 833)
        self.assertEqual(result.stats["entities"], 1004)
        self.assertLessEqual(result.stats["max_wire_distance"], 9.0)

    def test_nixie_known_structure(self) -> None:
        result = generate(
            TickerConfig(
                mode="nixie",
                display_width=21,
                seconds_per_step=0.5,
                nixie_edge_spaces=1,
            )
        )
        self.assertEqual(result.stats["nixie_tubes"], 21)
        self.assertEqual(result.stats["deciders"], 441)
        self.assertEqual(result.stats["entities"], 465)
        self.assertLessEqual(result.stats["max_wire_distance"], 9.0)

    def test_large_scaled_compact_display(self) -> None:
        result = generate(
            TickerConfig(
                message="HELLO WORLD!",
                mode="lamp-compact",
                display_width=60,
                pixel_scale=2,
                direction="right",
                rom_columns=10,
            )
        )
        self.assertEqual(result.stats["lamps"], 60 * 7 * 4)
        self.assertLessEqual(max_wire_distance(result.blueprint), 9.0)

    def test_right_scroll_preserves_text_orientation(self) -> None:
        ring = "THE FACTORY "
        width = len(ring)

        self.assertEqual(
            visible_text_frame(ring, 0, width, "right"),
            ring,
        )
        self.assertEqual(
            visible_text_frame(ring, 1, width, "right"),
            ring[-1] + ring[:-1],
        )

        stream = [(number,) for number in range(6)]
        self.assertEqual(
            visible_pixel_frame(stream, 0, 6, "right"),
            stream,
        )
        self.assertEqual(
            visible_pixel_frame(stream, 1, 6, "right"),
            [stream[-1], *stream[:-1]],
        )

    def test_blueprint_round_trip(self) -> None:
        result = generate(TickerConfig(message="THE FACTORY MUST GROW"))
        self.assertEqual(decode_blueprint(result.blueprint_string), result.blueprint)

    def test_invalid_characters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generate(TickerConfig(message="HELLO 😀"))

    def test_runtime_source_has_no_network_or_subprocess_imports(self) -> None:
        forbidden = {
            "socket",
            "urllib",
            "http",
            "requests",
            "subprocess",
            "webbrowser",
            "ftplib",
            "telnetlib",
        }
        runtime_files = (
            "app.py",
            "blueprint_core.py",
            "catalog.py",
            "common.py",
            "generators.py",
            "models.py",
        )
        for filename in runtime_files:
            tree = ast.parse((DESKTOP / filename).read_text(encoding="utf-8"))
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
            self.assertTrue(
                forbidden.isdisjoint(imports),
                f"{filename} imports forbidden runtime modules: {forbidden & imports}",
            )


if __name__ == "__main__":
    unittest.main()