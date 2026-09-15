"""Run the pre-registered full C-2 validation for the selected Maxwell mirror."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from .ephemeris import MeeusLowPrecision
from .scan_luneburg import POLE_TARGETS, build_scan_groups
from .validate_maxwell import (
    CONSENSUS_FRACTION_OF_RADIUS,
    DEFAULT_RADIUS_KM,
    DEFAULT_RESTARTS,
    DEFAULT_SEEDS,
    MINIMUM_POLE_SEPARATION_RAD,
    _summarise,
    evaluate_maxwell,
    evaluate_n_equals_one,
)
from .validate_v1 import (
    DAILY_TRACKS,
    DEFAULT_SOLAR_RADIUS_DEG,
    TargetGroup,
    _visible_observers_for_track,
    build_target_group,
    observer_grid,
    solar_disk_samples,
)


MODEL_STATUS = "v2-maxwell-full-c2-preregistered"
SELECTED_RADIUS_KM = 1.20 * DEFAULT_RADIUS_KM
SELECTED_CENTRE_Z_KM = 0.40 * DEFAULT_RADIUS_KM
FORWARD_MARGIN_ANGLE_DEG = 10.0
MINIMUM_FORWARD_SINE = math.sin(math.radians(FORWARD_MARGIN_ANGLE_DEG))
MAXIMUM_DIAMETER_COEFFICIENT_OF_VARIATION = 0.05
MAXIMUM_DIAMETER_MAX_TO_MIN_RATIO = 1.10
MAXIMUM_DISK_AXIS_RATIO = 1.10
MAXIMUM_NORMALISED_CENTRE_OFFSET = 0.05
SAMPLE_IDS = (
    "centre",
    "north_limb",
    "south_limb",
    "east_limb",
    "west_limb",
)


def build_c2_tracks(
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> tuple[dict[str, object], ...]:
    candidates = observer_grid()
    ephemeris = MeeusLowPrecision()
    tracks: list[dict[str, object]] = []
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
        moments = []
        for instant, samples in samples_by_moment:
            moments.append(
                {
                    "timestamp_utc": instant.isoformat(),
                    "groups": {
                        sample_id: build_target_group(
                            f"{track_id}:{sample_id}",
                            samples[sample_id],
                            instant,
                            visible,
                        )
                        for sample_id in SAMPLE_IDS
                    },
                }
            )
        tracks.append(
            {
                "track_id": track_id,
                "fixed_observer_count": len(visible),
                "fixed_observers_deg": [list(observer) for observer in visible],
                "moments": moments,
            }
        )
    return tuple(tracks)


def _disk_shape(targets: dict[str, dict[str, object]]) -> dict[str, float] | None:
    if any(not bool(targets[name].get("valid")) for name in SAMPLE_IDS):
        return None
    points = {
        name: np.asarray(targets[name]["common_point_km"], dtype=float)
        for name in SAMPLE_IDS
    }
    north_south = float(
        np.linalg.norm(points["north_limb"] - points["south_limb"])
    )
    east_west = float(
        np.linalg.norm(points["east_limb"] - points["west_limb"])
    )
    mean_diameter = (north_south + east_west) / 2.0
    if mean_diameter <= 0.0 or min(north_south, east_west) <= 0.0:
        return None
    limb_centroid = np.mean(
        [
            points["north_limb"],
            points["south_limb"],
            points["east_limb"],
            points["west_limb"],
        ],
        axis=0,
    )
    centre_offset = float(np.linalg.norm(points["centre"] - limb_centroid))
    return {
        "north_south_diameter_km": north_south,
        "east_west_diameter_km": east_west,
        "mean_diameter_km": mean_diameter,
        "axis_ratio": max(north_south, east_west) / min(north_south, east_west),
        "diameter_anisotropy_fraction": (
            abs(north_south - east_west) / mean_diameter
        ),
        "centre_to_limb_centroid_offset_km": centre_offset,
        "normalised_centre_offset": centre_offset / mean_diameter,
    }


def _diameter_summary(diameters: Sequence[float]) -> dict[str, float | int | None]:
    if not diameters:
        return {
            "valid_disk_count": 0,
            "mean_reconstructed_diameter_km": None,
            "diameter_coefficient_of_variation": None,
            "diameter_max_to_min_ratio": None,
        }
    mean = float(np.mean(diameters))
    return {
        "valid_disk_count": len(diameters),
        "mean_reconstructed_diameter_km": mean,
        "diameter_coefficient_of_variation": float(np.std(diameters) / mean),
        "diameter_max_to_min_ratio": max(diameters) / min(diameters),
    }


def evaluate_c2(
    tracks: Sequence[dict[str, object]],
    evaluator: Callable[[TargetGroup], dict[str, object]],
) -> dict[str, object]:
    output_tracks: list[dict[str, object]] = []
    all_diameters: list[float] = []
    all_centre_rms: list[float] = []
    for track in tracks:
        moments = []
        track_diameters: list[float] = []
        for moment in track["moments"]:
            targets = {
                sample_id: evaluator(moment["groups"][sample_id])
                for sample_id in SAMPLE_IDS
            }
            shape = _disk_shape(targets)
            if shape is not None:
                diameter = shape["mean_diameter_km"]
                track_diameters.append(diameter)
                all_diameters.append(diameter)
            centre_rms = targets["centre"].get("direction_rms_deg")
            if centre_rms is not None:
                all_centre_rms.append(float(centre_rms))
            moments.append(
                {
                    "timestamp_utc": moment["timestamp_utc"],
                    "targets": targets,
                    "reconstructed_disk": shape,
                }
            )
        output_tracks.append(
            {
                "track_id": track["track_id"],
                "fixed_observer_count": track["fixed_observer_count"],
                "fixed_observers_deg": track["fixed_observers_deg"],
                "moments": moments,
                "summary": _diameter_summary(track_diameters),
            }
        )
    summary = _diameter_summary(all_diameters)
    summary["sample_count"] = sum(len(track["moments"]) for track in tracks)
    summary["target_count"] = summary["sample_count"] * len(SAMPLE_IDS)
    summary["mean_centre_direction_rms_deg"] = (
        float(np.mean(all_centre_rms)) if all_centre_rms else None
    )
    return {
        "constraint": "C-2 solar disk coherence and constancy",
        "daily_tracks": output_tracks,
        "summary": summary,
    }


def _c2_targets(report: dict[str, object]) -> list[dict[str, object]]:
    return [
        target
        for track in report["daily_tracks"]
        for moment in track["moments"]
        for target in moment["targets"].values()
    ]


def _c2_shapes(report: dict[str, object]) -> list[dict[str, float]]:
    return [
        moment["reconstructed_disk"]
        for track in report["daily_tracks"]
        for moment in track["moments"]
        if moment["reconstructed_disk"] is not None
    ]


def _metric_within_all_tracks(
    report: dict[str, object],
    key: str,
    maximum: float,
) -> bool:
    summaries = [report["summary"]] + [
        track["summary"] for track in report["daily_tracks"]
    ]
    return all(
        summary.get(key) is not None and float(summary[key]) <= maximum
        for summary in summaries
    )


def apply_full_c2_gate(
    candidate_c2: dict[str, object],
    baseline_c2: dict[str, object],
    candidate_poles: dict[str, object],
    baseline_poles: dict[str, object],
    radius_km: float,
    *,
    matches_contract: bool,
) -> dict[str, object]:
    targets = _c2_targets(candidate_c2)
    shapes = _c2_shapes(candidate_c2)
    candidate_pole_map = {
        target["target_id"]: target for target in candidate_poles["targets"]
    }
    baseline_pole_map = {
        target["target_id"]: target for target in baseline_poles["targets"]
    }
    pole_points = [
        np.asarray(candidate_pole_map[target_id].get("common_point_s3_km"))
        for target_id in POLE_TARGETS
        if candidate_pole_map[target_id].get("common_point_s3_km") is not None
    ]
    pole_separation = None
    if len(pole_points) == 2:
        pole_separation = math.acos(
            float(np.clip(np.dot(*pole_points) / radius_km**2, -1.0, 1.0))
        )
    pole_targets = list(candidate_pole_map.values())
    checks = {
        "matches_pre_registered_contract": matches_contract,
        "all_fifteen_disks_valid": (
            candidate_c2["summary"]["valid_disk_count"] == 15
            and len(shapes) == 15
        ),
        "all_seventy_five_targets_valid": (
            len(targets) == 75 and all(bool(target.get("valid")) for target in targets)
        ),
        "all_c2_restart_points_agree": all(
            bool(target.get("restart_seed_consensus")) for target in targets
        ),
        "all_c2_branch_assignments_agree": all(
            bool(target.get("restart_branch_assignment_consensus"))
            for target in targets
        ),
        "all_c2_forward_margins_at_least_sin_10_deg": all(
            target.get("minimum_forward_sine") is not None
            and float(target["minimum_forward_sine"]) >= MINIMUM_FORWARD_SINE
            for target in targets
        ),
        "all_c2_sources_inside_mirror_and_above_map": all(
            bool(target.get("inside_mirror"))
            and bool(target.get("source_above_map"))
            for target in targets
        ),
        "solar_centre_rms_below_n_equals_1": bool(
            candidate_c2["summary"].get("mean_centre_direction_rms_deg") is not None
            and baseline_c2["summary"].get("mean_centre_direction_rms_deg") is not None
            and candidate_c2["summary"]["mean_centre_direction_rms_deg"]
            < baseline_c2["summary"]["mean_centre_direction_rms_deg"]
        ),
        "diameter_cv_at_most_0_05_globally_and_per_track": (
            _metric_within_all_tracks(
                candidate_c2,
                "diameter_coefficient_of_variation",
                MAXIMUM_DIAMETER_COEFFICIENT_OF_VARIATION,
            )
        ),
        "diameter_ratio_at_most_1_10_globally_and_per_track": (
            _metric_within_all_tracks(
                candidate_c2,
                "diameter_max_to_min_ratio",
                MAXIMUM_DIAMETER_MAX_TO_MIN_RATIO,
            )
        ),
        "every_disk_axis_ratio_at_most_1_10": (
            len(shapes) == 15
            and all(shape["axis_ratio"] <= MAXIMUM_DISK_AXIS_RATIO for shape in shapes)
        ),
        "every_disk_normalised_centre_offset_at_most_0_05": (
            len(shapes) == 15
            and all(
                shape["normalised_centre_offset"]
                <= MAXIMUM_NORMALISED_CENTRE_OFFSET
                for shape in shapes
            )
        ),
        "both_c3_poles_valid": bool(candidate_poles["complete"]),
        "both_c3_poles_beat_n_equals_1": all(
            bool(candidate_pole_map[target_id].get("valid"))
            and candidate_pole_map[target_id]["direction_rms_deg"]
            < baseline_pole_map[target_id]["direction_rms_deg"]
            for target_id in POLE_TARGETS
        ),
        "all_c3_restart_points_and_branches_agree": all(
            bool(target.get("restart_seed_consensus"))
            and bool(target.get("restart_branch_assignment_consensus"))
            for target in pole_targets
        ),
        "all_c3_rays_forward_and_sources_physical": all(
            bool(target.get("all_rays_forward"))
            and bool(target.get("inside_mirror"))
            and bool(target.get("source_above_map"))
            for target in pole_targets
        ),
        "celestial_poles_not_collapsed": bool(
            pole_separation is not None
            and pole_separation > MINIMUM_POLE_SEPARATION_RAD
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "minimum_forward_sine": MINIMUM_FORWARD_SINE,
            "forward_margin_angle_deg": FORWARD_MARGIN_ANGLE_DEG,
            "maximum_diameter_coefficient_of_variation": (
                MAXIMUM_DIAMETER_COEFFICIENT_OF_VARIATION
            ),
            "maximum_diameter_max_to_min_ratio": (
                MAXIMUM_DIAMETER_MAX_TO_MIN_RATIO
            ),
            "maximum_disk_axis_ratio": MAXIMUM_DISK_AXIS_RATIO,
            "maximum_normalised_centre_offset": (
                MAXIMUM_NORMALISED_CENTRE_OFFSET
            ),
            "restart_point_consensus_fraction_of_radius": (
                CONSENSUS_FRACTION_OF_RADIUS
            ),
            "minimum_pole_separation_rad": MINIMUM_POLE_SEPARATION_RAD,
        },
        "pole_separation_rad": pole_separation,
        "rule_frozen_before_run": True,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_full_c2_validation(
    output: Path,
    *,
    radius_km: float = SELECTED_RADIUS_KM,
    centre_z_km: float = SELECTED_CENTRE_Z_KM,
    restarts: int = DEFAULT_RESTARTS,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, object]:
    matches_contract = bool(
        math.isclose(radius_km, SELECTED_RADIUS_KM, rel_tol=0.0, abs_tol=1e-9)
        and math.isclose(
            centre_z_km, SELECTED_CENTRE_Z_KM, rel_tol=0.0, abs_tol=1e-9
        )
        and restarts == DEFAULT_RESTARTS
        and tuple(seeds) == DEFAULT_SEEDS
        and math.isclose(minimum_altitude_deg, 2.0, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(
            solar_radius_deg,
            DEFAULT_SOLAR_RADIUS_DEG,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    )
    tracks = build_c2_tracks(minimum_altitude_deg, solar_radius_deg)
    _, pole_groups = build_scan_groups(minimum_altitude_deg, solar_radius_deg)
    baseline_c2 = evaluate_c2(tracks, evaluate_n_equals_one)
    baseline_poles = _summarise(pole_groups, evaluate_n_equals_one)
    centre = np.array([0.0, 0.0, centre_z_km])
    evaluator = lambda group: evaluate_maxwell(
        group, radius_km, centre, seeds, restarts
    )
    candidate_c2 = evaluate_c2(tracks, evaluator)
    candidate_poles = _summarise(pole_groups, evaluator)
    gate = apply_full_c2_gate(
        candidate_c2,
        baseline_c2,
        candidate_poles,
        baseline_poles,
        radius_km,
        matches_contract=matches_contract,
    )
    payload = {
        "schema_version": 1,
        "model": "maxwell-mirror-v2-full-c2-preregistered",
        "status": "completed",
        "pre_registered_contract": "docs/V2_MAXWELL_FULL_C2.md",
        "matches_pre_registered_contract": matches_contract,
        "design": {
            "radius_km": radius_km,
            "centre_z_km": centre_z_km,
            "solar_radius_deg": solar_radius_deg,
            "daily_track_count": len(tracks),
            "moments_per_track": [len(track["moments"]) for track in tracks],
            "samples_per_moment": list(SAMPLE_IDS),
            "restarts_per_seed": restarts,
            "seeds": list(seeds),
            "rk45_used": False,
        },
        "baseline_n_equals_1": {
            "solar_disk_c2": baseline_c2,
            "celestial_poles_c3": baseline_poles,
        },
        "candidate": {
            "solar_disk_c2": candidate_c2,
            "celestial_poles_c3": candidate_poles,
        },
        "acceptance_gate": gate,
    }
    _write_json(output, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius-km", type=float, default=SELECTED_RADIUS_KM)
    parser.add_argument("--centre-z-km", type=float, default=SELECTED_CENTRE_Z_KM)
    parser.add_argument("--restarts", type=int, default=DEFAULT_RESTARTS)
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument("--solar-radius-deg", type=float, default=DEFAULT_SOLAR_RADIUS_DEG)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_full_c2_validation(
        args.output,
        radius_km=args.radius_km,
        centre_z_km=args.centre_z_km,
        restarts=args.restarts,
        minimum_altitude_deg=args.minimum_altitude_deg,
        solar_radius_deg=args.solar_radius_deg,
    )
    print(f"Full C-2: {'PASS' if payload['acceptance_gate']['passed'] else 'FAIL'}")
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
