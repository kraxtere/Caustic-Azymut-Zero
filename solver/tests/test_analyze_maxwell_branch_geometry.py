from __future__ import annotations

import math
import unittest

from solver.analyze_maxwell_branch_geometry import (
    disk_uses_one_branch_signature,
    effective_image_distance_km,
    inverse_stereographic_local_scale,
    legendre_modes,
)


class MaxwellBranchGeometryAnalysisTests(unittest.TestCase):
    def test_effective_distance_uses_full_angular_diameter(self) -> None:
        angle_deg = 0.5
        distance = 10_000.0
        diameter = distance * math.radians(angle_deg)
        self.assertAlmostEqual(
            effective_image_distance_km(diameter, angle_deg / 2.0), distance
        )

    def test_disk_signature_detects_one_limb_switch(self) -> None:
        selectors = {
            "centre": {"selected_reflection_parities": [False, True]},
            "north": {"selected_reflection_parities": [False, True]},
            "east": {"selected_reflection_parities": [True, True]},
        }
        self.assertFalse(disk_uses_one_branch_signature(selectors))
        selectors["east"]["selected_reflection_parities"] = [False, True]
        self.assertTrue(disk_uses_one_branch_signature(selectors))

    def test_even_p2_cannot_distinguish_opposite_solstices(self) -> None:
        north = legendre_modes(23.44)
        south = legendre_modes(-23.44)
        self.assertAlmostEqual(north["p2"], south["p2"])
        self.assertAlmostEqual(north["p1"], -south["p1"])
        self.assertAlmostEqual(north["p3"], -south["p3"])

    def test_intermediate_declination_separates_p1_from_p3(self) -> None:
        solstice = legendre_modes(23.44)
        intermediate = legendre_modes(11.7)
        solstice_ratio = solstice["p3"] / solstice["p1"]
        intermediate_ratio = intermediate["p3"] / intermediate["p1"]
        self.assertAlmostEqual(solstice_ratio, -1.1044, places=3)
        self.assertAlmostEqual(intermediate_ratio, -1.3971, places=3)
        self.assertGreater(abs(intermediate_ratio - solstice_ratio), 0.25)

    def test_inverse_stereographic_scale_diverges_only_at_north_pole(self) -> None:
        self.assertAlmostEqual(inverse_stereographic_local_scale(0.0, 2.0), 1.0)
        self.assertAlmostEqual(inverse_stereographic_local_scale(-2.0, 2.0), 0.5)
        self.assertGreater(inverse_stereographic_local_scale(1.99, 2.0), 100.0)
        with self.assertRaises(ValueError):
            inverse_stereographic_local_scale(2.0, 2.0)


if __name__ == "__main__":
    unittest.main()
