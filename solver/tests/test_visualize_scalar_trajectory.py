import json
import tempfile
import unittest
from pathlib import Path

from solver.visualize_scalar_trajectory import SAMPLE_IDS, _candidate_path, build_payload, load_frames, run


class ScalarTrajectoryTests(unittest.TestCase):
    def test_loads_candidate_checkpoints_and_computes_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for declination in (-23.44, -11.72, 11.72, 23.44):
                points = {
                    "centre": [declination, 0.0, 10.0],
                    "north_limb": [declination, 2.0, 10.0],
                    "south_limb": [declination, -2.0, 10.0],
                    "east_limb": [declination + 3.0, 0.0, 10.0],
                    "west_limb": [declination - 3.0, 0.0, 10.0],
                }
                for sample_id in SAMPLE_IDS:
                    path = _candidate_path(root, 0.4, "degree_3", declination, sample_id)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps({
                        "source_km": points[sample_id],
                        "alphas_rad": [1.0],
                        "rms_km": 12.5,
                        "iterations": 3,
                        "converged": True,
                    }), encoding="utf-8")
            frames = load_frames(root)
            self.assertEqual(len(frames), 4)
            self.assertAlmostEqual(frames[0]["shape"]["mean_diameter_km"], 5.0)
            self.assertAlmostEqual(frames[0]["shape"]["axis_ratio"], 1.5)
            payload = build_payload(frames, 0.4, "degree_3")
            self.assertEqual(payload["frame_count"], 4)
            self.assertEqual(len(payload["centre_step_distances_km"]), 3)
            html = root / "trajectory.html"
            data = root / "trajectory.json"
            run(root, html, data)
            self.assertIn("interpolacja wizualna", html.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(data.read_text(encoding="utf-8"))["frame_count"], 4)


if __name__ == "__main__":
    unittest.main()
