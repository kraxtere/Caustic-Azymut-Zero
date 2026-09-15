"""Validate an explicit v2 spherical-lens candidate on the v1 C-2/C-3 grid.

This is a validation-only adapter, not an optimizer. The default geometry is
a Luneburg hemisphere centred on the azimuthal map origin, with its equator in
the map plane and radius equal to the north-to-south map radius.
"""

from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

from .field import FieldParams
from .field_lens import LensFieldParams
from .geometry_flat import R_MAP
from .raytrace import IntegrationOptions
from .validate_v1 import (
    DEFAULT_SOLAR_RADIUS_DEG,
    _comparison_to_baseline,
    observer_grid,
    validate_celestial_poles,
    validate_solar_disk,
)


DEFAULT_DOME_RADIUS_KM = math.pi * R_MAP


def validate_lens_candidate(
    params: LensFieldParams,
    *,
    integration: IntegrationOptions | None = None,
    workers: int = 1,
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, object]:
    """Run unchanged C-2/C-3 metrics for one declared hybrid placement."""

    params.validate()
    if workers < 1:
        raise ValueError("workers must be at least one")
    if params.family == "maxwell":
        raise ValueError(
            "exact Maxwell validation requires the mirror boundary described "
            "by Leonhardt; the current integrator has no reflection event"
        )
    integration = integration or IntegrationOptions(rtol=1e-4, atol=1e-7)
    observers = observer_grid()
    executor = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        fitted_c2 = validate_solar_disk(
            params,
            integration,
            observers,
            minimum_altitude_deg,
            solar_radius_deg,
            executor,
        )
        fitted_c3 = validate_celestial_poles(
            params,
            integration,
            observers,
            minimum_altitude_deg,
            executor,
        )
    finally:
        if executor is not None:
            executor.shutdown()

    no_field = FieldParams(k=0.0, H=8.0, A=0.0, rho0=5000.0, s=1000.0)
    baseline_c2 = validate_solar_disk(
        no_field,
        integration,
        observers,
        minimum_altitude_deg,
        solar_radius_deg,
    )
    baseline_c3 = validate_celestial_poles(
        no_field,
        integration,
        observers,
        minimum_altitude_deg,
    )
    return {
        "schema_version": 2,
        "model": "spherical-gradient-index-lens-v2-hybrid-candidate",
        "validation_only": True,
        "lens_parameters": asdict(params),
        "hybrid_geometry": {
            "map": "azimuthal plane z=0",
            "lens": "upper half of a sphere; lower half is cut by the map plane",
            "centre_km": list(params.centre_km),
            "radius_km": params.radius_km,
            "exterior_index": 1.0,
            "ground_boundary": "ray invalid after return below z=0",
        },
        "diagnostic_component_alias": (
            "active_field_* is the lens contribution; legacy ring_path_* fields "
            "contain the same values for schema compatibility"
        ),
        "grid": {
            "candidate_observer_count": len(observers),
            "minimum_altitude_deg": minimum_altitude_deg,
        },
        "workers_used": workers,
        "integration": asdict(integration),
        "c2_solar_disk": fitted_c2,
        "c3_celestial_poles": fitted_c3,
        "baseline_n_equals_1": {
            "c2_solar_disk": baseline_c2,
            "c3_celestial_poles": baseline_c3,
        },
        "comparison_to_n_equals_1": _comparison_to_baseline(
            fitted_c2,
            baseline_c2,
            fitted_c3,
            baseline_c3,
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family",
        choices=("luneburg", "maxwell"),
        default="luneburg",
    )
    parser.add_argument("--radius-km", type=float, default=DEFAULT_DOME_RADIUS_KM)
    parser.add_argument("--centre-z-km", type=float, default=0.0)
    parser.add_argument("--n0", type=float, default=1.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-path-km", type=float, default=500_000.0)
    parser.add_argument("--rtol", type=float, default=1e-4)
    parser.add_argument("--atol", type=float, default=1e-7)
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument(
        "--solar-radius-deg",
        type=float,
        default=DEFAULT_SOLAR_RADIUS_DEG,
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params = LensFieldParams(
        family=args.family,
        radius_km=args.radius_km,
        n0=args.n0,
        centre_km=(0.0, 0.0, args.centre_z_km),
    )
    integration = IntegrationOptions(
        max_path_km=args.max_path_km,
        rtol=args.rtol,
        atol=args.atol,
    )
    print(f"Walidacja v2: {params}")
    payload = validate_lens_candidate(
        params,
        integration=integration,
        workers=args.workers,
        minimum_altitude_deg=args.minimum_altitude_deg,
        solar_radius_deg=args.solar_radius_deg,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    comparison = payload["comparison_to_n_equals_1"]
    print(
        "C-2 zmiana RMS wzgledem n=1 = "
        f"{comparison['c2_solar_disk']['mean_centre_rms_relative_change']}"
    )
    for target_id, result in comparison["c3_celestial_poles"].items():
        print(
            f"C-3 {target_id}: zmiana RMS={result['rms_relative_change']}; "
            f"wszystkie promienie w przod={result['fitted_all_rays_forward']}"
        )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
