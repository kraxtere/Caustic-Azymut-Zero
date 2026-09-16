import math
import unittest

import numpy as np

from solver.run_scalar_nx_svd import ALL_TERMS, BASIS_LEVELS, _residual


class ScalarNxSvdRunnerTests(unittest.TestCase):
    def test_basis_levels_are_nested_and_have_frozen_sizes(self) -> None:
        self.assertEqual([len(BASIS_LEVELS[name]) for name in BASIS_LEVELS], [3, 6, 10])
        self.assertEqual(tuple(BASIS_LEVELS["degree_3"]), ALL_TERMS)
        self.assertEqual(tuple(BASIS_LEVELS["degree_2"]), ALL_TERMS[:6])

    def test_fit_residual_uses_c3_scale_and_axis_limits(self) -> None:
        observables = np.array([
            math.log(12.0), math.log(18.0), 0.2, math.log(1.05), math.log(1.20)
        ])
        residual = _residual(observables, True, (10.0, 20.0))
        np.testing.assert_allclose(
            residual,
            [math.log(1.2), 0.0, 0.2, 0.0, math.log(1.20 / 1.10)],
        )


if __name__ == "__main__":
    unittest.main()
