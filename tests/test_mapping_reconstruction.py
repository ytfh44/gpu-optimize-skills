from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MappingReconstructionTests(unittest.TestCase):
    def test_kernel_guidance_derives_candidates_from_mappings_and_constraints(self) -> None:
        text = (ROOT / "skills/gpu-kernel-execution/SKILL.md").read_text(encoding="utf-8")
        section = text.split(
            "## Mapping reconstruction and constraint-derived candidates", 1
        )[1].split("## Occupancy and resource pressure", 1)[0]
        for snippet in [
            "Observed mapping/evidence",
            "Evidence source/scope",
            "Assumptions and unknowns",
            "Preconditions",
            "logical work",
            "ownership / decomposition",
            "execution instances",
            "hardware scheduling slots",
            "logical values",
            "memory transactions",
            "execution pipelines",
            "dependency DAG",
            "semantic",
            "numerical",
            "alignment",
            "bounds",
            "synchronization",
            "aliasing",
            "remaining degrees of freedom",
            "new cost",
            "launch/dispatch",
            "units and scope",
            "IR/ISA",
            "barrier",
            "guard and fallback",
            "one-factor transformation",
        ]:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet.casefold(), section.casefold())

        mapping_order = [
            "logical work",
            "ownership / decomposition",
            "execution instances",
            "hardware scheduling slots",
            "logical values",
            "layout / address mapping",
            "memory transactions",
            "banks / cache sets / pages / channels",
        ]
        positions = [section.index(item) for item in mapping_order]
        self.assertEqual(positions, sorted(positions))

        lowering_order = [
            "logical operations",
            "compiler lowering",
            "instructions",
            "execution pipelines",
        ]
        lowering_positions = [section.index(item) for item in lowering_order]
        self.assertEqual(lowering_positions, sorted(lowering_positions))

        dag_order = [
            "dependency DAG",
            "schedule",
            "resource occupancy over time",
        ]
        dag_positions = [section.index(item) for item in dag_order]
        self.assertEqual(dag_positions, sorted(dag_positions))


if __name__ == "__main__":
    unittest.main()
