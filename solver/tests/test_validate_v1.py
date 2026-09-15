from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from solver.ephemeris import RaDec
from solver.validate_v1 import (
    DEFAULT_SOLAR_RADIUS_DEG,
    _visible_observers,
    angular_separation_deg,
    observer_grid,
    solar_disk_samples,
    validate_fit,
)


class ValidationGeometryTests(unittest.TestCase):
    def test_default_grid_has_64_unique_observers(self) -> None:
        observers = observer_grid()
        self.assertEqual(len(observers), 64)
        self.assertEqual(len(set(observers)), 64)

    def test_solar_limb_offsets_have_exact_angular_radius(self) -> None:
        centre = RaDec(ra_deg=359.9, dec_deg=23.4)
        samples = solar_disk_samples(centre)
        self.assertEqual(
            set(samples),
            {"centre", "north_limb", "south_limb", "east_limb", "west_limb"},
        )
        for name, limb in samples.items():
            expected = 0.0 if name == "centre" else DEFAULT_SOLAR_RADIUS_DEG
            self.assertAlmostEqual(
                angular_separation_deg(centre, limb),
                expected,
                places=9,
            )

    def test_poles_select_the_expected_hemisphere(self) -> None:
        observers = observer_grid()
        instant = datetime(2026, 3, 20, tzinfo=timezone.utc)
        north = _visible_observers((RaDec(0, 90),), instant, observers, 2.0)
        south = _visible_observers((RaDec(0, -90),), instant, observers, 2.0)
        self.assertEqual(len(north), 32)
        self.assertEqual(len(south), 32)
        self.assertTrue(all(latitude > 0 for latitude, _ in north))
        self.assertTrue(all(latitude < 0 for latitude, _ in south))

    def test_no_field_validation_report_is_strict_json(self) -> None:
        instant = datetime(2026, 3, 20, 14, tzinfo=timezone.utc)
        fit = {
            "model": "axisymmetric-atmosphere-plus-gaussian-ring-v1",
            "intersection_mode": "rays",
            "optimizer": {"seed": 7},
            "fitted_cost_km": 1.0,
            "parameters": {"k": 0, "H": 8, "A": 0, "rho0": 5000, "s": 1000},
            "integration": {
                "max_path_km": 500000,
                "rtol": 1e-4,
                "atol": 1e-7,
                "gradient_tolerance_per_km": 1e-9,
                "escape_sigma": 7,
                "maximum_step_km": None,
                "ground_tolerance_km": 1e-6,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fit.json"
            path.write_text(json.dumps(fit), encoding="utf-8")
            with patch("solver.validate_v1.MOMENTS", (instant,)):
                report = validate_fit(path)
        self.assertEqual(report["grid"]["candidate_observer_count"], 64)
        self.assertEqual(report["c2_solar_disk"]["summary"]["valid_disk_count"], 1)
        json.dumps(report, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
