"""Run the preregistered cheap scale gate for local Maxwell dipole candidates."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .scan_local_dipole_c3 import ALPHA_MARGIN, fit_group
from .scan_maxwell_declination import build_declination_groups
from .validate_maxwell import DEFAULT_RESTARTS, DEFAULT_SEEDS, evaluate_maxwell
from .validate_maxwell_c2 import SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG


EPSILONS = (0.0, 0.10, 0.20, 0.40)
DECLINATIONS_DEG = (-23.44, -11.72, 0.0, 11.72, 23.44)
SAMPLE_IDS = ("centre", "north_limb", "south_limb", "east_limb", "west_limb")
MAXIMUM_AXIS_RATIO = 1.10
MAXIMUM_NORMALISED_CENTRE_OFFSET = 0.05


def _disk_shape(targets: dict[str, dict[str, object]]) -> dict[str, float]:
    points = {name: np.asarray(targets[name]["source_km"], dtype=float) for name in SAMPLE_IDS}
    north_south = float(np.linalg.norm(points["north_limb"] - points["south_limb"]))
    east_west = float(np.linalg.norm(points["east_limb"] - points["west_limb"]))
    mean = (north_south + east_west) / 2.0
    centroid = np.mean([points[name] for name in SAMPLE_IDS[1:]], axis=0)
    offset = float(np.linalg.norm(points["centre"] - centroid))
    return {
        "north_south_diameter_km": north_south,
        "east_west_diameter_km": east_west,
        "mean_diameter_km": mean,
        "axis_ratio": max(north_south, east_west) / min(north_south, east_west),
        "normalised_centre_offset": offset / mean,
    }


def _scale_metrics(records: list[dict[str, object]]) -> dict[str, float]:
    by_delta = {float(record["declination_deg"]): record for record in records}
    diameters = np.asarray([record["disk"]["mean_diameter_km"] for record in records])
    return {
        "diameter_coefficient_of_variation": float(np.std(diameters) / np.mean(diameters)),
        "absolute_log_asymmetry_11_72": abs(math.log(
            by_delta[-11.72]["disk"]["mean_diameter_km"]
            / by_delta[11.72]["disk"]["mean_diameter_km"]
        )),
        "absolute_log_asymmetry_23_44": abs(math.log(
            by_delta[-23.44]["disk"]["mean_diameter_km"]
            / by_delta[23.44]["disk"]["mean_diameter_km"]
        )),
    }


def run(output: Path) -> dict[str, object]:
    design = {
        float(delta): item
        for delta, item in build_declination_groups(DEFAULT_SOLAR_RADIUS_DEG)
        if float(delta) in DECLINATIONS_DEG
    }
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    seeds = {
        (delta, sample_id): evaluate_maxwell(
            design[delta]["groups"][sample_id],
            SELECTED_RADIUS_KM,
            centre,
            DEFAULT_SEEDS,
            DEFAULT_RESTARTS,
        )
        for delta in DECLINATIONS_DEG
        for sample_id in SAMPLE_IDS
    }
    candidates = []
    for epsilon in EPSILONS:
        records = []
        for delta in DECLINATIONS_DEG:
            targets = {
                sample_id: fit_group(
                    design[delta]["groups"][sample_id],
                    epsilon,
                    seeds[(delta, sample_id)],
                )
                for sample_id in SAMPLE_IDS
            }
            records.append({
                "declination_deg": delta,
                "observer_count": len(design[delta]["observer_coordinates_deg"]),
                "targets": targets,
                "disk": _disk_shape(targets),
            })
            print(f"epsilon={epsilon:+.2f} delta={delta:+.2f} complete", flush=True)
        candidates.append({"epsilon": epsilon, "records": records, "scale_metrics": _scale_metrics(records)})

    control = candidates[0]
    for candidate in candidates:
        records = candidate["records"]
        targets = [target for record in records for target in record["targets"].values()]
        disks = [record["disk"] for record in records]
        metrics = candidate["scale_metrics"]
        checks = {
            "all_three_scale_metrics_beat_epsilon_zero": bool(
                candidate["epsilon"] != 0.0
                and all(metrics[name] < control["scale_metrics"][name] for name in metrics)
            ),
            "restart_consensus_all_targets": all(bool(target["restart_consensus"]) for target in targets),
            "all_sources_inside_mirror_and_above_map": all(
                bool(target["inside_mirror"] and target["source_above_map"]) for target in targets
            ),
            "alpha_margin_all_targets": all(
                float(target["minimum_alpha_margin_rad"]) >= ALPHA_MARGIN for target in targets
            ),
            "disk_shape_within_full_c2_limits": all(
                float(disk["axis_ratio"]) <= MAXIMUM_AXIS_RATIO
                and float(disk["normalised_centre_offset"]) <= MAXIMUM_NORMALISED_CENTRE_OFFSET
                for disk in disks
            ),
        }
        candidate["gate"] = {"passed": all(checks.values()), "checks": checks}

    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_LOCAL_DIPOLE_SCALE_GATE.md",
        "design": {
            "epsilons": list(EPSILONS),
            "declinations_deg": list(DECLINATIONS_DEG),
            "input_angular_radius_deg": DEFAULT_SOLAR_RADIUS_DEG,
            "samples_per_declination": list(SAMPLE_IDS),
            "radius_km": SELECTED_RADIUS_KM,
            "centre_z_km": SELECTED_CENTRE_Z_KM,
        },
        "candidates": candidates,
        "passing_epsilons": [candidate["epsilon"] for candidate in candidates if candidate["gate"]["passed"]],
        "rule_frozen_before_run": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.output)
    print(f"PASS epsilon: {payload['passing_epsilons']}")


if __name__ == "__main__":
    main()
