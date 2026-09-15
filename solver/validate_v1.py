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
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from .ephemeris import MeeusLowPrecision, RaDec
from .field import FieldParams
from .fit_field import MOMENTS
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
) -> TracedTarget:
    rays = tuple(
        trace_ray(
            origin,
            direction,
            params,
            integration,
            collect_diagnostics=True,
        )
        for origin, direction in zip(group.origins, group.directions, strict=True)
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
        payload.update(
            {
                "rms_km": result.rms_km,
                "common_point_km": result.point.tolist(),
                "minimum_forward_distance_km": float(
                    np.min(result.forward_distances_km)
                ),
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
) -> dict[str, object]:
    ephemeris = MeeusLowPrecision()
    moments: list[dict[str, object]] = []
    diameters: list[float] = []
    centre_residuals: list[float] = []
    for instant in MOMENTS:
        samples = solar_disk_samples(
            ephemeris.sun_radec(instant),
            solar_radius_deg,
        )
        visible = _visible_observers(
            tuple(samples.values()),
            instant,
            observers,
            minimum_altitude_deg,
        )
        traced = {
            sample_id: trace_target(
                build_target_group(sample_id, radec, instant, visible),
                params,
                integration,
            )
            for sample_id, radec in samples.items()
        }
        shape = _solar_shape_metrics(traced)
        if shape is not None:
            diameters.append(shape["mean_diameter_km"])
        if traced["centre"].triangulation is not None:
            centre_residuals.append(traced["centre"].triangulation.rms_km)
        moments.append(
            {
                "timestamp_utc": instant.isoformat(),
                "common_observer_count": len(visible),
                "targets": {
                    name: _target_to_json(target)
                    for name, target in traced.items()
                },
                "reconstructed_disk": shape,
            }
        )

    diameter_mean = float(np.mean(diameters)) if diameters else None
    return {
        "constraint": "C-2 solar disk coherence and constancy",
        "input_angular_radius_deg": solar_radius_deg,
        "moments": moments,
        "summary": {
            "valid_disk_count": len(diameters),
            "mean_centre_rms_km": (
                float(np.mean(centre_residuals)) if centre_residuals else None
            ),
            "mean_reconstructed_diameter_km": diameter_mean,
            "diameter_coefficient_of_variation": (
                float(np.std(diameters) / diameter_mean)
                if diameter_mean is not None and diameter_mean > 0
                else None
            ),
            "diameter_max_to_min_ratio": (
                max(diameters) / min(diameters)
                if diameters and min(diameters) > 0
                else None
            ),
        },
    }


def validate_celestial_poles(
    params: FieldParams,
    integration: IntegrationOptions,
    observers: Sequence[tuple[float, float]],
    minimum_altitude_deg: float,
) -> dict[str, object]:
    instant = MOMENTS[0]
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


def validate_fit(
    fit_path: Path,
    *,
    refraction_policy: str = "vacuum-geometric",
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, object]:
    if refraction_policy not in {"vacuum-geometric", "as-fitted"}:
        raise ValueError("unknown refraction policy")
    fit_payload, fitted_params, integration = _load_fit(fit_path)
    effective_params = (
        replace(fitted_params, k=0.0)
        if refraction_policy == "vacuum-geometric"
        else fitted_params
    )
    observers = observer_grid()
    source_digest = hashlib.sha256(fit_path.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
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
        "integration": asdict(integration),
        "c2_solar_disk": validate_solar_disk(
            effective_params,
            integration,
            observers,
            minimum_altitude_deg,
            solar_radius_deg,
        ),
        "c3_celestial_poles": validate_celestial_poles(
            effective_params,
            integration,
            observers,
            minimum_altitude_deg,
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
    parser.add_argument(
        "--solar-radius-deg",
        type=float,
        default=DEFAULT_SOLAR_RADIUS_DEG,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("Walidacja v1: 64 kandydatow, C-2 (5 punktow tarczy), C-3 (2 bieguny).")
    print(f"Polityka refrakcji: {args.refraction_policy}")
    payload = validate_fit(
        args.fit_json,
        refraction_policy=args.refraction_policy,
        minimum_altitude_deg=args.minimum_altitude_deg,
        solar_radius_deg=args.solar_radius_deg,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    c2 = payload["c2_solar_disk"]["summary"]
    print(f"C-2: poprawnych rekonstrukcji tarczy {c2['valid_disk_count']}/6")
    print(f"C-2: stosunek max/min srednicy = {c2['diameter_max_to_min_ratio']}")
    for target_id, result in payload["c3_celestial_poles"]["targets"].items():
        print(f"C-3 {target_id}: RMS={result.get('rms_km')} km")
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
