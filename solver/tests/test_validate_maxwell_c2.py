from __future__ import annotations

import math
import copy
import unittest

from solver.validate_maxwell_c2 import (
    FORWARD_MARGIN_ANGLE_DEG,
    MINIMUM_FORWARD_SINE,
    SAMPLE_IDS,
    SELECTED_CENTRE_Z_KM,
    SELECTED_RADIUS_KM,
    apply_full_c2_gate,
    build_c2_tracks,
)
from solver.validate_maxwell import DEFAULT_RADIUS_KM


class MaxwellFullC2ContractTests(unittest.TestCase):
    @staticmethod
    def _passing_gate_inputs():
        target = {
            "valid": True,
            "restart_seed_consensus": True,
            "restart_branch_assignment_consensus": True,
            "minimum_forward_sine": 0.20,
            "inside_mirror": True,
            "source_above_map": True,
        }
        shape = {"axis_ratio": 1.01, "normalised_centre_offset": 0.01}
        tracks = []
        for track_index in range(3):
            moments = []
            for moment_index in range(5):
                moments.append(
                    {
                        "timestamp_utc": f"track-{track_index}-{moment_index}",
                        "targets": {
                            sample: copy.deepcopy(target) for sample in SAMPLE_IDS
                        },
                        "reconstructed_disk": dict(shape),
                    }
                )
            tracks.append(
                {
                    "moments": moments,
                    "summary": {
                        "diameter_coefficient_of_variation": 0.01,
                        "diameter_max_to_min_ratio": 1.02,
                    },
                }
            )
        candidate_c2 = {
            "daily_tracks": tracks,
            "summary": {
                "valid_disk_count": 15,
                "mean_centre_direction_rms_deg": 1.0,
                "diameter_coefficient_of_variation": 0.01,
                "diameter_max_to_min_ratio": 1.02,
            },
        }
        baseline_c2 = {"summary": {"mean_centre_direction_rms_deg": 2.0}}
        radius = SELECTED_RADIUS_KM
        candidate_poles = {
            "complete": True,
            "targets": [
                {
                    "target_id": "north_celestial_pole",
                    "valid": True,
                    "direction_rms_deg": 1.0,
                    "common_point_s3_km": [radius, 0.0, 0.0, 0.0],
                    "restart_seed_consensus": True,
                    "restart_branch_assignment_consensus": True,
                    "all_rays_forward": True,
                    "inside_mirror": True,
                    "source_above_map": True,
                },
                {
                    "target_id": "south_celestial_pole",
                    "valid": True,
                    "direction_rms_deg": 1.0,
                    "common_point_s3_km": [0.0, radius, 0.0, 0.0],
                    "restart_seed_consensus": True,
                    "restart_branch_assignment_consensus": True,
                    "all_rays_forward": True,
                    "inside_mirror": True,
                    "source_above_map": True,
                },
            ],
        }
        baseline_poles = {
            "targets": [
                {"target_id": "north_celestial_pole", "direction_rms_deg": 2.0},
                {"target_id": "south_celestial_pole", "direction_rms_deg": 2.0},
            ]
        }
        return candidate_c2, baseline_c2, candidate_poles, baseline_poles

    def test_selected_candidate_is_exactly_the_radius_scan_winner(self) -> None:
        self.assertAlmostEqual(SELECTED_RADIUS_KM, 1.20 * DEFAULT_RADIUS_KM)
        self.assertAlmostEqual(SELECTED_CENTRE_Z_KM, 0.40 * DEFAULT_RADIUS_KM)

    def test_forward_margin_is_a_predeclared_ten_degree_buffer(self) -> None:
        self.assertEqual(FORWARD_MARGIN_ANGLE_DEG, 10.0)
        self.assertAlmostEqual(MINIMUM_FORWARD_SINE, math.sin(math.radians(10.0)))

    def test_full_c2_design_has_three_tracks_fifteen_disks_and_75_targets(self) -> None:
        tracks = build_c2_tracks()
        self.assertEqual(len(tracks), 3)
        self.assertEqual(sum(len(track["moments"]) for track in tracks), 15)
        self.assertEqual(
            sum(
                len(moment["groups"])
                for track in tracks
                for moment in track["moments"]
            ),
            75,
        )
        self.assertTrue(
            all(
                tuple(moment["groups"].keys()) == SAMPLE_IDS
                for track in tracks
                for moment in track["moments"]
            )
        )

    def test_gate_requires_branch_assignment_consensus_per_target(self) -> None:
        inputs = self._passing_gate_inputs()
        self.assertTrue(
            apply_full_c2_gate(
                *inputs, SELECTED_RADIUS_KM, matches_contract=True
            )["passed"]
        )
        candidate = inputs[0]
        candidate["daily_tracks"][0]["moments"][0]["targets"]["east_limb"][
            "restart_branch_assignment_consensus"
        ] = False
        result = apply_full_c2_gate(
            *inputs, SELECTED_RADIUS_KM, matches_contract=True
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["all_c2_branch_assignments_agree"])

    def test_positive_but_subthreshold_forward_margin_fails(self) -> None:
        inputs = self._passing_gate_inputs()
        candidate = inputs[0]
        candidate["daily_tracks"][0]["moments"][0]["targets"]["north_limb"][
            "minimum_forward_sine"
        ] = 0.01
        result = apply_full_c2_gate(
            *inputs, SELECTED_RADIUS_KM, matches_contract=True
        )
        self.assertFalse(result["passed"])
        self.assertFalse(
            result["checks"]["all_c2_forward_margins_at_least_sin_10_deg"]
        )


if __name__ == "__main__":
    unittest.main()
