from __future__ import annotations

import argparse
import unittest

from solver.validate_maxwell import apply_maxwell_gate, parse_integer_list


def _target(
    target_id: str,
    rms: float,
    point: list[float],
    *,
    valid: bool = True,
    forward: bool = True,
    consensus: bool = True,
) -> dict[str, object]:
    return {
        "target_id": target_id,
        "valid": valid,
        "direction_rms_deg": rms,
        "common_point_s3_km": point,
        "all_rays_forward": forward,
        "restart_seed_consensus": consensus,
        "inside_mirror": True,
        "source_above_map": True,
    }


def _metrics(
    solar_rms: float,
    north_rms: float,
    south_rms: float,
    *,
    forward: bool = True,
    collapsed: bool = False,
) -> dict[str, object]:
    north = [1.0, 0.0, 0.0, 0.0]
    south = north if collapsed else [0.0, 1.0, 0.0, 0.0]
    solar_target = _target(
        "solar",
        solar_rms,
        [0.0, 0.0, 1.0, 0.0],
        forward=forward,
    )
    pole_targets = [
        _target(
            "north_celestial_pole",
            north_rms,
            north,
            forward=forward,
        ),
        _target(
            "south_celestial_pole",
            south_rms,
            south,
            forward=forward,
        ),
    ]
    return {
        "solar_centres": {
            "complete": True,
            "mean_direction_rms_deg": solar_rms,
            "targets": [solar_target],
        },
        "celestial_poles": {
            "complete": True,
            "targets": pole_targets,
        },
    }


class MaxwellGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = _metrics(10.0, 5.0, 6.0)

    def test_gate_requires_all_three_strict_improvements(self) -> None:
        result = apply_maxwell_gate(
            _metrics(9.0, 4.0, 5.0),
            self.baseline,
            1.0,
        )
        self.assertTrue(result["passed"])

    def test_equal_north_pole_rms_fails(self) -> None:
        result = apply_maxwell_gate(
            _metrics(9.0, 5.0, 5.0),
            self.baseline,
            1.0,
        )
        self.assertFalse(result["passed"])
        self.assertFalse(
            result["checks"]["north_pole_direction_rms_below_n_equals_1"]
        )

    def test_forward_violation_fails(self) -> None:
        result = apply_maxwell_gate(
            _metrics(9.0, 4.0, 5.0, forward=False),
            self.baseline,
            1.0,
        )
        self.assertFalse(result["checks"]["all_maxwell_rays_forward"])

    def test_collapsed_poles_fail(self) -> None:
        result = apply_maxwell_gate(
            _metrics(9.0, 4.0, 5.0, collapsed=True),
            self.baseline,
            1.0,
        )
        self.assertFalse(result["checks"]["celestial_poles_not_collapsed"])

    def test_seed_parser_rejects_duplicates(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_integer_list("3,17,3")


if __name__ == "__main__":
    unittest.main()
