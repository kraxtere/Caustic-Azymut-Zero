from __future__ import annotations

import math
import unittest

import numpy as np

from solver.maxwell_mirror import (
    lift_direction_to_three_sphere,
    maxwell_great_circle_constraint,
    maxwell_mirror_conjugate,
    stereographic_from_three_sphere,
    stereographic_to_three_sphere,
    trace_maxwell_mirror_analytic,
)


class ThreeSphereProjectionTests(unittest.TestCase):
    def test_projection_round_trip_in_full_3d(self) -> None:
        point = np.array([0.7, -1.1, 0.4])
        sphere = stereographic_to_three_sphere(point, 3.0)
        self.assertAlmostEqual(np.linalg.norm(sphere), 3.0, places=13)
        np.testing.assert_allclose(
            stereographic_from_three_sphere(sphere, 3.0),
            point,
            atol=5e-16,
        )

    def test_lifted_direction_matches_finite_difference(self) -> None:
        point = np.array([0.7, -1.1, 0.4])
        direction = np.array([0.3, 0.8, -0.2])
        direction /= np.linalg.norm(direction)
        tangent = lift_direction_to_three_sphere(point, direction, 3.0)
        step = 1e-7
        finite = (
            stereographic_to_three_sphere(point + step * direction, 3.0)
            - stereographic_to_three_sphere(point - step * direction, 3.0)
        ) / (2.0 * step)
        finite /= np.linalg.norm(finite)
        np.testing.assert_allclose(tangent, finite, rtol=2e-9, atol=2e-9)


class AnalyticMaxwellMirrorTests(unittest.TestCase):
    def test_first_image_is_minus_source_for_multiple_directions(self) -> None:
        position = np.array([0.2, -0.35, 0.1])
        directions = (
            np.array([1.0, 0.0, 0.2]),
            np.array([-0.4, 0.8, 0.1]),
            np.array([0.2, -0.1, 1.0]),
        )
        expected = maxwell_mirror_conjugate(position)
        for direction in directions:
            state = trace_maxwell_mirror_analytic(
                position,
                direction,
                mirror_radius=1.0,
                central_angle_rad=math.pi,
            )
            np.testing.assert_allclose(state.point_xyz, expected, atol=2e-15)
            self.assertEqual(state.reflection_count, 1)
            self.assertAlmostEqual(state.optical_path_n0_km, math.pi)

    def test_positive_path_parameter_rejects_backward_or_later_cycles(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\[0, pi\]"):
            trace_maxwell_mirror_analytic(
                np.zeros(3),
                np.array([1.0, 0.0, 0.0]),
                1.0,
                -0.01,
            )
        with self.assertRaisesRegex(ValueError, r"\[0, pi\]"):
            trace_maxwell_mirror_analytic(
                np.zeros(3),
                np.array([1.0, 0.0, 0.0]),
                1.0,
                math.pi + 0.01,
            )

    def test_fold_obeys_specular_reflection_at_spherical_mirror(self) -> None:
        position = np.array([0.2, -0.3, 0.1])
        direction = np.array([0.7, 0.1, 0.5])
        radius = 1.0
        constraint = maxwell_great_circle_constraint(
            position,
            direction,
            radius,
        )
        q = constraint.sphere_point
        tangent = constraint.sphere_tangent
        crossing = math.atan2(-q[3] / radius, tangent[3])
        epsilon = 1e-7
        before = trace_maxwell_mirror_analytic(
            position,
            direction,
            radius,
            crossing - epsilon,
        )
        after = trace_maxwell_mirror_analytic(
            position,
            direction,
            radius,
            crossing + epsilon,
        )
        boundary = (before.point_xyz + after.point_xyz) / 2.0
        normal = boundary / np.linalg.norm(boundary)
        expected_after = before.direction_xyz - 2.0 * np.dot(
            before.direction_xyz,
            normal,
        ) * normal
        np.testing.assert_allclose(
            after.direction_xyz,
            expected_after,
            rtol=0.0,
            atol=5e-7,
        )

    def test_single_observation_is_a_curve_not_unique_arbitrary_source(self) -> None:
        position = np.array([0.2, -0.35, 0.1])
        first = maxwell_great_circle_constraint(
            position,
            np.array([1.0, 0.0, 0.0]),
            1.0,
        )
        second = maxwell_great_circle_constraint(
            position,
            np.array([0.0, 1.0, 0.0]),
            1.0,
        )
        self.assertGreater(
            np.linalg.norm(first.plane_projector - second.plane_projector),
            0.1,
        )
        np.testing.assert_array_equal(
            maxwell_mirror_conjugate(position),
            -position,
        )

    def test_translated_mirror_conjugate(self) -> None:
        centre = np.array([10.0, -3.0, 2.0])
        position = np.array([10.2, -3.35, 2.1])
        np.testing.assert_allclose(
            maxwell_mirror_conjugate(position, centre),
            np.array([9.8, -2.65, 1.9]),
            atol=1e-15,
        )

    def test_distinct_observers_do_not_supply_one_source_candidate(self) -> None:
        first_observer = np.array([0.2, -0.35, 0.1])
        second_observer = np.array([-0.1, 0.4, 0.25])
        first_candidate = maxwell_mirror_conjugate(first_observer)
        second_candidate = maxwell_mirror_conjugate(second_observer)
        self.assertGreater(
            np.linalg.norm(first_candidate - second_candidate),
            0.1,
        )


if __name__ == "__main__":
    unittest.main()
