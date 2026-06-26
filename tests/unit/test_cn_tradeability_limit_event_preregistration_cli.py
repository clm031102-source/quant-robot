import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_tradeability_limit_event_preregistration import (
    run_cn_tradeability_limit_event_preregistration_cli,
)


class CNTradeabilityLimitEventPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_round159_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_cn_tradeability_limit_event_preregistration_cli(output_dir=output)

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(
                result["summary"]["next_required_gate"],
                "round160_cn_tradeability_limit_event_proxy_prescreen",
            )
            self.assertTrue((output / "cn_tradeability_limit_event_preregistration.json").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_preregistration.md").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_candidates.csv").exists())

    def test_cli_raises_when_candidate_or_family_floor_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                run_cn_tradeability_limit_event_preregistration_cli(
                    output_dir=tmp,
                    min_candidates=99,
                    min_families=4,
                )


if __name__ == "__main__":
    unittest.main()
