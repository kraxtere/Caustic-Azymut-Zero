from __future__ import annotations

import unittest

from solver.scan_maxwell_radius import (
    DEFAULT_RADIUS_FRACTIONS,
    FIXED_CENTRE_Z_KM,
    build_radius_candidates,
)
from solver.validate_maxwell import DEFAULT_RADIUS_KM


class MaxwellRadiusScanDesignTests(unittest.TestCase):
    def test_increased_radii_precede_control(self) -> None:
        candidates = build_radius_candidates()
        self.assertEqual(len(candidates), 6)
        self.assertTrue(all(value > DEFAULT_RADIUS_KM for value in candidates[:-1]))
        self.assertEqual(candidates[-1], DEFAULT_RADIUS_KM)

    def test_pre_registered_grid_cannot_be_changed(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be changed"):
            build_radius_candidates(fractions=(1.1, 1.0))
        expected = tuple(
            DEFAULT_RADIUS_KM * value for value in DEFAULT_RADIUS_FRACTIONS
        )
        self.assertEqual(build_radius_candidates(), expected)

    def test_centre_height_is_fixed_in_kilometres(self) -> None:
        self.assertEqual(FIXED_CENTRE_Z_KM, 0.40 * DEFAULT_RADIUS_KM)
        ratios = tuple(FIXED_CENTRE_Z_KM / r for r in build_radius_candidates())
        self.assertGreater(ratios[-1], ratios[0])
        self.assertAlmostEqual(ratios[-1], 0.40)


if __name__ == "__main__":
    unittest.main()
