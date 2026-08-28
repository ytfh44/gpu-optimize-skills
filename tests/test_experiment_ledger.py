from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ExperimentLedgerTests(unittest.TestCase):
    def test_validation_scopes_rejections_and_revalidates_compositions(self) -> None:
        text = (ROOT / "skills/gpu-optimization-validation/SKILL.md").read_text(encoding="utf-8")
        section = text.split("## Evidence-scoped experiment ledger", 1)[1].split(
            "## Representative benchmark matrix", 1
        )[0]
        for snippet in [
            "Baseline ID",
            "immutable snapshot",
            "reset/restore",
            "rejected hypothesis",
            "Evidence state / workload domain",
            "Falsifier",
            "Reopen if",
            "Reopened from",
            "accepted change",
            "composition revalidation",
            "same baseline",
            "Constituent IDs",
            "Interaction result",
            "New bottleneck",
            "Keep, guard, or reject the composition independently",
            "acceptance matrix",
        ]:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet.casefold(), section.casefold())


if __name__ == "__main__":
    unittest.main()
