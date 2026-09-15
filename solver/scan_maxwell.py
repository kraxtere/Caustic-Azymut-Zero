"""Run the pre-registered one-dimensional Maxwell mirror z0 scan."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np

from .scan_luneburg import build_scan_groups
from .validate_maxwell import (
    DEFAULT_RADIUS_KM,
    DEFAULT_RESTARTS,
    DEFAULT_SEEDS,
    _summarise,
    apply_maxwell_gate,
    evaluate_maxwell,
    evaluate_n_equals_one,
)
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG


MODEL_STATUS = "v2-maxwell-z0-scan-preregistered"
DEFAULT_Z0_FRACTIONS = (-0.40, -0.25, -0.10, 0.10, 0.25, 0.40, 0.0)


def parse_float_list(value: str) -> tuple[float, ...]:
    try:
        values = tuple(float(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected comma-separated numbers") from error
    if not values or any(not math.isfinite(item) for item in values):
        raise argparse.ArgumentTypeError("expected finite scan values")
    if len(set(values)) != len(values):
        raise argparse.ArgumentTypeError("z0 fractions must be unique")
    return values


def build_z0_candidates(
    radius_km: float = DEFAULT_RADIUS_KM,
    fractions: Sequence[float] = DEFAULT_Z0_FRACTIONS,
) -> tuple[float, ...]:
    if not math.isfinite(radius_km) or radius_km <= 0.0:
        raise ValueError("radius_km must be finite and positive")
    values = tuple(float(value) for value in fractions)
    if values != DEFAULT_Z0_FRACTIONS:
        raise ValueError("the pre-registered z0 scan values cannot be changed")
    return tuple(radius_km * value for value in values)


def _checkpoint(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_z0_scan(
    output: Path,
    *,
    radius_km: float = DEFAULT_RADIUS_KM,
    restarts: int = DEFAULT_RESTARTS,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, object]:
    matches_contract = bool(
        math.isclose(radius_km, DEFAULT_RADIUS_KM, rel_tol=0.0, abs_tol=1e-9)
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
    z0_values = build_z0_candidates(radius_km)
    solar_groups, pole_groups = build_scan_groups(
        minimum_altitude_deg,
        solar_radius_deg,
    )
    baseline = {
        "solar_centres": _summarise(solar_groups, evaluate_n_equals_one),
        "celestial_poles": _summarise(pole_groups, evaluate_n_equals_one),
    }
    payload: dict[str, object] = {
        "schema_version": 1,
        "model": "maxwell-mirror-v2-preregistered-z0-scan",
        "status": "running",
        "pre_registered_contract": "docs/V2_MAXWELL_Z0_SCAN.md",
        "matches_pre_registered_contract": matches_contract,
        "design": {
            "radius_km": radius_km,
            "z0_fractions_of_radius": list(DEFAULT_Z0_FRACTIONS),
            "candidate_count": len(z0_values),
            "solar_centre_count": len(solar_groups),
            "pole_count": len(pole_groups),
            "full_solar_limb_c2_included": False,
            "restarts_per_seed": restarts,
            "seeds": list(seeds),
            "comparison_metric": "RMS observed-vs-predicted direction in degrees",
        },
        "baseline_n_equals_1": baseline,
        "candidates": [],
        "qualifying_candidates": [],
    }
    _checkpoint(output, payload)

    records: list[dict[str, object]] = payload["candidates"]
    qualifiers: list[int] = payload["qualifying_candidates"]
    for candidate_id, centre_z_km in enumerate(z0_values, start=1):
        centre = np.array([0.0, 0.0, centre_z_km])
        evaluator = lambda group: evaluate_maxwell(
            group,
            radius_km,
            centre,
            seeds,
            restarts,
        )
        metrics = {
            "solar_centres": _summarise(solar_groups, evaluator),
            "celestial_poles": _summarise(pole_groups, evaluator),
        }
        gate = apply_maxwell_gate(metrics, baseline, radius_km)
        gate["checks"] = {
            "matches_pre_registered_contract": matches_contract,
            **gate["checks"],
        }
        gate["passed"] = all(gate["checks"].values())
        record = {
            "candidate_id": candidate_id,
            "radius_km": radius_km,
            "centre_z_km": centre_z_km,
            "z0_fraction_of_radius": centre_z_km / radius_km,
            "metrics": metrics,
            "promotion_gate": gate,
        }
        records.append(record)
        if gate["passed"]:
            qualifiers.append(candidate_id)
        _checkpoint(output, payload)
        print(
            f"[{candidate_id}/{len(z0_values)}] z0/R="
            f"{centre_z_km / radius_km:+.2f}: "
            f"{'PASS' if gate['passed'] else 'FAIL'}"
        )

    payload["status"] = "completed"
    payload["completed_candidate_count"] = len(records)
    payload["qualifying_candidate_count"] = len(qualifiers)
    _checkpoint(output, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius-km", type=float, default=DEFAULT_RADIUS_KM)
    parser.add_argument("--restarts", type=int, default=DEFAULT_RESTARTS)
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument("--solar-radius-deg", type=float, default=DEFAULT_SOLAR_RADIUS_DEG)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_z0_scan(
        args.output,
        radius_km=args.radius_km,
        restarts=args.restarts,
        minimum_altitude_deg=args.minimum_altitude_deg,
        solar_radius_deg=args.solar_radius_deg,
    )
    print(
        f"Zakonczono: {payload['qualifying_candidate_count']}/"
        f"{payload['completed_candidate_count']} PASS"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
