from __future__ import annotations

import argparse
import unittest

from solver.scan_luneburg import (
    DEFAULT_BASE_RADIUS_KM,
    DEFAULT_STAGE1_Z0_FRACTIONS,
    apply_promotion_gate,
    build_candidates,
    build_scan_groups,
    parse_float_list,
)


def _target(rms: float, forward: float = 1.0) -> dict[str, object]:
    return {
        "invalid_rays": 0,
        "triangulation_valid": True,
        "rms_km": rms,
        "minimum_forward_distance_km": forward,
    }


def _metrics(
    solar_rms: float,
    north_rms: float,
    south_rms: float,
    *,
    forward: bool = True,
) -> dict[str, object]:
    minimum = 1.0 if forward else -0.001
    return {
        "solar_centres": {
            "complete": True,
            "mean_rms_km": solar_rms,
            "all_minimum_forward_distances_non_negative": forward,
        },
        "celestial_poles": {
            "all_minimum_forward_distances_non_negative": forward,
            "targets": {
                "north_celestial_pole": _target(north_rms, minimum),
                "south_celestial_pole": _target(south_rms, minimum),
            },
        },
    }


class ScanDesignTests(unittest.TestCase):
    def test_stage_one_starts_with_nonzero_offsets_then_zero_control(self) -> None:
        candidates = build_candidates("z0", DEFAULT_BASE_RADIUS_KM, None)
        self.assertEqual(len(candidates), len(DEFAULT_STAGE1_Z0_FRACTIONS))
        self.assertTrue(all(item.radius_km == DEFAULT_BASE_RADIUS_KM for item in candidates))
        offsets = [item.centre_km[2] for item in candidates]
        self.assertTrue(all(value != 0.0 for value in offsets[:-1]))
        self.assertEqual(offsets[-1], 0.0)
        self.assertTrue(any(value < 0.0 for value in offsets[:-1]))
        self.assertTrue(any(value > 0.0 for value in offsets[:-1]))

    def test_grid_requires_stage_one_selected_z0_neighbourhood(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires --z0-fractions"):
            build_candidates("grid", DEFAULT_BASE_RADIUS_KM, None)
        candidates = build_candidates(
            "grid",
            DEFAULT_BASE_RADIUS_KM,
            (-0.4, -0.3),
            (0.9, 1.1),
        )
        self.assertEqual(len(candidates), 4)

    def test_float_list_rejects_duplicates(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_float_list("0.5,0.5")

    def test_scan_uses_fifteen_centres_and_two_poles(self) -> None:
        solar, poles = build_scan_groups(2.0, 0.2666)
        self.assertEqual(len(solar), 15)
        self.assertEqual(len(poles), 2)
        self.assertEqual({group.target_id for group in poles}, {
            "north_celestial_pole",
            "south_celestial_pole",
        })


class PromotionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = _metrics(100.0, 20.0, 30.0)

    def test_requires_all_three_rms_improvements_and_forward_rays(self) -> None:
        result = apply_promotion_gate(
            _metrics(99.0, 19.0, 29.0),
            self.baseline,
        )
        self.assertTrue(result["passed"])

    def test_equal_rms_does_not_beat_baseline(self) -> None:
        result = apply_promotion_gate(
            _metrics(100.0, 19.0, 29.0),
            self.baseline,
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["solar_mean_rms_below_n_equals_1"])

    def test_negative_forward_distance_blocks_better_rms(self) -> None:
        result = apply_promotion_gate(
            _metrics(90.0, 10.0, 20.0, forward=False),
            self.baseline,
        )
        self.assertFalse(result["passed"])
        self.assertFalse(
            result["checks"]["all_minimum_forward_distances_non_negative"]
        )

    def test_incomplete_solar_set_cannot_pass(self) -> None:
        candidate = _metrics(90.0, 10.0, 20.0)
        candidate["solar_centres"]["complete"] = False
        candidate["solar_centres"]["mean_rms_km"] = None
        result = apply_promotion_gate(candidate, self.baseline)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
