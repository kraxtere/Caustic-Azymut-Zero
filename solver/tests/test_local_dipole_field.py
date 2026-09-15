from __future__ import annotations

import unittest

import numpy as np

from solver.field_lens import LensFieldParams, n_and_grad


class LocalDipoleFieldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.radius = 7.0
        self.params = LensFieldParams(
            "maxwell", self.radius, dipole_epsilon=0.8
        )

    def test_index_equals_n0_everywhere_on_mirror(self) -> None:
        for direction in (
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([1.0, 2.0, -3.0]),
        ):
            point = self.radius * direction / np.linalg.norm(direction)
            index, _ = n_and_grad(point, self.params)
            self.assertAlmostEqual(index, self.params.n0, places=13)

    def test_centre_gradient_is_finite_and_matches_epsilon_over_r(self) -> None:
        index, gradient = n_and_grad(np.zeros(3), self.params)
        self.assertAlmostEqual(index, 2.0)
        np.testing.assert_allclose(
            gradient, np.array([0.0, 0.0, index * 0.8 / self.radius])
        )

    def test_analytic_gradient_matches_central_difference(self) -> None:
        point = np.array([1.1, -0.7, 2.3])
        _, gradient = n_and_grad(point, self.params)
        step = 1e-5
        numerical = np.zeros(3)
        for axis in range(3):
            offset = np.zeros(3)
            offset[axis] = step
            plus, _ = n_and_grad(point + offset, self.params)
            minus, _ = n_and_grad(point - offset, self.params)
            numerical[axis] = (plus - minus) / (2.0 * step)
        relative_error = np.linalg.norm(gradient - numerical) / np.linalg.norm(gradient)
        self.assertLessEqual(relative_error, 1e-6)


if __name__ == "__main__":
    unittest.main()
