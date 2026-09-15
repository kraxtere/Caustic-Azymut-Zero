from __future__ import annotations

import argparse
import unittest

from solver.scan_maxwell import (
    DEFAULT_Z0_FRACTIONS,
    build_z0_candidates,
    parse_float_list,
)
from solver.validate_maxwell import DEFAULT_RADIUS_KM


class MaxwellZ0ScanDesignTests(unittest.TestCase):
    def test_nonzero_offsets_precede_zero_control(self) -> None:
        candidates = build_z0_candidates()
        self.assertEqual(len(candidates), 7)
        self.assertTrue(all(value != 0.0 for value in candidates[:-1]))
        self.assertEqual(candidates[-1], 0.0)
        self.assertTrue(any(value < 0.0 for value in candidates))
        self.assertTrue(any(value > 0.0 for value in candidates))
        self.assertTrue(
            all(abs(value) <= 0.40 * DEFAULT_RADIUS_KM for value in candidates)
        )

    def test_pre_registered_grid_cannot_be_changed(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be changed"):
            build_z0_candidates(fractions=(-0.2, 0.0, 0.2))
        expected = tuple(DEFAULT_RADIUS_KM * value for value in DEFAULT_Z0_FRACTIONS)
        self.assertEqual(build_z0_candidates(), expected)

    def test_float_parser_rejects_duplicates(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_float_list("-0.1,-0.1,0")


if __name__ == "__main__":
    unittest.main()
