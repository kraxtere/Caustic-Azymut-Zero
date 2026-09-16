import unittest

import numpy as np

from solver.scan_scalar_branch_boundary import _cluster_sources


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


if __name__ == "__main__":
    unittest.main()
