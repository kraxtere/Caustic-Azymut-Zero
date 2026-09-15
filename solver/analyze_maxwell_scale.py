"""Analyse Maxwell branch side and simple residual scale corrections."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Callable, Sequence

import numpy as np


STABLE_MIN_DECLINATION_DEG = -11.72
MAXIMUM_ACCEPTABLE_RMSE = 0.01
MAXIMUM_ACCEPTABLE_ABSOLUTE_ERROR = 0.02


def residual_correction(
    declinations_deg: Sequence[float],
    transfer_scales: Sequence[float],
) -> np.ndarray:
    declinations = np.asarray(declinations_deg, dtype=float)
    scales = np.asarray(transfer_scales, dtype=float)
    zero = np.flatnonzero(np.isclose(declinations, 0.0, atol=1e-12))
    if len(zero) != 1 or np.any(scales <= 0.0):
        raise ValueError("data need one zero declination and positive scales")
    return scales[zero[0]] / scales


def _fit_one_parameter(
    basis: np.ndarray,
    target: np.ndarray,
) -> float:
    denominator = float(np.dot(basis, basis))
    if denominator == 0.0:
        raise ValueError("fit basis cannot be zero")
    return float(np.dot(basis, target) / denominator)


def fit_correction_models(
    declinations_deg: Sequence[float],
    corrections: Sequence[float],
) -> list[dict[str, object]]:
    x = np.radians(np.asarray(declinations_deg, dtype=float))
    observed = np.asarray(corrections, dtype=float)
    if x.shape != observed.shape or len(x) < 4:
        raise ValueError("declinations and corrections need equal length >= 4")

    models: list[tuple[str, int, Callable[[], tuple[np.ndarray, list[float]]]]] = []

    def linear_delta() -> tuple[np.ndarray, list[float]]:
        coefficient = _fit_one_parameter(x, observed - 1.0)
        return 1.0 + coefficient * x, [coefficient]

    def linear_sine() -> tuple[np.ndarray, list[float]]:
        basis = np.sin(x)
        coefficient = _fit_one_parameter(basis, observed - 1.0)
        return 1.0 + coefficient * basis, [coefficient]

    def quadratic_delta() -> tuple[np.ndarray, list[float]]:
        matrix = np.column_stack((x, x**2))
        coefficients, *_ = np.linalg.lstsq(matrix, observed - 1.0, rcond=None)
        return 1.0 + matrix @ coefficients, coefficients.tolist()

    def exponential_delta() -> tuple[np.ndarray, list[float]]:
        coefficient = _fit_one_parameter(x, np.log(observed))
        return np.exp(coefficient * x), [coefficient]

    models.extend(
        [
            ("1+a*delta_rad", 1, linear_delta),
            ("1+a*sin(delta)", 1, linear_sine),
            ("1+a*delta_rad+b*delta_rad^2", 2, quadratic_delta),
            ("exp(a*delta_rad)", 1, exponential_delta),
        ]
    )
    results = []
    for name, parameter_count, fitter in models:
        predicted, coefficients = fitter()
        residuals = predicted - observed
        rmse = float(math.sqrt(np.mean(residuals**2)))
        maximum_error = float(np.max(np.abs(residuals)))
        results.append(
            {
                "model": name,
                "parameter_count": parameter_count,
                "coefficients": coefficients,
                "rmse": rmse,
                "maximum_absolute_error": maximum_error,
                "acceptable": bool(
                    rmse <= MAXIMUM_ACCEPTABLE_RMSE
                    and maximum_error <= MAXIMUM_ACCEPTABLE_ABSOLUTE_ERROR
                ),
                "predicted_corrections": predicted.tolist(),
                "residuals": residuals.tolist(),
            }
        )
    return results


def select_model(models: Sequence[dict[str, object]]) -> str | None:
    acceptable = [model for model in models if model["acceptable"]]
    if not acceptable:
        return None
    selected = min(
        acceptable,
        key=lambda model: (model["parameter_count"], model["rmse"]),
    )
    return str(selected["model"])


def _branch_counts(targets: dict[str, dict[str, object]]) -> list[int]:
    return [int(target["selected_reflected_branch_count"]) for target in targets.values()]


def analyse(
    corrected_c2_path: Path,
    declination_scan_path: Path,
) -> dict[str, object]:
    corrected = json.loads(corrected_c2_path.read_text(encoding="utf-8"))
    scan = json.loads(declination_scan_path.read_text(encoding="utf-8"))
    december = next(
        track
        for track in corrected["candidate"]["solar_disk_c2"]["daily_tracks"]
        if track["track_id"] == "december_solstice"
    )
    december_records = []
    for moment in december["moments"]:
        targets = moment["targets"]
        december_records.append(
            {
                "timestamp_utc": moment["timestamp_utc"],
                "reflected_branch_counts": _branch_counts(targets),
                "all_targets_same_count": len(set(_branch_counts(targets))) == 1,
                "all_branch_assignments_agree_across_seeds": all(
                    target["restart_branch_assignment_consensus"]
                    for target in targets.values()
                ),
            }
        )

    scan_by_delta = {record["declination_deg"]: record for record in scan["records"]}
    branch_reference = {}
    for declination in (-23.44, -17.58, -11.72):
        record = scan_by_delta[declination]
        branch_reference[str(declination)] = {
            "valid": record["valid"],
            "reflected_branch_counts": _branch_counts(record["targets"]),
            "all_branch_assignments_agree": record["all_branch_assignments_agree"],
        }
    december_on_reflected_side = bool(
        all(record["all_targets_same_count"] for record in december_records)
        and all(
            record["all_branch_assignments_agree_across_seeds"]
            for record in december_records
        )
        and all(
            min(record["reflected_branch_counts"]) > 0
            for record in december_records
        )
        and min(branch_reference["-23.44"]["reflected_branch_counts"]) > 0
        and max(branch_reference["-11.72"]["reflected_branch_counts"]) == 0
    )

    stable = [
        record
        for record in scan["records"]
        if record["valid"]
        and record["declination_deg"] >= STABLE_MIN_DECLINATION_DEG
    ]
    declinations = [record["declination_deg"] for record in stable]
    scales = [record["normalised_transfer_scale_km_per_radian"] for record in stable]
    corrections = residual_correction(declinations, scales)
    models = fit_correction_models(declinations, corrections)
    return {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_MAXWELL_SCALE_CORRECTION.md",
        "branch_side": {
            "observer_cohorts_identical": False,
            "comparison_level": "topology (stable reflected versus stable direct)",
            "declination_reference": branch_reference,
            "december_moments": december_records,
            "december_on_same_reflected_side_as_minus_23_44": (
                december_on_reflected_side
            ),
        },
        "stable_scale_correction": {
            "declinations_deg": declinations,
            "transfer_scales_km_per_radian": scales,
            "correction_definition": "C(delta)=S(0)/S(delta)",
            "corrections": corrections.tolist(),
            "model_acceptance": {
                "maximum_rmse": MAXIMUM_ACCEPTABLE_RMSE,
                "maximum_absolute_error": MAXIMUM_ACCEPTABLE_ABSOLUTE_ERROR,
                "selection": "fewest parameters, then lowest RMSE",
            },
            "models": models,
            "selected_simple_model": select_model(models),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corrected-c2", required=True, type=Path)
    parser.add_argument("--declination-scan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = analyse(args.corrected_c2, args.declination_scan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "Grudzien po odbitej stronie: "
        f"{payload['branch_side']['december_on_same_reflected_side_as_minus_23_44']}"
    )
    print(
        "Wybrany prosty model: "
        f"{payload['stable_scale_correction']['selected_simple_model']}"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
