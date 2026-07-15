from __future__ import annotations

import ast
import sys
from pathlib import Path
import unittest

DESKTOP = Path(__file__).resolve().parents[1]
ROOT = DESKTOP.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desktop.blueprint_core import (  # noqa: E402
    TickerConfig,
    decode_blueprint,
    generate,
    generate_blueprint_book,
    project_as_json,
    project_from_json,
)
from desktop.common import visible_pixel_frame, visible_text_frame  # noqa: E402


class BlueprintCoreTests(unittest.TestCase):
    def test_compact_known_structure(self) -> None:
        result = generate(TickerConfig())
        self.assertEqual(result.stats["lamps"], 168)
        self.assertEqual(result.stats["deciders"], 119)
        self.assertEqual(result.stats["arithmetic"], 27)
        self.assertEqual(result.stats["entities"], 314)
        self.assertLessEqual(result.stats["max_wire_distance"], 9.0)

    def test_compatibility_known_structure(self) -> None:
        result = generate(TickerConfig(mode="lamp-compatible", display_width=24))
        self.assertEqual(result.stats["lamps"], 168)
        self.assertEqual(result.stats["deciders"], 833)
        self.assertEqual(result.stats["entities"], 1004)
        self.assertLessEqual(result.stats["max_wire_distance"], 9.0)

    def test_static_multiline_and_independent_pixel_dimensions(self) -> None:
        result = generate(TickerConfig(
            message="HELLO\nWORLD", mode="lamp-static", animation="static",
            display_width=32, display_height=16, pixel_width=2, pixel_height=3,
        ))
        self.assertEqual(result.stats["lamps"], 32 * 16 * 2 * 3)
        self.assertEqual(result.stats["frames"], 1)
        self.assertEqual(result.stats["display_lamps_wide"], 64)
        self.assertEqual(result.stats["display_lamps_high"], 48)

    def test_nixie_static_and_scrolling(self) -> None:
        scrolling = generate(TickerConfig(mode="nixie", display_width=16))
        static = generate(TickerConfig(mode="nixie-static", display_width=16, animation="static"))
        self.assertEqual(scrolling.stats["nixie_tubes"], 16)
        self.assertEqual(static.stats["nixie_tubes"], 16)
        self.assertEqual(static.stats["frames"], 1)

    def test_right_scroll_preserves_orientation(self) -> None:
        ring = "THE FACTORY "
        self.assertEqual(visible_text_frame(ring, 0, len(ring), "right"), ring)
        self.assertEqual(visible_text_frame(ring, 1, len(ring), "right"), ring[-1] + ring[:-1])
        stream = [(n,) for n in range(6)]
        self.assertEqual(visible_pixel_frame(stream, 0, 6, "right"), stream)
        self.assertEqual(visible_pixel_frame(stream, 1, 6, "right"), [stream[-1], *stream[:-1]])

    def test_animation_behaviours_generate(self) -> None:
        for animation in ("loop", "once", "bounce"):
            result = generate(TickerConfig(message="TEST", animation=animation, pause_seconds=0.2))
            self.assertGreater(result.stats["frames"], 1)
            self.assertLessEqual(result.stats["max_wire_distance"], 9.0)

    def test_all_compact_layouts_keep_wires_short(self) -> None:
        for layout in ("compact-square", "below", "above", "left", "right", "strip"):
            result = generate(TickerConfig(
                message="TEST", display_width=24, display_height=12,
                pixel_width=2, pixel_height=2, circuit_layout=layout,
            ))
            self.assertLessEqual(result.stats["max_wire_distance"], 9.0, layout)

    def test_custom_font(self) -> None:
        custom = {"€": ["11111", "10000", "11110", "10000", "11111", "00000", "00000"]}
        result = generate(TickerConfig(message="€ 100", custom_font=custom))
        self.assertTrue(result.blueprint_string.startswith("0"))

    def test_project_round_trip(self) -> None:
        config = TickerConfig(
            message="PROJECT", display_width=40, display_height=11,
            pixel_width=3, pixel_height=2, circuit_layout="right",
            animation="bounce", start_padding=12, end_padding=8,
        )
        restored = project_from_json(project_as_json(config))
        self.assertEqual(restored, config)

    def test_blueprint_book_contains_variants(self) -> None:
        book, encoded = generate_blueprint_book(TickerConfig(message="BOOK TEST"))
        self.assertGreaterEqual(len(book["blueprint_book"]["blueprints"]), 3)
        self.assertEqual(decode_blueprint(encoded), book)

    def test_blueprint_round_trip(self) -> None:
        result = generate(TickerConfig(message="THE FACTORY MUST GROW"))
        self.assertEqual(decode_blueprint(result.blueprint_string), result.blueprint)

    def test_runtime_source_has_no_network_or_subprocess_imports(self) -> None:
        forbidden = {"socket", "urllib", "http", "requests", "subprocess", "webbrowser", "ftplib", "telnetlib"}
        for filename in ("app.py", "blueprint_core.py", "catalog.py", "common.py", "generators.py", "models.py"):
            tree = ast.parse((DESKTOP / filename).read_text(encoding="utf-8"))
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
            self.assertTrue(forbidden.isdisjoint(imports), f"{filename} imports forbidden modules")


if __name__ == "__main__":
    unittest.main()
