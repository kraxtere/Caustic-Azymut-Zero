from __future__ import annotations

import unittest

from solver.continue_maxwell_branches import (
    build_common_cohort_tracks,
    common_observer_cohort,
    multiplicative_decomposition,
)


class MaxwellForcedBranchContinuationTests(unittest.TestCase):
    def test_common_cohort_is_identical_for_all_tracks_and_targets(self) -> None:
        tracks = build_common_cohort_tracks()
        cohorts = {tuple(map(tuple, track["fixed_observers_deg"])) for track in tracks}
        self.assertEqual(len(cohorts), 1)
        cohort = next(iter(cohorts))
        self.assertEqual(len(cohort), 8)
        for track in tracks:
            for moment in track["moments"]:
                for group in moment["groups"].values():
                    self.assertEqual(group.observer_coordinates_deg, cohort)

    def test_factorisation_is_exact_and_reports_sequential_increment(self) -> None:
        result = multiplicative_decomposition(
            selected_december_diameter=150.0,
            direct_december_diameter=120.0,
            direct_june_diameter=100.0,
            expected_input_ratio=1.05,
        )
        self.assertAlmostEqual(
            result["total_unexplained_ratio"],
            result["smooth_direct_continuation_ratio"]
            * result["discrete_branch_multiplier"],
        )
        self.assertAlmostEqual(result["factorisation_identity_error"], 0.0)
        self.assertAlmostEqual(
            result["branch_increment_after_smooth_fraction_points"],
            result["total_unexplained_ratio"]
            - result["smooth_direct_continuation_ratio"],
        )
        self.assertAlmostEqual(
            result["smooth_log_share"] + result["branch_log_share"], 1.0
        )

    def test_common_cohort_rejects_an_empty_intersection(self) -> None:
        tracks = (
            {"fixed_observers_deg": [[1.0, 2.0]]},
            {"fixed_observers_deg": [[3.0, 4.0]]},
        )
        with self.assertRaises(ValueError):
            common_observer_cohort(tracks)


if __name__ == "__main__":
    unittest.main()
