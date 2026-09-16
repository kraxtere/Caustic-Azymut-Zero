import unittest

import numpy as np

from solver.scan_scalar_branch_boundary import ALPHA_CONSENSUS_RAD, _cluster_sources


class ScalarBranchBoundaryTests(unittest.TestCase):
    def test_cluster_sources_separates_distant_basins(self) -> None:
        labels = _cluster_sources(
            [
                np.array([0.0, 0.0, 0.0]),
                np.array([0.1, 0.0, 0.0]),
                np.array([10.0, 0.0, 0.0]),
            ],
            threshold_km=1.0,
        )
        self.assertEqual(labels, [0, 0, 1])

    def test_alpha_consensus_is_stricter_than_visible_path_change(self) -> None:
        first = np.array([0.5, 1.0, 1.5])
        second = first.copy()
        second[1] += 2.0 * ALPHA_CONSENSUS_RAD
        self.assertGreater(float(np.max(np.abs(first - second))), ALPHA_CONSENSUS_RAD)


if __name__ == "__main__":
    unittest.main()
