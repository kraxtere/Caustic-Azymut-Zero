from __future__ import annotations

import copy
import unittest

import numpy as np

from solver.continue_maxwell_branches import evaluate_fixed_branches
from solver.identify_maxwell_response import identify
from solver.scan_maxwell_declination import build_declination_groups
from solver.validate_maxwell_c2 import SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM
from solver.validate_v1 import TargetGroup


class MaxwellResponseIdentificationTests(unittest.TestCase):
    @staticmethod
    def _records(p1: float, p3: float) -> list[dict[str, object]]:
        from solver.analyze_maxwell_branch_geometry import legendre_modes

        records = []
        for delta in (-23.44, -17.58, -11.72, -5.86, 0.0, 5.86, 11.72, 17.58, 23.44):
            modes = legendre_modes(delta)
            log_correction = p1 * modes["p1"] + p3 * modes["p3"]
            records.append(
                {
                    "declination_deg": delta,
                    "transfer_scale_km_per_radian": float(np.exp(-log_correction)),
                }
            )
        return records

    def test_pure_dipole_is_selected_by_intermediate_prediction(self) -> None:
        result = identify(self._records(0.4, 0.0))
        self.assertTrue(result["dipole_only"]["passed"])
        self.assertEqual(result["selected_response_basis"], "P1")

    def test_p1_p3_uses_intermediate_pair_and_passes_holdouts(self) -> None:
        result = identify(self._records(0.4, -1.0))
        self.assertFalse(result["dipole_only"]["passed"])
        self.assertTrue(result["dipole_plus_octupole"]["passed"])
        self.assertEqual(result["selected_response_basis"], "P1+P3")

    def test_source_label_cannot_change_fixed_branch_solution(self) -> None:
        _, item = build_declination_groups()[4]
        original = item["groups"]["centre"]
        renamed = TargetGroup(
            target_id="moon-with-identical-geometry",
            timestamp_utc=original.timestamp_utc,
            origins=original.origins,
            directions=original.directions,
            observer_coordinates_deg=original.observer_coordinates_deg,
        )
        centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
        parities = (False,) * len(original.origins)
        first = evaluate_fixed_branches(
            original, SELECTED_RADIUS_KM, centre, parities
        )
        second = evaluate_fixed_branches(
            renamed, SELECTED_RADIUS_KM, centre, parities
        )
        np.testing.assert_allclose(
            first["common_point_s3_km"], second["common_point_s3_km"]
        )


if __name__ == "__main__":
    unittest.main()
