from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HypothesisPortfolioTests(unittest.TestCase):
    def test_parent_defines_hypothesis_portfolio_and_search_rounds(self) -> None:
        text = (ROOT / "skills/gpu-code-optimizer/SKILL.md").read_text(encoding="utf-8")
        section = text.split("## Hypothesis portfolio and search rounds", 1)[1].split(
            "## Quick execution checklist", 1
        )[0]
        for snippet in [
            "Baseline ID",
            "reset/restore procedure",
            "per-variant baseline check",
            "one factor per variant",
            "independent variants",
            "cheapest falsifying experiment",
            "parallelize them only when the environment preserves measurement isolation",
            "Confidence",
            "prediction",
            "residual",
            "re-classify the bottleneck",
            "Keep as default / Keep behind guard/flag / Keep as local micro-optimization only / Reject / Need more evidence",
        ]:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet.casefold(), section.casefold())

        self.assertLess(section.index("Baseline ID"), section.index("Hypothesis:"))
        self.assertLess(section.index("one factor per variant"), section.index("Results:"))
        self.assertLess(section.index("Confidence"), section.index("Status:"))


if __name__ == "__main__":
    unittest.main()
