from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import generator  # noqa: E402


class GeneratorTests(unittest.TestCase):
    def test_known_banner_structure(self) -> None:
        message = generator.normalize_message("GOAKILLER900 IS GAY", 1)
        self.assertEqual(message, " GOAKILLER900 IS GAY ")
        self.assertEqual(len(message), 21)

        blueprint = generator.build_blueprint(message, 30)
        generator.validate_structure(blueprint)

        entities = blueprint["blueprint"]["entities"]
        self.assertEqual(len(entities), 465)
        self.assertEqual(
            sum(entity["name"] == "nixie-tube-alpha" for entity in entities),
            21,
        )
        self.assertEqual(
            sum(entity["name"] == "decider-combinator" for entity in entities),
            441,
        )

    def test_blueprint_round_trip(self) -> None:
        message = generator.normalize_message("THE FACTORY MUST GROW!", 2)
        blueprint = generator.build_blueprint(message, 21)
        encoded = generator.encode_blueprint(blueprint)

        decoded = json.loads(
            zlib.decompress(base64.b64decode(encoded[1:]))
        )
        self.assertEqual(decoded, blueprint)

    def test_lowercase_and_whitespace_normalization(self) -> None:
        self.assertEqual(
            generator.normalize_message("  hello\n\tworld  ", 1),
            " HELLO WORLD ",
        )

    def test_unsupported_character_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported character"):
            generator.normalize_message("NO €", 1)

    def test_invalid_wire_reference_is_rejected(self) -> None:
        message = generator.normalize_message("TEST", 1)
        blueprint = generator.build_blueprint(message, 30)
        blueprint["blueprint"]["wires"].append([999999, 1, 1, 1])

        with self.assertRaisesRegex(ValueError, "missing entity"):
            generator.validate_structure(blueprint)


if __name__ == "__main__":
    unittest.main()
