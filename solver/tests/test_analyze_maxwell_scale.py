from __future__ import annotations

import unittest

import numpy as np

from solver.analyze_maxwell_scale import (
    fit_correction_models,
    residual_correction,
    select_model,
)


class MaxwellScaleAnalysisTests(unittest.TestCase):
    def test_residual_correction_is_one_at_zero(self) -> None:
        declinations = (-10.0, 0.0, 10.0)
        correction = residual_correction(declinations, (2.0, 4.0, 8.0))
        np.testing.assert_allclose(correction, (2.0, 1.0, 0.5))

    def test_exact_linear_delta_selects_one_parameter_model(self) -> None:
        declinations = np.linspace(-12.0, 24.0, 7)
        x = np.radians(declinations)
        corrections = 1.0 + 0.4 * x
        models = fit_correction_models(declinations, corrections)
        self.assertEqual(select_model(models), "1+a*delta_rad")

    def test_non_simple_shape_selects_no_model(self) -> None:
        declinations = np.linspace(-12.0, 24.0, 7)
        corrections = np.array((1.0, 1.2, 0.8, 1.3, 0.7, 1.4, 0.6))
        models = fit_correction_models(declinations, corrections)
        self.assertIsNone(select_model(models))


if __name__ == "__main__":
    unittest.main()
