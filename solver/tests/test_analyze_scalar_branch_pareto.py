import unittest

import numpy as np

from solver.analyze_scalar_branch_pareto import _minimax_path, _weighted_path


class ScalarBranchParetoTests(unittest.TestCase):
    def test_minimax_prefers_smoother_middle_state(self) -> None:
        rows = [
            [{"source_km": np.array([0.0, 0.0, 0.0]), "rms_km": 1.0}],
            [
                {"source_km": np.array([100.0, 0.0, 0.0]), "rms_km": 1.1},
                {"source_km": np.array([1000.0, 0.0, 0.0]), "rms_km": 1.0},
            ],
            [{"source_km": np.array([200.0, 0.0, 0.0]), "rms_km": 1.0}],
        ]
        path = _minimax_path(rows, np.array([0.0, 1.0, 2.0]))
        self.assertEqual(path, [0, 0, 0])

    def test_zero_weight_selects_local_rms_minima(self) -> None:
        rows = [
            [
                {"source_km": np.array([0.0, 0.0, 0.0]), "rms_km": 2.0},
                {"source_km": np.array([1.0, 0.0, 0.0]), "rms_km": 1.0},
            ],
            [
                {"source_km": np.array([0.0, 0.0, 0.0]), "rms_km": 1.0},
                {"source_km": np.array([1.0, 0.0, 0.0]), "rms_km": 2.0},
            ],
        ]
        self.assertEqual(_weighted_path(0.0, rows, np.array([0.0, 1.0])), [1, 0])


if __name__ == "__main__":
    unittest.main()
