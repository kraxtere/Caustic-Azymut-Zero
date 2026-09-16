import unittest

from solver.scan_local_dipole_scale import _scale_metrics


class LocalDipoleScaleTests(unittest.TestCase):
    def test_scale_metrics_are_zero_for_constant_diameter(self) -> None:
        records = [
            {"declination_deg": delta, "disk": {"mean_diameter_km": 10.0}}
            for delta in (-23.44, -11.72, 0.0, 11.72, 23.44)
        ]
        metrics = _scale_metrics(records)
        self.assertEqual(metrics["diameter_coefficient_of_variation"], 0.0)
        self.assertEqual(metrics["absolute_log_asymmetry_11_72"], 0.0)
        self.assertEqual(metrics["absolute_log_asymmetry_23_44"], 0.0)

    def test_scale_metrics_detect_pair_asymmetry(self) -> None:
        records = [
            {"declination_deg": delta, "disk": {"mean_diameter_km": diameter}}
            for delta, diameter in ((-23.44, 12.0), (-11.72, 11.0), (0.0, 10.0), (11.72, 9.0), (23.44, 8.0))
        ]
        metrics = _scale_metrics(records)
        self.assertGreater(metrics["diameter_coefficient_of_variation"], 0.0)
        self.assertGreater(metrics["absolute_log_asymmetry_11_72"], 0.0)
        self.assertGreater(metrics["absolute_log_asymmetry_23_44"], 0.0)


if __name__ == "__main__":
    unittest.main()
