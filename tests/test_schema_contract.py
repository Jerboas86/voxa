import json
from pathlib import Path
import unittest


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"


class SchemaContractTest(unittest.TestCase):
    def test_corpus_schema_requires_proxy_signals(self) -> None:
        schema = self._load_schema("voxa.corpus.schema.json")

        self.assertIn("proxy_signals", schema["required"])
        self.assertIn("proxy_signals", schema["properties"])
        self.assertEqual(schema["properties"]["proxy_signals"]["minItems"], 1)

    def test_corpus_schema_defines_proxy_signal_shape(self) -> None:
        schema = self._load_schema("voxa.corpus.schema.json")
        proxy_signal = schema["$defs"]["proxySignal"]

        self.assertEqual(
            proxy_signal["required"],
            [
                "proxy_id",
                "kind",
                "target_metric",
                "rms_dbfs",
                "duration_s",
                "audio_path",
                "audio_hash",
            ],
        )
        self.assertEqual(proxy_signal["properties"]["audio_path"]["pattern"], "^(?!/).+")
        self.assertEqual(proxy_signal["properties"]["duration_s"]["minimum"], 0)

    def test_corpus_schema_requires_white_noise_overall_rms_proxy(self) -> None:
        schema = self._load_schema("voxa.corpus.schema.json")

        contains_conditions = [
            clause["properties"]["proxy_signals"]["contains"]
            for clause in schema["allOf"]
            if "properties" in clause and "proxy_signals" in clause["properties"]
        ]

        self.assertTrue(contains_conditions)
        self.assertIn(
            {
                "type": "object",
                "properties": {
                    "kind": {"const": "white_noise"},
                    "target_metric": {"const": "overall_rms_dbfs"},
                },
                "required": ["kind", "target_metric"],
            },
            contains_conditions,
        )

    def test_corpus_schema_defines_overall_rms_dbfs(self) -> None:
        schema = self._load_schema("voxa.corpus.schema.json")
        corpus_statistics = schema["$defs"]["corpusStatistics"]["properties"]

        self.assertEqual(corpus_statistics["overall_rms_dbfs"]["type"], "number")

        dependent_clause = next(
            clause["then"]
            for clause in schema["allOf"]
            if "then" in clause
            and clause["then"].get("required") == ["corpus_statistics"]
        )
        self.assertIn("overall_rms_dbfs", dependent_clause["properties"]["corpus_statistics"]["required"])

    def _load_schema(self, filename: str) -> dict:
        return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
