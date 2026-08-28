from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FreshContextEvaluationTests(unittest.TestCase):
    def test_evaluation_rewards_rediscovery_and_rejects_recipe_parroting(self) -> None:
        text = (ROOT / "evals/optimization-search-autonomy.md").read_text(encoding="utf-8")
        for snippet in [
            "Fresh-context evaluation contract",
            "unseen mechanism",
            "named technique",
            "falsifying",
            "negative result",
            "reopen",
            "re-profile",
            "Minimum scoring rubric",
            "0 / 1 / 2",
            "8/12",
            "raw-prompt-only isolation",
            "critical failure",
        ]:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet.casefold(), text.casefold())

        cases = [
            block
            for block in re.split(r"\n## ", text)
            if "**Raw user prompt**" in block and "**Pass condition:**" in block
        ]
        self.assertEqual(len(cases), 5)
        for case in cases:
            raw_prompt = case.split("**Raw user prompt**", 1)[1].split(
                "**Pass condition:**", 1
            )[0]
            self.assertNotIn("Expected primary skill", raw_prompt)
            self.assertNotIn("Allowed secondary skills", raw_prompt)
            self.assertNotIn("Pass condition", raw_prompt)
            self.assertIn("**Pass condition:**", case)


if __name__ == "__main__":
    unittest.main()
