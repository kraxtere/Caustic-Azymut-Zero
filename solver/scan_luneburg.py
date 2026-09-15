"""Cheap staged scan of Luneburg placement before the full C-2 validation.

Stage ``z0`` deliberately scans clearly non-zero vertical lens centres at one
fixed radius.  Only after inspecting that result should stage ``grid`` scan a
local Cartesian product of radius and centre height.  Every candidate uses the
15 solar centres and both C-3 poles from the existing validation design; solar
limbs are not traced here.

The promotion gate is intentionally strict.  A candidate advances only when
all targets are valid, its mean solar-centre RMS and each pole RMS are lower
than their matching n=1 controls, and every minimum forward distance is
non-negative.  The output is checkpointed after every candidate.
"""

from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from .ephemeris import MeeusLowPrecision, RaDec
from .field import FieldParams
from .field_lens import LensFieldParams
from .geometry_flat import R_MAP
from .raytrace import FieldParameters, IntegrationOptions
from .validate_v1 import (
    DAILY_TRACKS,
    DEFAULT_SOLAR_RADIUS_DEG,
    POLE_VALIDATION_MOMENT,
    TargetGroup,
    _visible_observers,
    _visible_observers_for_track,
    build_target_group,
    observer_grid,
    solar_disk_samples,
    trace_target,
)


DEFAULT_BASE_RADIUS_KM = math.pi * R_MAP
DEFAULT_STAGE1_Z0_FRACTIONS = (-0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 0.0)
DEFAULT_GRID_RADIUS_FRACTIONS = (0.8, 1.0, 1.2)
POLE_TARGETS = {
    "north_celestial_pole": RaDec(0.0, 90.0),
    "south_celestial_pole": RaDec(0.0, -90.0),
}


def parse_float_list(value: str) -> tuple[float, ...]:
    """Parse a comma-separated, finite list without silently deduplicating."""

    try:
        values = tuple(float(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected comma-separated numbers") from error
    if not values or any(not math.isfinite(item) for item in values):
        raise argparse.ArgumentTypeError("expected at least one finite number")
    if len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("scan values must be unique")
    return values


def build_candidates(
    stage: str,
    base_radius_km: float,
    z0_fractions: Sequence[float] | None,
    radius_fractions: Sequence[float] = DEFAULT_GRID_RADIUS_FRACTIONS,
) -> tuple[LensFieldParams, ...]:
    """Build the ordered stage-one line or stage-two local grid."""

    if not math.isfinite(base_radius_km) or base_radius_km <= 0:
        raise ValueError("base_radius_km must be finite and positive")
    if stage == "z0":
        effective_z0 = z0_fractions or DEFAULT_STAGE1_Z0_FRACTIONS
        radii = (base_radius_km,)
    elif stage == "grid":
        if z0_fractions is None:
            raise ValueError(
                "stage grid requires --z0-fractions chosen from the stage-z0 result"
            )
        effective_z0 = z0_fractions
        if not radius_fractions or any(
            not math.isfinite(value) or value <= 0 for value in radius_fractions
        ):
            raise ValueError("radius fractions must be finite and positive")
        radii = tuple(base_radius_km * value for value in radius_fractions)
    else:
        raise ValueError("stage must be 'z0' or 'grid'")

    if any(not math.isfinite(value) for value in effective_z0):
        raise ValueError("z0 fractions must be finite")
    candidates = tuple(
        LensFieldParams(
            family="luneburg",
            radius_km=radius,
            centre_km=(0.0, 0.0, base_radius_km * z0_fraction),
        )
        for radius in radii
        for z0_fraction in effective_z0
    )
    if len({(item.radius_km, item.centre_km[2]) for item in candidates}) != len(
        candidates
    ):
        raise ValueError("candidate grid contains duplicates")
    return candidates


def build_scan_groups(
    minimum_altitude_deg: float,
    solar_radius_deg: float,
) -> tuple[tuple[TargetGroup, ...], tuple[TargetGroup, ...]]:
    """Build the exact centre-only subset of the existing C-2/C-3 design."""

    candidates = observer_grid()
    ephemeris = MeeusLowPrecision()
    solar_groups: list[TargetGroup] = []
    for track_id, instants in DAILY_TRACKS:
        samples_by_moment = tuple(
            (
                instant,
                solar_disk_samples(
                    ephemeris.sun_radec(instant),
                    solar_radius_deg,
                ),
            )
            for instant in instants
        )
        visible = _visible_observers_for_track(
            tuple(
                (instant, tuple(samples.values()))
                for instant, samples in samples_by_moment
            ),
            candidates,
            minimum_altitude_deg,
        )
        for instant, samples in samples_by_moment:
            solar_groups.append(
                build_target_group(
                    f"{track_id}:centre",
                    samples["centre"],
                    instant,
                    visible,
                )
            )

    pole_groups: list[TargetGroup] = []
    for target_id, target in POLE_TARGETS.items():
        visible = _visible_observers(
            (target,),
            POLE_VALIDATION_MOMENT,
            candidates,
            minimum_altitude_deg,
        )
        pole_groups.append(
            build_target_group(
                target_id,
                target,
                POLE_VALIDATION_MOMENT,
                visible,
            )
        )
    return tuple(solar_groups), tuple(pole_groups)


def _summarise_groups(
    groups: Iterable[TargetGroup],
    params: FieldParameters,
    integration: IntegrationOptions,
    executor: Executor | None,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for group in groups:
        traced = trace_target(group, params, integration, executor)
        triangulation = traced.triangulation
        results.append(
            {
                "target_id": traced.target_id,
                "timestamp_utc": traced.timestamp_utc.isoformat(),
                "observer_count": traced.observer_count,
                "invalid_rays": traced.invalid_rays,
                "triangulation_valid": triangulation is not None,
                "rms_km": triangulation.rms_km if triangulation is not None else None,
                "minimum_forward_distance_km": (
                    float(np.min(triangulation.forward_distances_km))
                    if triangulation is not None
                    else None
                ),
            }
        )

    complete = all(
        item["invalid_rays"] == 0 and item["triangulation_valid"]
        for item in results
    )
    rms_values = [
        float(item["rms_km"])
        for item in results
        if item["rms_km"] is not None
    ]
    forward_values = [
        float(item["minimum_forward_distance_km"])
        for item in results
        if item["minimum_forward_distance_km"] is not None
    ]
    return {
        "target_count": len(results),
        "valid_target_count": len(rms_values),
        "invalid_ray_count": sum(int(item["invalid_rays"]) for item in results),
        "complete": complete,
        "mean_rms_km": float(np.mean(rms_values)) if complete else None,
        "partial_mean_rms_km": float(np.mean(rms_values)) if rms_values else None,
        "minimum_forward_distance_km": (
            min(forward_values) if len(forward_values) == len(results) else None
        ),
        "all_minimum_forward_distances_non_negative": (
            complete
            and len(forward_values) == len(results)
            and all(value >= 0.0 for value in forward_values)
        ),
        "targets": results,
    }


def evaluate_candidate(
    params: FieldParameters,
    solar_groups: Sequence[TargetGroup],
    pole_groups: Sequence[TargetGroup],
    integration: IntegrationOptions,
    executor: Executor | None,
) -> dict[str, object]:
    """Evaluate one field on solar centres and the two separate poles."""

    solar = _summarise_groups(solar_groups, params, integration, executor)
    poles_summary = _summarise_groups(pole_groups, params, integration, executor)
    poles = {
        item["target_id"]: item for item in poles_summary.pop("targets")
    }
    poles_summary["targets"] = poles
    return {"solar_centres": solar, "celestial_poles": poles_summary}


def apply_promotion_gate(
    candidate: dict[str, object],
    baseline: dict[str, object],
) -> dict[str, object]:
    """Apply the approved all-or-nothing RMS and forward-distance gate."""

    candidate_solar = candidate["solar_centres"]
    baseline_solar = baseline["solar_centres"]
    candidate_poles = candidate["celestial_poles"]
    baseline_poles = baseline["celestial_poles"]
    candidate_targets = candidate_poles["targets"]
    baseline_targets = baseline_poles["targets"]

    solar_complete = bool(candidate_solar["complete"])
    solar_beats = (
        solar_complete
        and candidate_solar["mean_rms_km"] < baseline_solar["mean_rms_km"]
    )
    pole_checks = {}
    for target_id in POLE_TARGETS:
        target = candidate_targets[target_id]
        control = baseline_targets[target_id]
        pole_checks[target_id] = bool(
            target["triangulation_valid"]
            and target["invalid_rays"] == 0
            and target["rms_km"] < control["rms_km"]
        )

    all_forward = bool(
        candidate_solar["all_minimum_forward_distances_non_negative"]
        and candidate_poles["all_minimum_forward_distances_non_negative"]
    )
    checks = {
        "complete_solar_centre_set": solar_complete,
        "solar_mean_rms_below_n_equals_1": solar_beats,
        "north_pole_rms_below_n_equals_1": pole_checks[
            "north_celestial_pole"
        ],
        "south_pole_rms_below_n_equals_1": pole_checks[
            "south_celestial_pole"
        ],
        "all_minimum_forward_distances_non_negative": all_forward,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "rule": (
            "all targets valid; solar mean RMS and each C-3 pole RMS strictly "
            "below matching n=1; every minimum_forward_distance_km >= 0"
        ),
    }


def _checkpoint(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("z0", "grid"), default="z0")
    parser.add_argument(
        "--base-radius-km",
        type=float,
        default=DEFAULT_BASE_RADIUS_KM,
    )
    parser.add_argument(
        "--z0-fractions",
        type=parse_float_list,
        help=(
            "comma-separated multiples of base radius; stage z0 defaults to "
            "-0.75,-0.5,-0.25,0.25,0.5,0.75 followed by a zero control; "
            "required for stage grid"
        ),
    )
    parser.add_argument(
        "--radius-fractions",
        type=parse_float_list,
        default=DEFAULT_GRID_RADIUS_FRACTIONS,
        help="stage-grid multiples of base radius (default: 0.8,1.0,1.2)",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-path-km", type=float, default=500_000.0)
    parser.add_argument("--rtol", type=float, default=1e-4)
    parser.add_argument("--atol", type=float, default=1e-7)
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument(
        "--solar-radius-deg",
        type=float,
        default=DEFAULT_SOLAR_RADIUS_DEG,
        help="used only to preserve the full-C-2 observer cohorts",
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("workers must be at least one")
    candidates = build_candidates(
        args.stage,
        args.base_radius_km,
        args.z0_fractions,
        args.radius_fractions,
    )
    integration = IntegrationOptions(
        max_path_km=args.max_path_km,
        rtol=args.rtol,
        atol=args.atol,
    )
    solar_groups, pole_groups = build_scan_groups(
        args.minimum_altitude_deg,
        args.solar_radius_deg,
    )
    rays_per_candidate = sum(
        len(group.origins) for group in (*solar_groups, *pole_groups)
    )
    payload: dict[str, object] = {
        "schema_version": 1,
        "model": "luneburg-v2-staged-placement-scan",
        "stage": args.stage,
        "status": "running",
        "scan_design": {
            "base_radius_km": args.base_radius_km,
            "z0_fractions_of_base_radius": (
                list(args.z0_fractions)
                if args.z0_fractions is not None
                else list(DEFAULT_STAGE1_Z0_FRACTIONS)
            ),
            "radius_fractions_of_base_radius": (
                [1.0]
                if args.stage == "z0"
                else list(args.radius_fractions)
            ),
            "candidate_count": len(candidates),
            "solar_centre_count": len(solar_groups),
            "pole_count": len(pole_groups),
            "rays_per_candidate": rays_per_candidate,
            "full_solar_limb_c2_included": False,
            "stage_order": "z0 first; local (R,z0) grid second",
        },
        "integration": asdict(integration),
        "workers_used": args.workers,
        "promotion_gate": {
            "requires_complete_evaluated_set": True,
            "solar_mean_rms_strictly_below_n_equals_1": True,
            "each_pole_rms_strictly_below_n_equals_1": True,
            "minimum_forward_distance_km_required": ">= 0 for every target",
        },
        "baseline_n_equals_1": None,
        "candidates": [],
        "qualifying_candidates": [],
    }
    _checkpoint(args.output, payload)

    executor = (
        ProcessPoolExecutor(max_workers=args.workers)
        if args.workers > 1
        else None
    )
    try:
        no_field = FieldParams(k=0.0, H=8.0, A=0.0, rho0=5000.0, s=1000.0)
        print(f"Kontrola n=1; {rays_per_candidate} promieni")
        baseline = evaluate_candidate(
            no_field,
            solar_groups,
            pole_groups,
            integration,
            executor,
        )
        payload["baseline_n_equals_1"] = baseline
        _checkpoint(args.output, payload)

        records: list[dict[str, object]] = payload["candidates"]
        for number, params in enumerate(candidates, start=1):
            print(
                f"[{number}/{len(candidates)}] R={params.radius_km:.6f} km; "
                f"z0={params.centre_km[2]:.6f} km"
            )
            metrics = evaluate_candidate(
                params,
                solar_groups,
                pole_groups,
                integration,
                executor,
            )
            gate = apply_promotion_gate(metrics, baseline)
            record = {
                "candidate_id": number,
                "parameters": asdict(params),
                "metrics": metrics,
                "promotion_gate": gate,
            }
            records.append(record)
            if gate["passed"]:
                payload["qualifying_candidates"].append(number)
            _checkpoint(args.output, payload)
            print(f"  bramka: {'PASS' if gate['passed'] else 'FAIL'}")
    finally:
        if executor is not None:
            executor.shutdown()

    payload["status"] = "completed"
    payload["completed_candidate_count"] = len(payload["candidates"])
    payload["qualifying_candidate_count"] = len(
        payload["qualifying_candidates"]
    )
    _checkpoint(args.output, payload)
    print(
        f"Zakonczono: {payload['qualifying_candidate_count']}/"
        f"{len(candidates)} kandydatow przechodzi bramke"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
