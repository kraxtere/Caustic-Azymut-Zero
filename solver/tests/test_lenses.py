from __future__ import annotations

import math
import unittest

import numpy as np

from solver.lenses import (
    luneburg_index,
    luneburg_ray_state,
    luneburg_surface_focus,
    maxwell_fisheye_index,
    maxwell_mirror_image,
    maxwell_spherical_ray,
    stereographic_from_sphere,
    stereographic_to_sphere,
)


class MaxwellFishEyeTests(unittest.TestCase):
    def test_index_has_expected_centre_equator_and_far_values(self) -> None:
        self.assertEqual(maxwell_fisheye_index(0, 4, n0=1.3), 2.6)
        self.assertEqual(maxwell_fisheye_index(4, 4, n0=1.3), 1.3)
        self.assertLess(maxwell_fisheye_index(4000, 4, n0=1.3), 3e-6)

    def test_stereographic_projection_round_trip(self) -> None:
        point = np.array([0.35, -0.72])
        sphere_point = stereographic_to_sphere(point, sphere_radius=2.5)
        self.assertAlmostEqual(np.linalg.norm(sphere_point), 2.5, places=13)
        np.testing.assert_allclose(
            stereographic_from_sphere(sphere_point, sphere_radius=2.5),
            point,
            atol=2e-15,
        )

    def test_all_great_circle_rays_meet_at_antipode(self) -> None:
        radius = 3.0
        source = stereographic_to_sphere(
            np.array([0.4, -0.2]),
            sphere_radius=radius,
        )
        trial_tangents = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([1.0, -2.0, 0.5]),
        ]
        endpoints = [
            maxwell_spherical_ray(source, tangent, math.pi, radius)
            for tangent in trial_tangents
        ]
        for endpoint in endpoints:
            np.testing.assert_allclose(endpoint, -source, atol=2e-15)

    def test_mirror_image_is_diametrically_opposite(self) -> None:
        source = np.array([0.2, -0.45])
        np.testing.assert_array_equal(maxwell_mirror_image(source, 1.0), -source)


class LuneburgTests(unittest.TestCase):
    def test_index_matches_standard_profile(self) -> None:
        self.assertAlmostEqual(luneburg_index(0, 7), math.sqrt(2), places=14)
        self.assertEqual(luneburg_index(7, 7), 1.0)
        self.assertEqual(luneburg_index(9, 7), 1.0)

    def test_parallel_bundle_focuses_at_opposite_surface(self) -> None:
        radius = 2.0
        direction = np.array([1.0, 0.0, 0.0])
        impact_parameters = [
            (0.0, 0.0),
            (0.3, -0.4),
            (-0.9, 0.2),
            (0.5, 1.1),
        ]
        focus = luneburg_surface_focus(direction, radius)
        for y, z in impact_parameters:
            x = -math.sqrt(radius**2 - y**2 - z**2)
            entry = np.array([x, y, z])
            state = luneburg_ray_state(
                entry,
                direction,
                optical_parameter=math.pi * radius / 2,
                lens_radius=radius,
            )
            np.testing.assert_allclose(state.point, focus, atol=3e-16)

    def test_analytic_ray_preserves_luneburg_hamiltonian(self) -> None:
        radius = 2.0
        direction = np.array([1.0, 0.0, 0.0])
        entry = np.array([-math.sqrt(2.75), 1.0, 0.5])
        for fraction in np.linspace(0.0, 0.5, 11):
            state = luneburg_ray_state(
                entry,
                direction,
                optical_parameter=fraction * math.pi * radius,
                lens_radius=radius,
            )
            n_value = luneburg_index(np.linalg.norm(state.point), radius)
            self.assertAlmostEqual(
                float(np.dot(state.optical_momentum, state.optical_momentum)),
                n_value**2,
                places=13,
            )


if __name__ == "__main__":
    unittest.main()
