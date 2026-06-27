from pathlib import Path
import unittest


class CloudProjectDocsTests(unittest.TestCase):
    def test_current_research_index_matches_single_main_remote_structure(self) -> None:
        index = Path("docs/research/CURRENT_RESEARCH_INDEX.md").read_text(encoding="utf-8")

        self.assertIn("Current remote topic branches: none", index)
        self.assertIn("Remote branch cleanup status: complete", index)
        self.assertIn("Deleted historical branches", index)
        self.assertNotIn("Current active CN stock sprint branch", index)
        self.assertNotIn("pending CN ETF research branch", index)
        self.assertNotIn("Do not delete `codex/factor-batch-cn-etf-20260617`", index)

    def test_readme_uses_real_safe_sync_trigger_phrase(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("say `同步项目`", readme)
        self.assertNotIn("鍚屾", readme)

    def test_workstation_policy_assigns_cloud_integration_to_laptop_only(self) -> None:
        policy = Path("configs/workstations.json").read_text(encoding="utf-8")

        self.assertIn('"trigger_phrase": "同步项目"', policy)
        self.assertIn('"factor_integration"', policy)


if __name__ == "__main__":
    unittest.main()
