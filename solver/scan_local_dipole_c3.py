"""Run the preregistered epsilon-only C-3 scan for the local Maxwell dipole."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from .field_lens import LensFieldParams
from .maxwell_mirror import maxwell_direction_to_auxiliary_target
from .maxwell_numeric import LocalMaxwellCurve, build_local_maxwell_curve
from .scan_luneburg import build_scan_groups
from .validate_maxwell import DEFAULT_RESTARTS, DEFAULT_SEEDS, evaluate_maxwell
from .validate_maxwell_c2 import SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG, TargetGroup


EPSILON_GRID = (-0.40, -0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.40)
ALPHA_MARGIN = 1e-4
CONSENSUS_FRACTION = 1e-6
MINIMUM_POLE_SEPARATION_FRACTION = 1e-3
START_SEEDS = (3, 17, 91, 2048, 4099, 8209, 16411)


def _curve_point(curve: LocalMaxwellCurve, alpha: float) -> np.ndarray:
    return curve.state_at_angle(alpha)[0]


def _closest_alpha(
    curve: LocalMaxwellCurve,
    grid: np.ndarray,
    sampled_points: np.ndarray,
    point: np.ndarray,
) -> float:
    squared = np.sum((sampled_points - point) ** 2, axis=1)
    index = int(np.argmin(squared))
    low = grid[max(0, index - 1)]
    high = grid[min(len(grid) - 1, index + 1)]
    result = minimize_scalar(
        lambda alpha: float(np.sum((_curve_point(curve, alpha) - point) ** 2)),
        bounds=(low, high),
        method="bounded",
        options={"xatol": 1e-10},
    )
    return float(result.x)


def _fit_from_start(
    curves: tuple[LocalMaxwellCurve, ...],
    grid: np.ndarray,
    sampled_curves: tuple[np.ndarray, ...],
    initial_alphas: np.ndarray,
    radius: float,
) -> dict[str, object]:
    alphas = np.clip(initial_alphas, ALPHA_MARGIN, math.pi - ALPHA_MARGIN)
    points = np.array([_curve_point(curve, alpha) for curve, alpha in zip(curves, alphas)])
    source = np.mean(points, axis=0)
    converged = False
    for iteration in range(30):
        alphas = np.array(
            [
                _closest_alpha(curve, grid, samples, source)
                for curve, samples in zip(curves, sampled_curves, strict=True)
            ]
        )
        points = np.array(
            [_curve_point(curve, alpha) for curve, alpha in zip(curves, alphas)]
        )
        updated = np.mean(points, axis=0)
        if float(np.linalg.norm(updated - source)) <= 1e-7 * radius:
            source = updated
            converged = True
            break
        source = updated
    residuals = np.linalg.norm(points - source, axis=1)
    return {
        "source_km": source,
        "alphas_rad": alphas,
        "rms_km": float(math.sqrt(np.mean(residuals**2))),
        "iterations": iteration + 1,
        "converged": converged,
    }


def fit_group(
    group: TargetGroup,
    epsilon: float,
    analytic_seed: dict[str, object],
    additional_amplitudes: dict[str, float] | None = None,
) -> dict[str, object]:
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    params = LensFieldParams(
        "maxwell",
        SELECTED_RADIUS_KM,
        centre_km=tuple(centre),
        dipole_epsilon=epsilon,
        **(additional_amplitudes or {}),
    )
    curves = tuple(
        build_local_maxwell_curve(origin, direction, params)
        for origin, direction in zip(group.origins, group.directions, strict=True)
    )
    grid = np.linspace(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, 129)
    sampled_curves = tuple(
        np.array([_curve_point(curve, alpha) for alpha in grid]) for curve in curves
    )
    target = np.asarray(analytic_seed["common_point_s3_km"], dtype=float)
    parities = analytic_seed["selected_reflection_parities"]
    warm_alphas = np.array(
        [
            maxwell_direction_to_auxiliary_target(
                origin,
                target,
                SELECTED_RADIUS_KM,
                reflected_branch=bool(reflected),
                centre_xyz=centre,
            )[1]
            for origin, reflected in zip(group.origins, parities, strict=True)
        ]
    )
    starts = [warm_alphas]
    for index, seed in enumerate(START_SEEDS):
        rng = np.random.default_rng(seed)
        if index < 4:
            scale = (0.02, 0.05, 0.10, 0.20)[index]
            starts.append(warm_alphas + rng.normal(0.0, scale, len(warm_alphas)))
        else:
            starts.append(rng.uniform(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, len(warm_alphas)))
    runs = tuple(
        _fit_from_start(
            curves, grid, sampled_curves, start, SELECTED_RADIUS_KM
        )
        for start in starts
    )
    best = min(runs, key=lambda run: run["rms_km"])
    best_squared = float(best["rms_km"]) ** 2
    competitive = [
        run
        for run in runs
        if float(run["rms_km"]) ** 2
        <= best_squared + max(0.01 * best_squared, 1e-12 * SELECTED_RADIUS_KM**2)
    ]
    spread = max(
        (
            float(np.linalg.norm(first["source_km"] - second["source_km"]))
            for i, first in enumerate(competitive)
            for second in competitive[i + 1 :]
        ),
        default=0.0,
    )
    source = np.asarray(best["source_km"])
    return {
        "target_id": group.target_id,
        "rms_km": best["rms_km"],
        "source_km": source.tolist(),
        "inside_mirror": bool(np.linalg.norm(source - centre) < SELECTED_RADIUS_KM),
        "source_above_map": bool(source[2] >= -1e-6),
        "minimum_alpha_margin_rad": float(
            min(np.min(best["alphas_rad"]), np.min(math.pi - best["alphas_rad"]))
        ),
        "restart_consensus": spread <= CONSENSUS_FRACTION * SELECTED_RADIUS_KM,
        "competitive_run_count": len(competitive),
        "maximum_competitive_source_spread_km": spread,
        "all_runs_converged": all(bool(run["converged"]) for run in runs),
        "runs": [
            {
                "rms_km": run["rms_km"],
                "source_km": np.asarray(run["source_km"]).tolist(),
                "iterations": run["iterations"],
                "converged": run["converged"],
            }
            for run in runs
        ],
    }


def run(output: Path) -> dict[str, object]:
    _, groups = build_scan_groups(2.0, DEFAULT_SOLAR_RADIUS_DEG)
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    analytic_seeds = {
        group.target_id: evaluate_maxwell(
            group, SELECTED_RADIUS_KM, centre, DEFAULT_SEEDS, DEFAULT_RESTARTS
        )
        for group in groups
    }
    records = []
    for epsilon in EPSILON_GRID:
        targets = {
            group.target_id: fit_group(group, epsilon, analytic_seeds[group.target_id])
            for group in groups
        }
        records.append({"epsilon": epsilon, "targets": targets})
        print(f"epsilon={epsilon:+.2f} complete")
    control = next(record for record in records if record["epsilon"] == 0.0)
    for record in records:
        targets = record["targets"]
        north = targets["north_celestial_pole"]
        south = targets["south_celestial_pole"]
        separation = float(
            np.linalg.norm(np.asarray(north["source_km"]) - np.asarray(south["source_km"]))
        )
        checks = {
            "both_poles_beat_epsilon_zero": bool(
                record["epsilon"] != 0.0
                and north["rms_km"] < control["targets"]["north_celestial_pole"]["rms_km"]
                and south["rms_km"] < control["targets"]["south_celestial_pole"]["rms_km"]
            ),
            "restart_consensus_both_poles": bool(
                north["restart_consensus"] and south["restart_consensus"]
            ),
            "sources_inside_mirror_and_above_map": bool(
                north["inside_mirror"] and south["inside_mirror"]
                and north["source_above_map"] and south["source_above_map"]
            ),
            "poles_not_collapsed": separation >= MINIMUM_POLE_SEPARATION_FRACTION * SELECTED_RADIUS_KM,
            "alpha_margin_both_poles": bool(
                north["minimum_alpha_margin_rad"] >= ALPHA_MARGIN
                and south["minimum_alpha_margin_rad"] >= ALPHA_MARGIN
            ),
        }
        record["pole_separation_km"] = separation
        record["gate"] = {"passed": all(checks.values()), "checks": checks}
    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_LOCAL_DIPOLE_C3_SCAN.md",
        "epsilon_grid": list(EPSILON_GRID),
        "records": records,
        "passing_epsilons": [record["epsilon"] for record in records if record["gate"]["passed"]],
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
