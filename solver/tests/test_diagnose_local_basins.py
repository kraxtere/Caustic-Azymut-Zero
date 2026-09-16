import unittest

import numpy as np

from solver.diagnose_local_basins import _cluster_runs


class BasinDiagnosticTests(unittest.TestCase):
    def test_cluster_runs_separates_sources_beyond_threshold(self) -> None:
        runs = [
            {"source_km": np.array([0.0, 0.0, 0.0]), "rms_km": 2.0},
            {"source_km": np.array([0.001, 0.0, 0.0]), "rms_km": 1.0},
            {"source_km": np.array([10.0, 0.0, 0.0]), "rms_km": 3.0},
        ]
        clusters, labels = _cluster_runs(runs)
        self.assertEqual(labels, [0, 0, 1])
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0]["rms_km"], 1.0)


if __name__ == "__main__":
    unittest.main()

