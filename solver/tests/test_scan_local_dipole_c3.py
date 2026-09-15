from __future__ import annotations

import unittest

from solver.scan_local_dipole_c3 import EPSILON_GRID, START_SEEDS


class LocalDipoleC3ScanContractTests(unittest.TestCase):
    def test_grid_is_symmetric_unique_and_contains_control(self) -> None:
        self.assertEqual(len(EPSILON_GRID), len(set(EPSILON_GRID)))
        self.assertIn(0.0, EPSILON_GRID)
        self.assertEqual(tuple(-value for value in reversed(EPSILON_GRID)), EPSILON_GRID)

    def test_scan_has_seven_alternative_starts(self) -> None:
        self.assertEqual(len(START_SEEDS), 7)
        self.assertEqual(len(START_SEEDS), len(set(START_SEEDS)))


if __name__ == "__main__":
    unittest.main()
