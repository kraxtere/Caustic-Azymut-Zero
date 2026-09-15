"""Run the pre-registered one-dimensional Maxwell mirror radius scan."""

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


MODEL_STATUS = "v2-maxwell-radius-scan-preregistered"
FIXED_CENTRE_Z_KM = 0.40 * DEFAULT_RADIUS_KM
DEFAULT_RADIUS_FRACTIONS = (1.05, 1.10, 1.20, 1.35, 1.50, 1.00)


def build_radius_candidates(
    base_radius_km: float = DEFAULT_RADIUS_KM,
    fractions: Sequence[float] = DEFAULT_RADIUS_FRACTIONS,
) -> tuple[float, ...]:
    if not math.isfinite(base_radius_km) or base_radius_km <= 0.0:
        raise ValueError("base_radius_km must be finite and positive")
    values = tuple(float(value) for value in fractions)
    if values != DEFAULT_RADIUS_FRACTIONS:
        raise ValueError("the pre-registered radius scan values cannot be changed")
    return tuple(base_radius_km * value for value in values)


def _checkpoint(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_radius_scan(
    output: Path,
    *,
    base_radius_km: float = DEFAULT_RADIUS_KM,
    centre_z_km: float = FIXED_CENTRE_Z_KM,
    restarts: int = DEFAULT_RESTARTS,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    minimum_altitude_deg: float = 2.0,
    solar_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> dict[str, object]:
    matches_contract = bool(
        math.isclose(base_radius_km, DEFAULT_RADIUS_KM, rel_tol=0.0, abs_tol=1e-9)
        and math.isclose(centre_z_km, FIXED_CENTRE_Z_KM, rel_tol=0.0, abs_tol=1e-9)
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
    radius_values = build_radius_candidates(base_radius_km)
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
        "model": "maxwell-mirror-v2-preregistered-radius-scan",
        "status": "running",
        "pre_registered_contract": "docs/V2_MAXWELL_RADIUS_SCAN.md",
        "matches_pre_registered_contract": matches_contract,
        "design": {
            "base_radius_km": base_radius_km,
            "fixed_centre_z_km": centre_z_km,
            "radius_fractions_of_base": list(DEFAULT_RADIUS_FRACTIONS),
            "candidate_count": len(radius_values),
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
    centre = np.array([0.0, 0.0, centre_z_km])
    for candidate_id, radius_km in enumerate(radius_values, start=1):
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
            "base_radius_km": base_radius_km,
            "radius_km": radius_km,
            "radius_fraction_of_base": radius_km / base_radius_km,
            "centre_z_km": centre_z_km,
            "z0_fraction_of_candidate_radius": centre_z_km / radius_km,
            "metrics": metrics,
            "promotion_gate": gate,
        }
        records.append(record)
        if gate["passed"]:
            qualifiers.append(candidate_id)
        _checkpoint(output, payload)
        print(
            f"[{candidate_id}/{len(radius_values)}] R/Rbase="
            f"{radius_km / base_radius_km:.2f}, "
            f"z0/R={centre_z_km / radius_km:.3f}: "
            f"{'PASS' if gate['passed'] else 'FAIL'}"
        )

    payload["status"] = "completed"
    payload["completed_candidate_count"] = len(records)
    payload["qualifying_candidate_count"] = len(qualifiers)
    _checkpoint(output, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-radius-km", type=float, default=DEFAULT_RADIUS_KM)
    parser.add_argument("--centre-z-km", type=float, default=FIXED_CENTRE_Z_KM)
    parser.add_argument("--restarts", type=int, default=DEFAULT_RESTARTS)
    parser.add_argument("--minimum-altitude-deg", type=float, default=2.0)
    parser.add_argument("--solar-radius-deg", type=float, default=DEFAULT_SOLAR_RADIUS_DEG)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_radius_scan(
        args.output,
        base_radius_km=args.base_radius_km,
        centre_z_km=args.centre_z_km,
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
