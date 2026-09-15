from __future__ import annotations

import unittest

from solver.scan_maxwell_declination import (
    DECLINATIONS_DEG,
    _trend,
    build_declination_groups,
)
from solver.validate_maxwell_c2 import SAMPLE_IDS


class MaxwellDeclinationScanDesignTests(unittest.TestCase):
    def test_grid_is_symmetric_includes_zero_and_has_common_observers(self) -> None:
        self.assertEqual(len(DECLINATIONS_DEG), 9)
        self.assertEqual(DECLINATIONS_DEG[4], 0.0)
        self.assertEqual(DECLINATIONS_DEG, tuple(-x for x in reversed(DECLINATIONS_DEG)))
        design = build_declination_groups()
        observer_sets = [item["observer_coordinates_deg"] for _, item in design]
        self.assertTrue(observer_sets[0])
        self.assertTrue(all(value == observer_sets[0] for value in observer_sets))
        self.assertTrue(
            all(tuple(item["groups"].keys()) == SAMPLE_IDS for _, item in design)
        )

    def test_trend_requires_strict_monotonicity_and_linear_r_squared(self) -> None:
        increasing = _trend([float(index) for index in range(9)])
        self.assertTrue(increasing["hypothesis_supported"])
        nonmonotonic = _trend([0.0, 1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0, 0.0])
        self.assertFalse(nonmonotonic["hypothesis_supported"])


if __name__ == "__main__":
    unittest.main()
