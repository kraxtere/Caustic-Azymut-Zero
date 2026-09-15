"""Identify odd Maxwell scale response on one forced-direct observer cohort."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .analyze_maxwell_branch_geometry import legendre_modes
from .continue_maxwell_branches import evaluate_fixed_branches
from .scan_maxwell_declination import build_declination_groups
from .validate_maxwell_c2 import (
    SAMPLE_IDS,
    SELECTED_CENTRE_Z_KM,
    SELECTED_RADIUS_KM,
    _disk_shape,
)
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG


PREDICTION_TOLERANCE = math.log(1.02)


def _shape(targets: dict[str, dict[str, object]]) -> dict[str, float] | None:
    compatible = {
        name: {
            "valid": bool(targets[name].get("fit_valid")),
            "common_point_km": targets[name].get("common_point_km"),
        }
        for name in SAMPLE_IDS
    }
    return _disk_shape(compatible)


def identify(records: list[dict[str, object]]) -> dict[str, object]:
    by_delta = {float(record["declination_deg"]): record for record in records}
    scale_zero = float(by_delta[0.0]["transfer_scale_km_per_radian"])
    for record in records:
        scale = float(record["transfer_scale_km_per_radian"])
        record["correction_c"] = scale_zero / scale
        record["log_correction"] = math.log(scale_zero / scale)

    pairs = []
    for positive in (5.86, 11.72, 17.58, 23.44):
        plus = float(by_delta[positive]["log_correction"])
        minus = float(by_delta[-positive]["log_correction"])
        odd = (plus - minus) / 2.0
        even = (plus + minus) / 2.0
        modes = legendre_modes(positive)
        pairs.append(
            {
                "absolute_declination_deg": positive,
                "odd_log_response": odd,
                "even_log_response": even,
                "p1": modes["p1"],
                "p3": modes["p3"],
            }
        )
    pair_map = {pair["absolute_declination_deg"]: pair for pair in pairs}

    solstice = pair_map[23.44]
    dipole_a = solstice["odd_log_response"] / solstice["p1"]
    dipole_predictions = {
        str(pair["absolute_declination_deg"]): dipole_a * pair["p1"]
        for pair in pairs
    }
    intermediate_error = (
        dipole_predictions["11.72"] - pair_map[11.72]["odd_log_response"]
    )
    dipole_passed = abs(intermediate_error) <= PREDICTION_TOLERANCE

    identification = (pair_map[11.72], pair_map[23.44])
    matrix = np.array([[pair["p1"], pair["p3"]] for pair in identification])
    target = np.array([pair["odd_log_response"] for pair in identification])
    coefficient_p1, coefficient_p3 = np.linalg.solve(matrix, target)
    holdout_errors = {}
    for declination in (5.86, 17.58):
        pair = pair_map[declination]
        prediction = coefficient_p1 * pair["p1"] + coefficient_p3 * pair["p3"]
        holdout_errors[str(declination)] = prediction - pair["odd_log_response"]
    p1_p3_passed = max(map(abs, holdout_errors.values())) <= PREDICTION_TOLERANCE

    return {
        "records": records,
        "parity_pairs": pairs,
        "tolerance": {
            "maximum_absolute_log_error": PREDICTION_TOLERANCE,
            "equivalent_multiplicative_error": 1.02,
        },
        "dipole_only": {
            "coefficient_p1": dipole_a,
            "fit_pair_absolute_declination_deg": 23.44,
            "prediction_pair_absolute_declination_deg": 11.72,
            "intermediate_prediction_error": intermediate_error,
            "passed": dipole_passed,
            "predictions": dipole_predictions,
        },
        "dipole_plus_octupole": {
            "coefficient_p1": float(coefficient_p1),
            "coefficient_p3": float(coefficient_p3),
            "identification_pairs_absolute_declination_deg": [11.72, 23.44],
            "holdout_pairs_absolute_declination_deg": [5.86, 17.58],
            "holdout_errors": holdout_errors,
            "passed": p1_p3_passed,
        },
        "selected_response_basis": (
            "P1" if dipole_passed else "P1+P3" if p1_p3_passed else None
        ),
    }


def run(output: Path) -> dict[str, object]:
    design = build_declination_groups()
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    records = []
    for declination, item in design:
        targets = {
            sample_id: evaluate_fixed_branches(
                item["groups"][sample_id],
                SELECTED_RADIUS_KM,
                centre,
                (False,) * len(item["groups"][sample_id].origins),
            )
            for sample_id in SAMPLE_IDS
        }
        shape = _shape(targets)
        if shape is None:
            raise ValueError(f"forced-direct disk failed at {declination}")
        scale = shape["mean_diameter_km"] / (
            2.0 * math.radians(DEFAULT_SOLAR_RADIUS_DEG)
        )
        records.append(
            {
                "declination_deg": declination,
                "observer_count": len(item["observer_coordinates_deg"]),
                "mean_diameter_km": shape["mean_diameter_km"],
                "transfer_scale_km_per_radian": scale,
                "all_targets_physically_admissible": all(
                    bool(target["physically_admissible"])
                    for target in targets.values()
                ),
                "minimum_forward_sine": min(
                    float(target["minimum_forward_sine"])
                    for target in targets.values()
                ),
            }
        )
    result = identify(records)
    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_MAXWELL_RESPONSE_IDENTIFICATION.md",
        "design": {
            "radius_km": SELECTED_RADIUS_KM,
            "centre_z_km": SELECTED_CENTRE_Z_KM,
            "branch": "forced-direct P",
            "common_observer_count": records[0]["observer_count"],
            "input_angular_radius_deg": DEFAULT_SOLAR_RADIUS_DEG,
            "field_modified": False,
        },
        **result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.output)
    print(f"Wybrana baza odpowiedzi: {payload['selected_response_basis']}")
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
