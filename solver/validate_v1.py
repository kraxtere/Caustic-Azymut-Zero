"""Stress-test a frozen v1 fit on a dense grid, solar limb, and sky poles.

This command performs validation only: it never refits field parameters.  The
default ``vacuum-geometric`` policy deliberately sets the atmospheric
coefficient to zero because the Meeus target directions used here are
geometric alt/az directions and contain no apparent-refraction correction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from .ephemeris import MeeusLowPrecision, RaDec
from .field import FieldParams
from .geometry_flat import altaz_of_radec, observer_xy, sky_direction_3d
from .raytrace import (
    IntegrationOptions,
    RayResult,
    TriangulationResult,
    trace_ray,
    triangulate_half_lines_detailed,
)


DEFAULT_LATITUDES_DEG = (-70.0, -50.0, -30.0, -10.0, 10.0, 30.0, 50.0, 70.0)
DEFAULT_LONGITUDES_DEG = (
    -157.5,
    -112.5,
    -67.5,
    -22.5,
    22.5,
    67.5,
    112.5,
    157.5,
)
DEFAULT_SOLAR_RADIUS_DEG = 0.2666
DAILY_TRACK_CLOCKS = ((10, 0), (11, 30), (13, 0), (14, 30), (16, 0))
DAILY_TRACK_DATES = (
    ("march_equinox", 2026, 3, 20),
    ("june_solstice", 2026, 6, 21),
    ("december_solstice", 2026, 12, 21),
)
DAILY_TRACKS = tuple(
    (
        track_id,
        tuple(
            datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
            for hour, minute in DAILY_TRACK_CLOCKS
        ),
    )
    for track_id, year, month, day in DAILY_TRACK_DATES
)
POLE_VALIDATION_MOMENT = datetime(2026, 3, 20, 14, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class TargetGroup:
    target_id: str
    timestamp_utc: datetime
    origins: tuple[np.ndarray, ...]
    directions: tuple[np.ndarray, ...]
    observer_coordinates_deg: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class TracedTarget:
    target_id: str
    timestamp_utc: datetime
    observer_count: int
    invalid_rays: int
    triangulation: TriangulationResult | None
    rays: tuple[RayResult, ...]


def observer_grid(
    latitudes_deg: Iterable[float] = DEFAULT_LATITUDES_DEG,
    longitudes_deg: Iterable[float] = DEFAULT_LONGITUDES_DEG,
) -> tuple[tuple[float, float], ...]:
    """Return the deterministic latitude/longitude product used by v1."""

    return tuple(
        (float(latitude), float(longitude))
        for latitude in latitudes_deg
        for longitude in longitudes_deg
    )


def radec_to_unit(radec: RaDec) -> np.ndarray:
    right_ascension = math.radians(radec.ra_deg)
    declination = math.radians(radec.dec_deg)
    return np.array(
        [
            math.cos(declination) * math.cos(right_ascension),
            math.cos(declination) * math.sin(right_ascension),
            math.sin(declination),
        ],
        dtype=float,
    )


def unit_to_radec(vector: np.ndarray) -> RaDec:
    unit = np.asarray(vector, dtype=float)
    if unit.shape != (3,) or not np.all(np.isfinite(unit)):
        raise ValueError("vector must be a finite three-vector")
    norm = float(np.linalg.norm(unit))
    if norm == 0:
        raise ValueError("vector cannot be zero")
    unit /= norm
    return RaDec(
        ra_deg=math.degrees(math.atan2(unit[1], unit[0])) % 360.0,
        dec_deg=math.degrees(math.asin(float(np.clip(unit[2], -1.0, 1.0)))),
    )


def angular_separation_deg(first: RaDec, second: RaDec) -> float:
    cosine = float(
        np.clip(np.dot(radec_to_unit(first), radec_to_unit(second)), -1, 1)
    )
    return math.degrees(math.acos(cosine))


def solar_disk_samples(
    centre: RaDec,
    angular_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, RaDec]:
    """Return centre and four exact great-circle limb offsets."""

    if not math.isfinite(angular_radius_deg) or angular_radius_deg <= 0:
        raise ValueError("angular_radius_deg must be finite and positive")
    centre_vector = radec_to_unit(centre)
    right_ascension = math.radians(centre.ra_deg)
    declination = math.radians(centre.dec_deg)
    east = np.array([-math.sin(right_ascension), math.cos(right_ascension), 0.0])
    north = np.array(
        [
            -math.sin(declination) * math.cos(right_ascension),
            -math.sin(declination) * math.sin(right_ascension),
            math.cos(declination),
        ]
    )
    radius = math.radians(angular_radius_deg)

    def offset(tangent: np.ndarray, sign: float) -> RaDec:
        return unit_to_radec(
            centre_vector * math.cos(radius)
            + sign * tangent * math.sin(radius)
        )

    return {
        "centre": centre,
        "north_limb": offset(north, 1.0),
        "south_limb": offset(north, -1.0),
        "east_limb": offset(east, 1.0),
        "west_limb": offset(east, -1.0),
    }


def _visible_observers(
    targets: Sequence[RaDec],
    instant: datetime,
    candidates: Sequence[tuple[float, float]],
    minimum_altitude_deg: float,
) -> tuple[tuple[float, float], ...]:
    """Select observers which see every requested target above the cutoff."""

    return tuple(
        observer
        for observer in candidates
        if all(
            altaz_of_radec(target, *observer, instant)[0]
            >= minimum_altitude_deg
            for target in targets
        )
    )


def _visible_observers_for_track(
    samples_by_moment: Sequence[tuple[datetime, Sequence[RaDec]]],
    candidates: Sequence[tuple[float, float]],
    minimum_altitude_deg: float,
) -> tuple[tuple[float, float], ...]:
    """Use one fixed observer set throughout a daily C-2 track."""

    return tuple(
        observer
        for observer in candidates
        if all(
            all(
                altaz_of_radec(target, *observer, instant)[0]
                >= minimum_altitude_deg
                for target in targets
            )
            for instant, targets in samples_by_moment
        )
    )


def build_target_group(
    target_id: str,
    target: RaDec,
    instant: datetime,
    observers: Sequence[tuple[float, float]],
) -> TargetGroup:
    origins: list[np.ndarray] = []
    directions: list[np.ndarray] = []
    for latitude, longitude in observers:
        altitude, azimuth = altaz_of_radec(
            target,
            latitude,
            longitude,
            instant,
        )
        origins.append(observer_xy(latitude, longitude))
        directions.append(
            sky_direction_3d(altitude, azimuth, latitude, longitude)
        )
    return TargetGroup(
        target_id=target_id,
        timestamp_utc=instant,
        origins=tuple(origins),
        directions=tuple(directions),
        observer_coordinates_deg=tuple(observers),
    )


def trace_target(
    group: TargetGroup,
    params: FieldParams,
    integration: IntegrationOptions,
    executor: Executor | None = None,
) -> TracedTarget:
    jobs = tuple(
        (origin, direction, params, integration)
        for origin, direction in zip(group.origins, group.directions, strict=True)
    )
    rays = tuple(
        executor.map(_trace_ray_job, jobs)
        if executor is not None
        else map(_trace_ray_job, jobs)
    )
    invalid_rays = sum(ray.status != "escaped" for ray in rays)
    triangulation = None
    if not invalid_rays and len(rays) >= 3:
        candidate = triangulate_half_lines_detailed(
            [ray.point for ray in rays],
            [ray.direction for ray in rays],
        )
        if (
            candidate.matrix_rank >= 3
            and math.isfinite(candidate.rms_km)
            and candidate.condition_number <= 1e14
        ):
            triangulation = candidate
    return TracedTarget(
        target_id=group.target_id,
        timestamp_utc=group.timestamp_utc,
        observer_count=len(rays),
        invalid_rays=invalid_rays,
        triangulation=triangulation,
        rays=rays,
    )


def _trace_ray_job(
    job: tuple[np.ndarray, np.ndarray, FieldParams, IntegrationOptions],
) -> RayResult:
    """Picklable unit of work for Windows multiprocessing."""

    origin, direction, params, integration = job
    return trace_ray(
        origin,
        direction,
        params,
        integration,
        collect_diagnostics=True,
    )


def _finite_diagnostic_values(
    rays: Sequence[RayResult],
    attribute: str,
) -> list[float]:
    values = [getattr(ray, attribute) for ray in rays]
    return [
        float(value)
        for value in values
        if value is not None and math.isfinite(value)
    ]


def _target_to_json(target: TracedTarget) -> dict[str, object]:
    payload: dict[str, object] = {
        "target_id": target.target_id,
        "timestamp_utc": target.timestamp_utc.isoformat(),
        "observer_count": target.observer_count,
        "invalid_rays": target.invalid_rays,
        "triangulation_valid": target.triangulation is not None,
    }
    if target.triangulation is not None:
        result = target.triangulation
        forward_violation_count = int(
            np.count_nonzero(result.forward_distances_km < -1e-6)
        )
        payload.update(
            {
                "rms_km": result.rms_km,
                "common_point_km": result.point.tolist(),
                "minimum_forward_distance_km": float(
                    np.min(result.forward_distances_km)
                ),
                "forward_ray_violation_count": forward_violation_count,
                "all_rays_forward": forward_violation_count == 0,
                "condition_number": result.condition_number,
            }
        )
    for attribute in (
        "net_direction_change_deg",
        "background_path_bending_deg",
        "ring_path_bending_deg",
        "combined_path_bending_deg",
    ):
        values = _finite_diagnostic_values(target.rays, attribute)
        stem = attribute.removesuffix("_deg")
        payload[f"{stem}_mean_deg"] = float(np.mean(values)) if values else None
        payload[f"{stem}_max_deg"] = max(values) if values else None
    ring_values = _finite_diagnostic_values(target.rays, "ring_path_bending_deg")
    payload["ring_affected_ray_count"] = sum(value > 1e-8 for value in ring_values)
    return payload


def _solar_shape_metrics(
    traced: dict[str, TracedTarget],
) -> dict[str, float | None] | None:
    if any(target.triangulation is None for target in traced.values()):
        return None
    points = {
        name: target.triangulation.point
        for name, target in traced.items()
        if target.triangulation is not None
    }
    north_south = float(
        np.linalg.norm(points["north_limb"] - points["south_limb"])
    )
    east_west = float(
        np.linalg.norm(points["east_limb"] - points["west_limb"])
    )
    mean_diameter = (north_south + east_west) / 2.0
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
        "axis_ratio": (
            max(north_south, east_west) / min(north_south, east_west)
            if min(north_south, east_west) > 0
            else None
        ),
        "diameter_anisotropy_fraction": (
            abs(north_south - east_west) / mean_diameter
            if mean_diameter > 0
            else None
        ),
        "centre_to_limb_centroid_offset_km": centre_offset,
        "normalised_centre_offset": (
            centre_offset / mean_diameter if mean_diameter > 0 else None
        ),
    }


def validate_solar_disk(
    params: FieldParams,
    integration: IntegrationOptions,
    observers: Sequence[tuple[float, float]],
    minimum_altitude_deg: float,
    solar_radius_deg: float,
    executor: Executor | None = None,
    tracks: Sequence[tuple[str, Sequence[datetime]]] = DAILY_TRACKS,
) -> dict[str, object]:
    ephemeris = MeeusLowPrecision()
    daily_tracks: list[dict[str, object]] = []
    all_diameters: list[float] = []
    all_centre_residuals: list[float] = []
    for track_id, instants in tracks:
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
            observers,
            minimum_altitude_deg,
        )
        moments: list[dict[str, object]] = []
        track_diameters: list[float] = []
        track_centre_residuals: list[float] = []
        for instant, samples in samples_by_moment:
            traced = {
                sample_id: trace_target(
                    build_target_group(sample_id, radec, instant, visible),
                    params,
                    integration,
                    executor,
                )
                for sample_id, radec in samples.items()
            }
            targets_json = {
                name: _target_to_json(target)
                for name, target in traced.items()
            }
            shape = _solar_shape_metrics(traced)
            if shape is not None:
                diameter = shape["mean_diameter_km"]
                if diameter is not None:
                    track_diameters.append(diameter)
                    all_diameters.append(diameter)
            if traced["centre"].triangulation is not None:
                centre_rms = traced["centre"].triangulation.rms_km
                track_centre_residuals.append(centre_rms)
                all_centre_residuals.append(centre_rms)
            moments.append(
                {
                    "timestamp_utc": instant.isoformat(),
                    "targets": targets_json,
                    "all_target_common_points_forward": all(
                        bool(target.get("all_rays_forward"))
                        for target in targets_json.values()
                    ),
                    "reconstructed_disk": shape,
                }
            )
        diameter_mean = (
            float(np.mean(track_diameters)) if track_diameters else None
        )
        daily_tracks.append(
            {
                "track_id": track_id,
                "fixed_observer_count": len(visible),
                "fixed_observers_deg": [list(observer) for observer in visible],
                "moments": moments,
                "summary": {
                    "valid_disk_count": len(track_diameters),
                    "mean_centre_rms_km": (
                        float(np.mean(track_centre_residuals))
                        if track_centre_residuals
                        else None
                    ),
                    "mean_reconstructed_diameter_km": diameter_mean,
                    "diameter_coefficient_of_variation": (
                        float(np.std(track_diameters) / diameter_mean)
                        if diameter_mean is not None and diameter_mean > 0
                        else None
                    ),
                    "diameter_max_to_min_ratio": (
                        max(track_diameters) / min(track_diameters)
                        if track_diameters and min(track_diameters) > 0
                        else None
                    ),
                },
            }
        )

    all_diameter_mean = (
        float(np.mean(all_diameters)) if all_diameters else None
    )
    return {
        "constraint": "C-2 solar disk coherence and constancy",
        "input_angular_radius_deg": solar_radius_deg,
        "design": (
            "fixed observer set within each daily track; 90-minute cadence "
            "avoids aliasing with the 45-degree longitude grid"
        ),
        "daily_tracks": daily_tracks,
        "summary": {
            "sample_count": sum(len(instants) for _, instants in tracks),
            "valid_disk_count": len(all_diameters),
            "mean_centre_rms_km": (
                float(np.mean(all_centre_residuals))
                if all_centre_residuals
                else None
            ),
            "mean_reconstructed_diameter_km": all_diameter_mean,
            "diameter_coefficient_of_variation": (
                float(np.std(all_diameters) / all_diameter_mean)
                if all_diameter_mean is not None and all_diameter_mean > 0
                else None
            ),
            "diameter_max_to_min_ratio": (
                max(all_diameters) / min(all_diameters)
                if all_diameters and min(all_diameters) > 0
                else None
            ),
        },
    }


def validate_celestial_poles(
    params: FieldParams,
    integration: IntegrationOptions,
    observers: Sequence[tuple[float, float]],
    minimum_altitude_deg: float,
    executor: Executor | None = None,
) -> dict[str, object]:
    instant = POLE_VALIDATION_MOMENT
    targets = {
        "north_celestial_pole": RaDec(0.0, 90.0),
        "south_celestial_pole": RaDec(0.0, -90.0),
    }
    results: dict[str, object] = {}
    for target_id, radec in targets.items():
        visible = _visible_observers(
            (radec,),
            instant,
            observers,
            minimum_altitude_deg,
        )
        traced = trace_target(
            build_target_group(target_id, radec, instant, visible),
            params,
            integration,
            executor,
        )
        results[target_id] = _target_to_json(traced)
    return {
        "constraint": "C-3 separate north and south celestial poles",
        "timestamp_utc": instant.isoformat(),
        "targets": results,
    }


def _load_fit(path: Path) -> tuple[dict[str, object], FieldParams, IntegrationOptions]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("model") != "axisymmetric-atmosphere-plus-gaussian-ring-v1":
        raise ValueError("fit JSON is not a v1 Gaussian-ring result")
    if payload.get("intersection_mode") != "rays":
        raise ValueError("v1 closure requires outward half-rays")
    params = FieldParams(**payload["parameters"])
    integration = IntegrationOptions(**payload["integration"])
    params.validate()
    return payload, params, integration


def _relative_change(fitted: float | None, baseline: float | None) -> float | None:
    if fitted is None or baseline is None or baseline == 0:
        return None
    return (fitted - baseline) / baseline


def _comparison_to_baseline(
    fitted_c2: dict[str, object],
    baseline_c2: dict[str, object],
    fitted_c3: dict[str, object],
    baseline_c3: dict[str, object],
) -> dict[str, object]:
    fitted_summary = fitted_c2["summary"]
    baseline_summary = baseline_c2["summary"]
    fitted_tracks = {
        track["track_id"]: track["summary"]
        for track in fitted_c2["daily_tracks"]
    }
    baseline_tracks = {
        track["track_id"]: track["summary"]
        for track in baseline_c2["daily_tracks"]
    }
    c2_tracks = {}
    for track_id, fitted_track in fitted_tracks.items():
        baseline_track = baseline_tracks[track_id]
        c2_tracks[track_id] = {
            "fitted_diameter_max_to_min_ratio": fitted_track[
                "diameter_max_to_min_ratio"
            ],
            "baseline_diameter_max_to_min_ratio": baseline_track[
                "diameter_max_to_min_ratio"
            ],
            "fitted_diameter_coefficient_of_variation": fitted_track[
                "diameter_coefficient_of_variation"
            ],
            "baseline_diameter_coefficient_of_variation": baseline_track[
                "diameter_coefficient_of_variation"
            ],
        }

    c3_targets = {}
    for target_id, fitted_target in fitted_c3["targets"].items():
        baseline_target = baseline_c3["targets"][target_id]
        c3_targets[target_id] = {
            "fitted_rms_km": fitted_target.get("rms_km"),
            "baseline_rms_km": baseline_target.get("rms_km"),
            "rms_relative_change": _relative_change(
                fitted_target.get("rms_km"),
                baseline_target.get("rms_km"),
            ),
            "fitted_all_rays_forward": fitted_target.get("all_rays_forward"),
            "baseline_all_rays_forward": baseline_target.get("all_rays_forward"),
            "fitted_minimum_forward_distance_km": fitted_target.get(
                "minimum_forward_distance_km"
            ),
            "baseline_minimum_forward_distance_km": baseline_target.get(
                "minimum_forward_distance_km"
            ),
        }
    return {
        "relative_change_convention": "(fitted - n=1) / n=1; negative is better",
        "c2_solar_disk": {
            "fitted_mean_centre_rms_km": fitted_summary["mean_centre_rms_km"],
            "baseline_mean_centre_rms_km": baseline_summary[
                "mean_centre_rms_km"
            ],
            "mean_centre_rms_relative_change": _relative_change(
                fitted_summary["mean_centre_rms_km"],
                baseline_summary["mean_centre_rms_km"],
            ),
            "daily_tracks": c2_tracks,
        },
        "c3_celestial_poles": c3_targets,
    }


def validate_fit(
    fit_path: Path,
    *,
    refraction_policy: str = "vacuum-geometric",
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
    workers: int = 1,
    c2_tracks: Sequence[tuple[str, Sequence[datetime]]] = DAILY_TRACKS,
) -> dict[str, object]:
    if refraction_policy not in {"vacuum-geometric", "as-fitted"}:
        raise ValueError("unknown refraction policy")
    if workers < 1:
        raise ValueError("workers must be at least one")
    fit_payload, fitted_params, integration = _load_fit(fit_path)
    effective_params = (
        replace(fitted_params, k=0.0)
        if refraction_policy == "vacuum-geometric"
        else fitted_params
    )
    observers = observer_grid()
    source_digest = hashlib.sha256(fit_path.read_bytes()).hexdigest()
    executor = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        c2_solar_disk = validate_solar_disk(
            effective_params,
            integration,
            observers,
            minimum_altitude_deg,
            solar_radius_deg,
            executor,
            c2_tracks,
        )
        c3_celestial_poles = validate_celestial_poles(
            effective_params,
            integration,
            observers,
            minimum_altitude_deg,
            executor,
        )
    finally:
        if executor is not None:
            executor.shutdown()

    no_field = replace(effective_params, k=0.0, A=0.0)
    baseline_c2 = validate_solar_disk(
        no_field,
        integration,
        observers,
        minimum_altitude_deg,
        solar_radius_deg,
        tracks=c2_tracks,
    )
    baseline_c3 = validate_celestial_poles(
        no_field,
        integration,
        observers,
        minimum_altitude_deg,
    )

    return {
        "schema_version": 2,
        "model": "axisymmetric-atmosphere-plus-gaussian-ring-v1-closure",
        "validation_only": True,
        "fit_source": {
            "path": str(fit_path),
            "sha256": source_digest,
            "optimizer_seed": fit_payload.get("optimizer", {}).get("seed"),
            "fitted_cost_km": fit_payload.get("fitted_cost_km"),
        },
        "coordinate_system": "x-y map plane, z altitude, kilometres",
        "intersection_mode": "rays",
        "refraction": {
            "policy": refraction_policy,
            "target_directions": "geometric Meeus alt-az; no apparent refraction",
            "fitted_parameters": asdict(fitted_params),
            "effective_parameters": asdict(effective_params),
            "note": (
                "k forced to zero to avoid fitting atmospheric refraction to "
                "geometric directions"
                if refraction_policy == "vacuum-geometric"
                else "fitted k retained; use only for an explicit sensitivity check"
            ),
        },
        "grid": {
            "latitudes_deg": list(DEFAULT_LATITUDES_DEG),
            "longitudes_deg": list(DEFAULT_LONGITUDES_DEG),
            "candidate_observer_count": len(observers),
            "minimum_altitude_deg": minimum_altitude_deg,
        },
        "workers_used": workers,
        "integration": asdict(integration),
        "c2_solar_disk": c2_solar_disk,
        "c3_celestial_poles": c3_celestial_poles,
        "baseline_n_equals_1": {
            "c2_solar_disk": baseline_c2,
            "c3_celestial_poles": baseline_c3,
        },
        "comparison_to_n_equals_1": _comparison_to_baseline(
            c2_solar_disk,
            baseline_c2,
            c3_celestial_poles,
            baseline_c3,
        ),
        "interpretation": {
            "automatic_pass_fail": False,
            "reason": (
                "No scientific acceptance tolerances for C-2/C-3 were supplied; "
                "the report preserves raw convergence, shape, and constancy metrics."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--refraction-policy",
        choices=("vacuum-geometric", "as-fitted"),
        default="vacuum-geometric",
    )
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--solar-radius-deg",
        type=float,
        default=DEFAULT_SOLAR_RADIUS_DEG,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        "Walidacja v1: 64 kandydatow, C-2 (3 dzienne tory po 5 chwil), "
        "C-3 (2 bieguny)."
    )
    print(f"Polityka refrakcji: {args.refraction_policy}")
    payload = validate_fit(
        args.fit_json,
        refraction_policy=args.refraction_policy,
        minimum_altitude_deg=args.minimum_altitude_deg,
        solar_radius_deg=args.solar_radius_deg,
        workers=args.workers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    c2 = payload["c2_solar_disk"]["summary"]
    print(
        "C-2: poprawnych rekonstrukcji tarczy "
        f"{c2['valid_disk_count']}/{c2['sample_count']}"
    )
    for track in payload["c2_solar_disk"]["daily_tracks"]:
        ratio = track["summary"]["diameter_max_to_min_ratio"]
        print(f"C-2 {track['track_id']}: stosunek max/min srednicy = {ratio}")
    for target_id, result in payload["c3_celestial_poles"]["targets"].items():
        print(
            f"C-3 {target_id}: RMS={result.get('rms_km')} km; "
            f"wszystkie promienie w przod={result.get('all_rays_forward')}"
        )
    comparison = payload["comparison_to_n_equals_1"]["c2_solar_disk"]
    print(
        "C-2 zmiana RMS wzgledem n=1 = "
        f"{comparison['mean_centre_rms_relative_change']}"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
