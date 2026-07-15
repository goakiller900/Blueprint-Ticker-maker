from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from desktop.blueprint_core import TickerConfig, decode_blueprint, generate
from generator import main


class GeneratorTests(unittest.TestCase):
    def test_compact_blueprint_round_trip(self) -> None:
        result = generate(TickerConfig(message="THE FACTORY GROWS!!"))
        self.assertEqual(decode_blueprint(result.blueprint_string), result.blueprint)
        self.assertEqual(result.stats["entities"], 314)

    def test_right_scroll_does_not_reverse_message(self) -> None:
        result = generate(
            TickerConfig(
                message="THE FACTORY",
                mode="nixie",
                direction="right",
                display_width=11,
                nixie_edge_spaces=0,
            )
        )
        self.assertEqual(result.preview_frames[0], "THE FACTORY")
        self.assertEqual(result.preview_frames[1], "YTHE FACTOR")

    def test_cli_writes_blueprint_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blueprint_path = root / "ticker.txt"
            json_path = root / "ticker.json"

            exit_code = main(
                [
                    "HELLO WORLD",
                    "--direction",
                    "right",
                    "--output",
                    str(blueprint_path),
                    "--json",
                    str(json_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            decoded = decode_blueprint(blueprint_path.read_text(encoding="utf-8"))
            self.assertEqual(decoded, json.loads(json_path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()