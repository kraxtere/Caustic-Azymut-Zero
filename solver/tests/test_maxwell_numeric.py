from __future__ import annotations

import math
import unittest

import numpy as np

from solver.field_lens import LensFieldParams
from solver.maxwell_mirror import trace_maxwell_mirror_analytic
from solver.maxwell_numeric import (
    build_local_maxwell_curve,
    trace_local_maxwell_to_central_angle,
)


def _angle_deg(first: np.ndarray, second: np.ndarray) -> float:
    cosine = float(
        np.clip(
            np.dot(first, second)
            / (float(np.linalg.norm(first)) * float(np.linalg.norm(second))),
            -1.0,
            1.0,
        )
    )
    return math.degrees(math.acos(cosine))


class LocalMaxwellNumericalPropagatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.radius = 10.0
        self.params = LensFieldParams("maxwell", self.radius)
        self.cases = (
            (np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.2, 0.1])),
            (np.array([2.0, -1.0, 3.0]), np.array([0.2, 0.7, 0.4])),
            (np.array([-4.0, 2.0, 1.0]), np.array([-0.3, 0.1, 0.9])),
        )
        self.angles = (0.25, 0.8, 1.7, 2.8)

    def test_epsilon_zero_reproduces_twelve_analytic_s3_rays(self) -> None:
        reflection_cases = 0
        for position, direction in self.cases:
            for angle in self.angles:
                with self.subTest(position=position.tolist(), angle=angle):
                    analytic = trace_maxwell_mirror_analytic(
                        position, direction, self.radius, angle
                    )
                    numeric = trace_local_maxwell_to_central_angle(
                        position, direction, self.params, angle
                    )
                    point_error = float(
                        np.linalg.norm(numeric.point_xyz - analytic.point_xyz)
                    )
                    direction_error = _angle_deg(
                        numeric.direction_xyz, analytic.direction_xyz
                    )
                    self.assertLessEqual(point_error, 1e-7 * self.radius)
                    self.assertLessEqual(direction_error, 1e-5)
                    self.assertEqual(
                        numeric.reflection_count % 2, analytic.reflection_count
                    )
                    reflection_cases += int(numeric.reflection_count > 0)
        self.assertGreater(reflection_cases, 0)

    def test_tighter_integrator_changes_endpoint_below_frozen_limit(self) -> None:
        position, direction = self.cases[1]
        coarse = trace_local_maxwell_to_central_angle(
            position,
            direction,
            self.params,
            2.4,
            rtol=1e-9,
            atol=1e-11,
            maximum_step_fraction=1.0 / 250.0,
        )
        fine = trace_local_maxwell_to_central_angle(
            position,
            direction,
            self.params,
            2.4,
            rtol=1e-10,
            atol=1e-12,
            maximum_step_fraction=1.0 / 500.0,
        )
        self.assertLessEqual(
            float(np.linalg.norm(coarse.point_xyz - fine.point_xyz)),
            1e-7 * self.radius,
        )

    def test_dense_curve_matches_analytic_first_interval(self) -> None:
        position, direction = self.cases[2]
        curve = build_local_maxwell_curve(position, direction, self.params)
        for angle in self.angles:
            point, tangent = curve.state_at_angle(angle)
            analytic = trace_maxwell_mirror_analytic(
                position, direction, self.radius, angle
            )
            self.assertLessEqual(
                float(np.linalg.norm(point - analytic.point_xyz)),
                1e-7 * self.radius,
            )
            self.assertLessEqual(_angle_deg(tangent, analytic.direction_xyz), 1e-5)


if __name__ == "__main__":
    unittest.main()
