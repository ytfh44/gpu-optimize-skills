from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CausalProbeTests(unittest.TestCase):
    def test_performance_evidence_records_predictions_and_surprises(self) -> None:
        text = (ROOT / "skills/gpu-performance-evidence/SKILL.md").read_text(encoding="utf-8")
        section = text.split("## Causal probes and prediction records", 1)[1].split(
            "## End-to-end priority rule", 1
        )[0]
        for snippet in [
            "Baseline controls",
            "same workload, device state, correctness contract, measurement scope",
            "compiler/dispatcher/runtime reachability",
            "generated code or the realized schedule",
            "Observed symptom",
            "Proposed mechanism",
            "Predicted independent evidence",
            "Cheapest falsifying probe",
            "Confounders and controls",
            "Cost",
            "Outcome",
            "metric and mechanism move as predicted",
            "neither moves",
            "mechanism moves but target metric does not",
            "target metric moves without the predicted mechanism",
            "movement has the opposite sign",
            "high-value residual evidence",
            "warm-up",
            "synchronization",
            "clock",
            "allocator",
            "profiler-validity",
            "confidence",
        ]:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet.casefold(), section.casefold())


if __name__ == "__main__":
    unittest.main()
