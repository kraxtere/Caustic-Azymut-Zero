from __future__ import annotations

import math
import unittest

import numpy as np

from solver.maxwell_mirror import (
    MaxwellGreatCircleConstraint,
    lift_direction_to_three_sphere,
    maxwell_great_circle_constraint,
    maxwell_mirror_conjugate,
    stereographic_from_three_sphere,
    stereographic_to_three_sphere,
    solve_maxwell_mirror_branches,
    trace_maxwell_mirror_analytic,
    triangulate_maxwell_great_circles,
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
    @staticmethod
    def constraint_toward_auxiliary_point(
        observer_xyz: np.ndarray,
        target_xyzw: np.ndarray,
        radius: float = 1.0,
    ) -> MaxwellGreatCircleConstraint:
        observer = stereographic_to_three_sphere(observer_xyz, radius)
        cosine = float(np.dot(observer, target_xyzw) / radius**2)
        tangent = target_xyzw - cosine * observer
        tangent /= np.linalg.norm(tangent)
        return MaxwellGreatCircleConstraint(observer, tangent)

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

    def test_s3_great_circle_has_two_independent_normals(self) -> None:
        constraint = maxwell_great_circle_constraint(
            np.array([0.2, -0.35, 0.1]),
            np.array([1.0, 0.0, 0.2]),
            1.0,
        )
        eigenvalues = np.linalg.eigvalsh(constraint.plane_projector)
        np.testing.assert_allclose(eigenvalues, [0.0, 0.0, 1.0, 1.0], atol=1e-14)

    def test_closed_form_fit_recovers_known_source_and_sign(self) -> None:
        source = np.array([0.1, -0.12, 0.08])
        initial_directions = (
            np.array([1.0, 0.1, 0.0]),
            np.array([-0.2, 0.9, 0.1]),
            np.array([0.1, -0.2, 0.8]),
            np.array([-0.5, -0.3, 0.4]),
        )
        constraints = []
        for initial_direction in initial_directions:
            observer = trace_maxwell_mirror_analytic(
                source,
                initial_direction,
                mirror_radius=1.0,
                central_angle_rad=0.25,
            )
            self.assertEqual(observer.reflection_count, 0)
            constraints.append(
                maxwell_great_circle_constraint(
                    observer.point_xyz,
                    -observer.direction_xyz,
                    mirror_radius=1.0,
                )
            )

        fit = triangulate_maxwell_great_circles(constraints)
        np.testing.assert_allclose(fit.point_xyz, source, atol=2e-14)
        self.assertLess(fit.rms_plane_distance, 2e-15)
        self.assertEqual(fit.forward_observation_count, len(constraints))

    def test_closed_form_fit_rejects_an_underdetermined_axis(self) -> None:
        constraint = maxwell_great_circle_constraint(
            np.array([0.2, -0.35, 0.1]),
            np.array([1.0, 0.0, 0.2]),
            1.0,
        )
        with self.assertRaisesRegex(ValueError, "unique axis"):
            triangulate_maxwell_great_circles([constraint, constraint])

    def test_alternating_branches_recover_a_mixed_reflection_source(self) -> None:
        source_xyz = np.array([0.16, -0.11, 0.09])
        source = stereographic_to_three_sphere(source_xyz, 1.0)
        reflection = np.diag([1.0, 1.0, 1.0, -1.0])
        expected_parities = (False, True, False, True, True, False)
        observers = (
            np.array([0.30, 0.10, 0.05]),
            np.array([-0.25, 0.12, 0.18]),
            np.array([0.05, -0.32, 0.14]),
            np.array([0.22, 0.20, -0.16]),
            np.array([-0.18, -0.21, 0.11]),
            np.array([0.08, 0.27, 0.20]),
        )
        constraints = [
            self.constraint_toward_auxiliary_point(
                observer,
                reflection @ source if reflected else source,
            )
            for observer, reflected in zip(
                observers,
                expected_parities,
                strict=True,
            )
        ]

        result = solve_maxwell_mirror_branches(
            constraints,
            restarts=16,
            seed=20260915,
        )
        self.assertTrue(result.best.converged)
        self.assertTrue(result.best.fit.inside_mirror)
        np.testing.assert_allclose(
            result.best.fit.point_xyz,
            source_xyz,
            atol=2e-14,
        )
        self.assertLess(result.best.fit.rms_plane_distance, 2e-15)
        self.assertEqual(
            result.best.reflection_parities,
            expected_parities,
        )
        for run in result.runs:
            self.assertTrue(
                all(
                    later <= earlier + 1e-13
                    for earlier, later in zip(
                        run.objective_history,
                        run.objective_history[1:],
                    )
                )
            )

    def test_branch_restart_seed_changes_starts_not_exact_best_fit(self) -> None:
        source_xyz = np.array([0.16, -0.11, 0.09])
        source = stereographic_to_three_sphere(source_xyz, 1.0)
        reflection = np.diag([1.0, 1.0, 1.0, -1.0])
        parities = (False, True, False, True, True, False)
        observers = tuple(
            np.array(point)
            for point in (
                (0.30, 0.10, 0.05),
                (-0.25, 0.12, 0.18),
                (0.05, -0.32, 0.14),
                (0.22, 0.20, -0.16),
                (-0.18, -0.21, 0.11),
                (0.08, 0.27, 0.20),
            )
        )
        constraints = [
            self.constraint_toward_auxiliary_point(
                observer,
                reflection @ source if reflected else source,
            )
            for observer, reflected in zip(observers, parities, strict=True)
        ]
        first = solve_maxwell_mirror_branches(
            constraints,
            restarts=16,
            seed=11,
        )
        repeated = solve_maxwell_mirror_branches(
            constraints,
            restarts=16,
            seed=11,
        )
        second = solve_maxwell_mirror_branches(
            constraints,
            restarts=16,
            seed=12,
        )
        first_starts = tuple(run.initial_reflection_parities for run in first.runs)
        repeated_starts = tuple(
            run.initial_reflection_parities for run in repeated.runs
        )
        second_starts = tuple(run.initial_reflection_parities for run in second.runs)
        self.assertEqual(first_starts, repeated_starts)
        self.assertNotEqual(first_starts, second_starts)
        np.testing.assert_allclose(first.best.fit.point_xyz, source_xyz, atol=2e-14)
        np.testing.assert_allclose(second.best.fit.point_xyz, source_xyz, atol=2e-14)

    def test_noisy_overdetermined_branches_converge_across_seeds(self) -> None:
        source_xyz = np.array([0.16, -0.11, 0.09])
        source = stereographic_to_three_sphere(source_xyz, 1.0)
        reflection = np.diag([1.0, 1.0, 1.0, -1.0])
        parities = (False, True, False, True, True, False)
        observers = tuple(
            np.array(point)
            for point in (
                (0.30, 0.10, 0.05),
                (-0.25, 0.12, 0.18),
                (0.05, -0.32, 0.14),
                (0.22, 0.20, -0.16),
                (-0.18, -0.21, 0.11),
                (0.08, 0.27, 0.20),
            )
        )
        exact = [
            self.constraint_toward_auxiliary_point(
                observer,
                reflection @ source if reflected else source,
            )
            for observer, reflected in zip(observers, parities, strict=True)
        ]
        rng = np.random.default_rng(731)
        noisy = []
        for constraint in exact:
            tangent = constraint.sphere_tangent + 2e-4 * rng.normal(size=4)
            tangent -= (
                np.dot(tangent, constraint.sphere_point)
                * constraint.sphere_point
            )
            tangent /= np.linalg.norm(tangent)
            noisy.append(
                MaxwellGreatCircleConstraint(constraint.sphere_point, tangent)
            )

        results = [
            solve_maxwell_mirror_branches(
                noisy,
                restarts=16,
                seed=seed,
            )
            for seed in (3, 17, 91, 2048)
        ]
        for result in results:
            self.assertTrue(result.best.converged)
            self.assertEqual(result.best.reflection_parities, parities)
            np.testing.assert_allclose(
                result.best.fit.point_xyz,
                source_xyz,
                atol=5e-4,
            )
        for result in results[1:]:
            np.testing.assert_allclose(
                result.best.fit.point_xyz,
                results[0].best.fit.point_xyz,
                atol=1e-13,
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
