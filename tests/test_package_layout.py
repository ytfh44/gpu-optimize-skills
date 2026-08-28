from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_readme_points_to_search_autonomy_evaluation(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("optimization-search-autonomy.md", text)
        self.assertIn("python -m unittest discover -s tests -v", text)

    def test_tests_are_named_after_features(self) -> None:
        test_files = list((ROOT / "tests").glob("test_*.py"))
        legacy_test_marker = "test_" + "issue" + "4"
        self.assertTrue(test_files)
        self.assertTrue(all(legacy_test_marker not in path.name.casefold() for path in test_files))
        self.assertFalse(
            any(legacy_test_marker in path.name.casefold() for path in (ROOT / "tests").rglob("*"))
        )

    def test_skill_documents_stay_within_runtime_loading_budget(self) -> None:
        for skill_file in (ROOT / "skills").glob("*/SKILL.md"):
            with self.subTest(skill=skill_file.parent.name):
                self.assertLessEqual(
                    len(skill_file.read_text(encoding="utf-8").splitlines()), 500
                )

    def test_forbidden_superpowers_tree_is_not_part_of_the_package(self) -> None:
        self.assertFalse((ROOT / "docs" / "superpowers").exists())


if __name__ == "__main__":
    unittest.main()
