from __future__ import annotations

import unittest

from solver.field_lens import LensFieldParams
from solver.validate_lens import validate_lens_candidate


class LensValidationAdapterTests(unittest.TestCase):
    def test_maxwell_cannot_run_without_declared_mirror_boundary(self) -> None:
        params = LensFieldParams(family="maxwell", radius_km=100.0)
        with self.assertRaisesRegex(ValueError, "mirror boundary"):
            validate_lens_candidate(params)


if __name__ == "__main__":
    unittest.main()
