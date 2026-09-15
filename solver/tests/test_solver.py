from __future__ import annotations

import unittest
from datetime import datetime, timezone

import numpy as np

from solver.ephemeris import MeeusLowPrecision, julian_day
from solver.field import FieldParams, n_and_grad, n_and_grad_components
from solver.fit_field import PARAMETER_SPACE, build_dataset, evaluate_field
from solver.geometry_flat import (
    R_MAP,
    altaz_of_radec,
    observer_xy,
    sky_direction_3d,
)
from solver.raytrace import (
    IntegrationOptions,
    trace_ray,
    triangulate_detailed,
    triangulate_half_lines_detailed,
)


class EphemerisTests(unittest.TestCase):
    def test_j2000_julian_day(self) -> None:
        instant = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
        self.assertAlmostEqual(julian_day(instant), 2451545.0, places=8)

    def test_2026_march_equinox_is_near_zero_declination(self) -> None:
        instant = datetime(2026, 3, 20, 12, tzinfo=timezone.utc)
        result = MeeusLowPrecision().sun_radec(instant)
        self.assertLess(abs(result.dec_deg), 0.1)


class GeometryTests(unittest.TestCase):
    def test_north_pole_is_map_origin(self) -> None:
        np.testing.assert_allclose(observer_xy(90, 123), [0, 0, 0], atol=1e-10)

    def test_south_pole_is_pi_r_from_centre(self) -> None:
        point = observer_xy(-90, 0)
        self.assertAlmostEqual(np.linalg.norm(point), np.pi * R_MAP, places=8)

    def test_solar_noon_equinox_geometry(self) -> None:
        instant = datetime(2026, 3, 20, 12, tzinfo=timezone.utc)
        ephemeris = MeeusLowPrecision()
        radec = ephemeris.sun_radec(instant)
        from solver.ephemeris import gmst_deg

        longitude = (radec.ra_deg - gmst_deg(instant) + 180) % 360 - 180
        altitude, _ = altaz_of_radec(radec, 52, longitude, instant)
        self.assertAlmostEqual(altitude, 38, delta=0.1)

    def test_sky_direction_is_unit_length(self) -> None:
        direction = sky_direction_3d(31, 247, 50, 18)
        self.assertAlmostEqual(np.linalg.norm(direction), 1.0, places=13)


class FieldTests(unittest.TestCase):
    def test_ring_peak_is_at_requested_radius(self) -> None:
        params = FieldParams(k=0, A=0.02, rho0=5000, s=1000)
        centre, gradient = n_and_grad(np.array([5000.0, 0.0, 0.0]), params)
        inside, _ = n_and_grad(np.array([4000.0, 0.0, 0.0]), params)
        outside, _ = n_and_grad(np.array([6000.0, 0.0, 0.0]), params)
        self.assertGreater(centre, inside)
        self.assertAlmostEqual(inside, outside, places=14)
        np.testing.assert_allclose(gradient, [0, 0, 0], atol=1e-14)

    def test_analytic_gradient_matches_finite_difference(self) -> None:
        params = FieldParams(k=0.0003, H=8, A=-0.02, rho0=5000, s=900)
        point = np.array([4300.0, 800.0, 250.0])
        _, analytic = n_and_grad(point, params)
        step = 1e-3
        finite = np.zeros(3)
        for axis in range(3):
            offset = np.zeros(3)
            offset[axis] = step
            plus, _ = n_and_grad(point + offset, params)
            minus, _ = n_and_grad(point - offset, params)
            finite[axis] = (plus - minus) / (2 * step)
        np.testing.assert_allclose(analytic, finite, rtol=2e-6, atol=1e-11)

    def test_component_gradients_add_up_to_total_gradient(self) -> None:
        params = FieldParams(k=0.0003, H=8, A=-0.02, rho0=5000, s=900)
        point = np.array([4300.0, 800.0, 250.0])
        refractive_index, total = n_and_grad(point, params)
        component_index, background, ring = n_and_grad_components(point, params)
        self.assertEqual(refractive_index, component_index)
        np.testing.assert_allclose(total, background + ring, atol=0.0)


class RayTests(unittest.TestCase):
    def test_zero_field_ray_stays_straight(self) -> None:
        params = FieldParams(k=0, A=0)
        direction = np.array([1.0, 0.5, 0.3])
        result = trace_ray(np.zeros(3), direction, params)
        np.testing.assert_allclose(
            result.direction,
            direction / np.linalg.norm(direction),
            atol=1e-14,
        )
        self.assertEqual(result.status, "escaped")

    def test_component_bending_diagnostics_do_not_change_ray(self) -> None:
        params = FieldParams(k=0.0003, H=8, A=0)
        direction = np.array([1.0, 0.0, 0.2])
        plain = trace_ray(np.zeros(3), direction, params)
        diagnosed = trace_ray(
            np.zeros(3),
            direction,
            params,
            collect_diagnostics=True,
        )
        np.testing.assert_allclose(diagnosed.point, plain.point, atol=0.0)
        np.testing.assert_allclose(diagnosed.direction, plain.direction, atol=0.0)
        self.assertGreater(diagnosed.background_path_bending_deg, 0.0)
        self.assertEqual(diagnosed.ring_path_bending_deg, 0.0)
        self.assertAlmostEqual(
            diagnosed.combined_path_bending_deg,
            diagnosed.background_path_bending_deg,
            places=14,
        )

    def test_exact_lines_triangulate_to_known_point(self) -> None:
        target = np.array([100.0, -25.0, 70.0])
        points = [
            np.array([0.0, 0.0, 0.0]),
            np.array([30.0, 50.0, 0.0]),
            np.array([-40.0, 15.0, 0.0]),
        ]
        directions = [target - point for point in points]
        result = triangulate_detailed(points, directions)
        np.testing.assert_allclose(result.point, target, atol=1e-11)
        self.assertLess(result.rms_km, 1e-11)
        self.assertGreater(np.min(result.forward_distances_km), 0)

    def test_half_lines_reject_an_intersection_behind_origins(self) -> None:
        points = [np.array([0.0, -1.0, 0.0]), np.array([0.0, 1.0, 0.0])]
        directions = [np.array([1.0, 1.0, 0.0]), np.array([1.0, -1.0, 0.0])]
        # Infinite lines meet at x=-1 when both directions are reversed here.
        directions = [-direction for direction in directions]
        line = triangulate_detailed(points, directions)
        ray = triangulate_half_lines_detailed(points, directions)
        self.assertLess(line.rms_km, 1e-12)
        self.assertGreater(ray.rms_km, 0.5)


class FitInfrastructureTests(unittest.TestCase):
    def test_parameter_normalization_round_trip(self) -> None:
        params = FieldParams(k=0.0003, H=8, A=0, rho0=5000, s=1500)
        restored = PARAMETER_SPACE.decode(PARAMETER_SPACE.encode(params))
        np.testing.assert_allclose(
            list(restored.__dict__.values()),
            list(params.__dict__.values()),
            rtol=1e-13,
        )

    def test_no_field_dataset_baseline(self) -> None:
        result = evaluate_field(
            FieldParams(k=0, A=0),
            build_dataset(),
            IntegrationOptions(),
            intersection_mode="lines",
        )
        self.assertEqual(result.invalid_rays, 0)
        self.assertAlmostEqual(result.cost_km, 2439.62, delta=0.1)


if __name__ == "__main__":
    unittest.main()
