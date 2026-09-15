"""Run the pre-registered centre/C-3 gate for the exact Maxwell mirror."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from .geometry_flat import R_MAP
from .maxwell_mirror import (
    MaxwellGreatCircleConstraint,
    maxwell_direction_to_auxiliary_target,
    maxwell_great_circle_constraint,
    solve_maxwell_mirror_branches,
)
from .raytrace import triangulate_half_lines_detailed
from .scan_luneburg import POLE_TARGETS, build_scan_groups
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG, TargetGroup


MODEL_STATUS = "v2-maxwell-cheap-gate-preregistered"
DEFAULT_RADIUS_KM = math.pi * R_MAP
DEFAULT_RESTARTS = 16
DEFAULT_SEEDS = (3, 17, 91, 2048)
CONSENSUS_FRACTION_OF_RADIUS = 1e-6
MINIMUM_POLE_SEPARATION_RAD = 1e-3
FORWARD_TOLERANCE = 1e-10
GROUND_TOLERANCE_KM = 1e-6


def parse_integer_list(value: str) -> tuple[int, ...]:
    try:
        values = tuple(int(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from error
    if not values or any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("seeds must be non-negative integers")
    if len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("seeds must be unique")
    return values


def _angle_deg(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    cosine = float(
        np.clip(
            np.dot(first, second)
            / (float(np.linalg.norm(first)) * float(np.linalg.norm(second))),
            -1.0,
            1.0,
        )
    )
    return math.degrees(math.acos(cosine))


def _direction_rms_deg(
    observed: Sequence[np.ndarray],
    predicted: Sequence[np.ndarray],
) -> tuple[float, list[float]]:
    residuals = [
        _angle_deg(first, second)
        for first, second in zip(observed, predicted, strict=True)
    ]
    return float(math.sqrt(np.mean(np.square(residuals)))), residuals


def evaluate_n_equals_one(group: TargetGroup) -> dict[str, object]:
    triangulation = triangulate_half_lines_detailed(
        group.origins,
        group.directions,
    )
    valid = bool(
        triangulation.matrix_rank >= 3
        and triangulation.condition_number <= 1e14
        and math.isfinite(triangulation.rms_km)
    )
    if not valid:
        return {
            "target_id": group.target_id,
            "timestamp_utc": group.timestamp_utc.isoformat(),
            "observer_count": len(group.origins),
            "valid": False,
        }
    predicted = [
        triangulation.point - origin
        for origin in group.origins
    ]
    direction_rms, residuals = _direction_rms_deg(group.directions, predicted)
    forward_distances = triangulation.forward_distances_km
    return {
        "target_id": group.target_id,
        "timestamp_utc": group.timestamp_utc.isoformat(),
        "observer_count": len(group.origins),
        "valid": True,
        "common_point_km": triangulation.point.tolist(),
        "native_line_rms_km": triangulation.rms_km,
        "direction_rms_deg": direction_rms,
        "maximum_direction_residual_deg": max(residuals),
        "minimum_forward_distance_km": float(np.min(forward_distances)),
        "all_rays_forward": bool(np.all(forward_distances >= -GROUND_TOLERANCE_KM)),
        "condition_number": triangulation.condition_number,
    }


def _maximum_pairwise_distance(points: Sequence[np.ndarray]) -> float:
    maximum = 0.0
    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            maximum = max(maximum, float(np.linalg.norm(first - second)))
    return maximum


def evaluate_maxwell(
    group: TargetGroup,
    radius_km: float,
    centre_km: np.ndarray,
    seeds: Sequence[int],
    restarts: int,
) -> dict[str, object]:
    try:
        constraints = tuple(
            maxwell_great_circle_constraint(
                origin,
                direction,
                radius_km,
                centre_km,
            )
            for origin, direction in zip(
                group.origins,
                group.directions,
                strict=True,
            )
        )
        searches = tuple(
            solve_maxwell_mirror_branches(
                constraints,
                restarts=restarts,
                seed=seed,
                centre_xyz=centre_km,
            )
            for seed in seeds
        )
    except (ValueError, np.linalg.LinAlgError) as error:
        return {
            "target_id": group.target_id,
            "timestamp_utc": group.timestamp_utc.isoformat(),
            "observer_count": len(group.origins),
            "valid": False,
            "failure": str(error),
        }

    seed_points = tuple(search.best.fit.point_xyzw for search in searches)
    maximum_seed_spread = _maximum_pairwise_distance(seed_points)
    consensus = maximum_seed_spread <= CONSENSUS_FRACTION_OF_RADIUS * radius_km
    seed_branch_assignments = tuple(
        search.best.reflection_parities for search in searches
    )
    branch_assignment_consensus = (
        len(set(seed_branch_assignments)) == 1
    )
    selected_search = min(
        searches,
        key=lambda search: search.best.fit.rms_plane_distance,
    )
    selected = selected_search.best
    fit = selected.fit
    predicted: list[np.ndarray] = []
    central_angles: list[float] = []
    signed_sines: list[float] = []
    for origin, constraint, reflected in zip(
        group.origins,
        constraints,
        selected.reflection_parities,
        strict=True,
    ):
        direction, angle = maxwell_direction_to_auxiliary_target(
            origin,
            fit.point_xyzw,
            radius_km,
            reflected_branch=reflected,
            centre_xyz=centre_km,
        )
        predicted.append(direction)
        central_angles.append(angle)
        target = fit.point_xyzw.copy()
        if reflected:
            target[3] *= -1.0
        signed_sines.append(
            float(np.dot(constraint.sphere_tangent, target) / radius_km)
        )

    direction_rms, residuals = _direction_rms_deg(group.directions, predicted)
    all_forward = bool(
        fit.forward_observation_count == fit.observation_count
        and all(value >= -FORWARD_TOLERANCE for value in signed_sines)
    )
    source_above_map = bool(fit.point_xyz[2] >= -GROUND_TOLERANCE_KM)
    valid = bool(
        consensus
        and fit.inside_mirror
        and source_above_map
        and all_forward
        and all(search.best.converged for search in searches)
    )
    return {
        "target_id": group.target_id,
        "timestamp_utc": group.timestamp_utc.isoformat(),
        "observer_count": len(group.origins),
        "valid": valid,
        "common_point_km": fit.point_xyz.tolist(),
        "common_point_s3_km": fit.point_xyzw.tolist(),
        "native_s3_plane_rms_km": fit.rms_plane_distance,
        "direction_rms_deg": direction_rms,
        "maximum_direction_residual_deg": max(residuals),
        "all_rays_forward": all_forward,
        "minimum_forward_sine": min(signed_sines),
        "minimum_central_angle_rad": min(central_angles),
        "maximum_central_angle_rad": max(central_angles),
        "inside_mirror": fit.inside_mirror,
        "source_above_map": source_above_map,
        "spectral_gap": float(fit.eigenvalues[1] - fit.eigenvalues[0]),
        "selected_seed": selected_search.seed,
        "selected_reflected_branch_count": sum(selected.reflection_parities),
        "restart_seed_consensus": consensus,
        "restart_branch_assignment_consensus": branch_assignment_consensus,
        "maximum_seed_point_spread_s3_km": maximum_seed_spread,
        "selected_reflection_parities": list(selected.reflection_parities),
        "seed_runs": [
            {
                "seed": search.seed,
                "best_native_s3_plane_rms_km": (
                    search.best.fit.rms_plane_distance
                ),
                "best_point_s3_km": search.best.fit.point_xyzw.tolist(),
                "best_reflected_branch_count": sum(
                    search.best.reflection_parities
                ),
                "best_reflection_parities": list(
                    search.best.reflection_parities
                ),
                "best_iterations": search.best.iterations,
                "all_runs_converged": all(run.converged for run in search.runs),
                "distinct_start_count": len(
                    {run.initial_reflection_parities for run in search.runs}
                ),
            }
            for search in searches
        ],
    }


def _summarise(
    groups: Sequence[TargetGroup],
    evaluator: Callable[[TargetGroup], dict[str, object]],
) -> dict[str, object]:
    targets = [evaluator(group) for group in groups]
    complete = all(bool(target["valid"]) for target in targets)
    residuals = [
        float(target["direction_rms_deg"])
        for target in targets
        if target.get("direction_rms_deg") is not None
    ]
    return {
        "target_count": len(targets),
        "valid_target_count": sum(bool(target["valid"]) for target in targets),
        "complete": complete,
        "mean_direction_rms_deg": (
            float(np.mean(residuals)) if complete else None
        ),
        "partial_mean_direction_rms_deg": (
            float(np.mean(residuals)) if residuals else None
        ),
        "targets": targets,
    }


def _pole_map(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    return {target["target_id"]: target for target in summary["targets"]}


def apply_maxwell_gate(
    candidate: dict[str, object],
    baseline: dict[str, object],
    radius_km: float,
) -> dict[str, object]:
    candidate_solar = candidate["solar_centres"]
    baseline_solar = baseline["solar_centres"]
    candidate_poles = _pole_map(candidate["celestial_poles"])
    baseline_poles = _pole_map(baseline["celestial_poles"])
    pole_points = [
        np.asarray(candidate_poles[target_id].get("common_point_s3_km"), dtype=float)
        for target_id in POLE_TARGETS
        if candidate_poles[target_id].get("common_point_s3_km") is not None
    ]
    pole_separation = None
    if len(pole_points) == 2:
        cosine = float(
            np.clip(np.dot(*pole_points) / radius_km**2, -1.0, 1.0)
        )
        pole_separation = math.acos(cosine)

    checks = {
        "complete_solar_centre_set": bool(candidate_solar["complete"]),
        "complete_celestial_poles": bool(candidate["celestial_poles"]["complete"]),
        "solar_mean_direction_rms_below_n_equals_1": bool(
            candidate_solar["complete"]
            and candidate_solar["mean_direction_rms_deg"]
            < baseline_solar["mean_direction_rms_deg"]
        ),
        "north_pole_direction_rms_below_n_equals_1": bool(
            candidate_poles["north_celestial_pole"].get("valid")
            and candidate_poles["north_celestial_pole"]["direction_rms_deg"]
            < baseline_poles["north_celestial_pole"]["direction_rms_deg"]
        ),
        "south_pole_direction_rms_below_n_equals_1": bool(
            candidate_poles["south_celestial_pole"].get("valid")
            and candidate_poles["south_celestial_pole"]["direction_rms_deg"]
            < baseline_poles["south_celestial_pole"]["direction_rms_deg"]
        ),
        "all_maxwell_rays_forward": all(
            bool(target.get("all_rays_forward"))
            for target in (
                *candidate_solar["targets"],
                *candidate["celestial_poles"]["targets"],
            )
        ),
        "all_restart_seeds_agree": all(
            bool(target.get("restart_seed_consensus"))
            for target in (
                *candidate_solar["targets"],
                *candidate["celestial_poles"]["targets"],
            )
        ),
        "sources_inside_mirror_and_above_map": all(
            bool(target.get("inside_mirror"))
            and bool(target.get("source_above_map"))
            for target in (
                *candidate_solar["targets"],
                *candidate["celestial_poles"]["targets"],
            )
        ),
        "celestial_poles_not_collapsed": bool(
            pole_separation is not None
            and pole_separation > MINIMUM_POLE_SEPARATION_RAD
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "pole_separation_rad": pole_separation,
        "minimum_pole_separation_rad": MINIMUM_POLE_SEPARATION_RAD,
        "rule_frozen_before_run": True,
    }


def validate_maxwell_gate(
    *,
    radius_km: float = DEFAULT_RADIUS_KM,
    centre_z_km: float = 0.0,
    restarts: int = DEFAULT_RESTARTS,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, object]:
    centre = np.array([0.0, 0.0, centre_z_km])
    solar_groups, pole_groups = build_scan_groups(
        minimum_altitude_deg,
        solar_radius_deg,
    )
    baseline = {
        "solar_centres": _summarise(solar_groups, evaluate_n_equals_one),
        "celestial_poles": _summarise(pole_groups, evaluate_n_equals_one),
    }
    evaluator = lambda group: evaluate_maxwell(
        group,
        radius_km,
        centre,
        seeds,
        restarts,
    )
    candidate = {
        "solar_centres": _summarise(solar_groups, evaluator),
        "celestial_poles": _summarise(pole_groups, evaluator),
    }
    gate = apply_maxwell_gate(candidate, baseline, radius_km)
    matches_pre_registered_candidate = bool(
        math.isclose(radius_km, DEFAULT_RADIUS_KM, rel_tol=0.0, abs_tol=1e-9)
        and math.isclose(centre_z_km, 0.0, rel_tol=0.0, abs_tol=1e-12)
        and restarts == DEFAULT_RESTARTS
        and tuple(seeds) == DEFAULT_SEEDS
        and math.isclose(
            minimum_altitude_deg,
            2.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            solar_radius_deg,
            DEFAULT_SOLAR_RADIUS_DEG,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    )
    gate["checks"] = {
        "matches_pre_registered_candidate": matches_pre_registered_candidate,
        **gate["checks"],
    }
    gate["passed"] = all(gate["checks"].values())
    return {
        "schema_version": 1,
        "model": "maxwell-mirror-v2-cheap-centre-c3-gate",
        "status": "completed",
        "validation_only": True,
        "pre_registered_contract": "docs/V2_MAXWELL_CHEAP_GATE.md",
        "matches_pre_registered_candidate": matches_pre_registered_candidate,
        "candidate": {
            "radius_km": radius_km,
            "centre_km": centre.tolist(),
            "first_central_angle_interval_rad": [0.0, math.pi],
        },
        "design": {
            "solar_centre_count": len(solar_groups),
            "pole_count": len(pole_groups),
            "full_solar_limb_c2_included": False,
            "restarts_per_seed": restarts,
            "seeds": list(seeds),
            "consensus_fraction_of_radius": CONSENSUS_FRACTION_OF_RADIUS,
            "minimum_pole_separation_rad": MINIMUM_POLE_SEPARATION_RAD,
            "comparison_metric": "RMS observed-vs-predicted direction in degrees",
        },
        "baseline_n_equals_1": baseline,
        "maxwell": candidate,
        "promotion_gate": gate,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius-km", type=float, default=DEFAULT_RADIUS_KM)
    parser.add_argument("--centre-z-km", type=float, default=0.0)
    parser.add_argument("--restarts", type=int, default=DEFAULT_RESTARTS)
    parser.add_argument("--seeds", type=parse_integer_list, default=DEFAULT_SEEDS)
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument("--solar-radius-deg", type=float, default=DEFAULT_SOLAR_RADIUS_DEG)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = validate_maxwell_gate(
        radius_km=args.radius_km,
        centre_z_km=args.centre_z_km,
        restarts=args.restarts,
        seeds=args.seeds,
        minimum_altitude_deg=args.minimum_altitude_deg,
        solar_radius_deg=args.solar_radius_deg,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    gate = payload["promotion_gate"]
    print(f"Maxwell cheap gate: {'PASS' if gate['passed'] else 'FAIL'}")
    for name, passed in gate["checks"].items():
        print(f"  {name}: {passed}")
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
