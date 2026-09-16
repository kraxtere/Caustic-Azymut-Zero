"""Compare local Maxwell monopole, quadrupole and octupole sensitivities."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .scan_local_dipole_c3 import fit_group
from .scan_local_dipole_scale import _disk_shape
from .scan_luneburg import build_scan_groups
from .scan_maxwell_declination import build_declination_groups
from .validate_maxwell import DEFAULT_RESTARTS, DEFAULT_SEEDS, evaluate_maxwell
from .validate_maxwell_c2 import SAMPLE_IDS, SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG


DIPOLE_CENTRE = 0.20
STEP = 0.05
DECLINATIONS = (-23.44, 0.0, 23.44)
MODES = ("monopole_epsilon", "quadrupole_epsilon", "octupole_epsilon")
METRIC_NAMES = ("north_rms", "south_rms", "solstice_asymmetry", "diameter_cv", "mean_axis_ratio")


def _metrics(c3: dict[str, dict[str, object]], disks: list[dict[str, object]]) -> dict[str, float]:
    by_delta = {float(record["declination_deg"]): record["disk"] for record in disks}
    diameters = np.asarray([record["disk"]["mean_diameter_km"] for record in disks])
    return {
        "north_rms": float(c3["north_celestial_pole"]["rms_km"]),
        "south_rms": float(c3["south_celestial_pole"]["rms_km"]),
        "solstice_asymmetry": abs(math.log(by_delta[-23.44]["mean_diameter_km"] / by_delta[23.44]["mean_diameter_km"])),
        "diameter_cv": float(np.std(diameters) / np.mean(diameters)),
        "mean_axis_ratio": float(np.mean([record["disk"]["axis_ratio"] for record in disks])),
    }


def _log_sensitivity(minus: dict[str, float], plus: dict[str, float]) -> dict[str, float]:
    return {name: (math.log(plus[name]) - math.log(minus[name])) / (2.0 * STEP) for name in METRIC_NAMES}


def run(output: Path) -> dict[str, object]:
    _, pole_groups = build_scan_groups(2.0, DEFAULT_SOLAR_RADIUS_DEG)
    pole_groups = {group.target_id: group for group in pole_groups}
    design = {float(delta): item for delta, item in build_declination_groups() if float(delta) in DECLINATIONS}
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    pole_seeds = {
        name: evaluate_maxwell(group, SELECTED_RADIUS_KM, centre, DEFAULT_SEEDS, DEFAULT_RESTARTS)
        for name, group in pole_groups.items()
    }
    disk_seeds = {
        (delta, sample): evaluate_maxwell(design[delta]["groups"][sample], SELECTED_RADIUS_KM, centre, DEFAULT_SEEDS, DEFAULT_RESTARTS)
        for delta in DECLINATIONS for sample in SAMPLE_IDS
    }

    def evaluate(dipole: float, mode: str | None = None, amplitude: float = 0.0) -> dict[str, object]:
        extra = {mode: amplitude} if mode else None
        c3 = {
            name: fit_group(group, dipole, pole_seeds[name], extra)
            for name, group in pole_groups.items()
        }
        disks = []
        for delta in DECLINATIONS:
            targets = {
                sample: fit_group(design[delta]["groups"][sample], dipole, disk_seeds[(delta, sample)], extra)
                for sample in SAMPLE_IDS
            }
            disks.append({"declination_deg": delta, "disk": _disk_shape(targets), "targets": targets})
        metrics = _metrics(c3, disks)
        consensus = all(target["restart_consensus"] for target in c3.values()) and all(
            target["restart_consensus"] for record in disks for target in record["targets"].values()
        )
        return {"dipole_epsilon": dipole, "mode": mode, "amplitude": amplitude, "metrics": metrics, "restart_consensus_all_targets": consensus}

    dipole_minus = evaluate(DIPOLE_CENTRE - STEP)
    dipole_plus = evaluate(DIPOLE_CENTRE + STEP)
    dipole_vector_map = _log_sensitivity(dipole_minus["metrics"], dipole_plus["metrics"])
    dipole_vector = np.array([dipole_vector_map[name] for name in METRIC_NAMES])
    records = []
    for mode in MODES:
        minus = evaluate(DIPOLE_CENTRE, mode, -STEP)
        plus = evaluate(DIPOLE_CENTRE, mode, STEP)
        sensitivity = _log_sensitivity(minus["metrics"], plus["metrics"])
        vector = np.array([sensitivity[name] for name in METRIC_NAMES])
        cosine = float(np.dot(vector, dipole_vector) / (np.linalg.norm(vector) * np.linalg.norm(dipole_vector)))
        orientation = -1.0 if sensitivity["solstice_asymmetry"] > 0.0 else 1.0
        oriented = {name: orientation * value for name, value in sensitivity.items()}
        useful = all(oriented[name] < 0.0 for name in ("solstice_asymmetry", "diameter_cv", "mean_axis_ratio"))
        records.append({
            "mode": mode,
            "minus": minus,
            "plus": plus,
            "log_sensitivity": sensitivity,
            "preferred_orientation": orientation,
            "oriented_log_sensitivity": oriented,
            "absolute_cosine_with_dipole": abs(cosine),
            "useful_for_scale_and_shape": useful,
        })
        print(f"{mode}: useful={useful} |cos|={abs(cosine):.6f}", flush=True)
    useful_records = [record for record in records if record["useful_for_scale_and_shape"]]
    selected = min(useful_records, key=lambda record: record["absolute_cosine_with_dipole"])["mode"] if useful_records else None
    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_LOCAL_MULTIPOLE_SENSITIVITY.md",
        "design": {"dipole_centre": DIPOLE_CENTRE, "step": STEP, "declinations_deg": list(DECLINATIONS), "modes": list(MODES)},
        "dipole_reference": {"minus": dipole_minus, "plus": dipole_plus, "log_sensitivity": dipole_vector_map},
        "records": records,
        "selected_mode_for_2d_scan": selected,
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
    print(f"Selected: {payload['selected_mode_for_2d_scan']}")


if __name__ == "__main__":
    main()
