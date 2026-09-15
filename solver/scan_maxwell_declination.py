"""Run the pre-registered Maxwell transfer-scale scan over declination."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .ephemeris import RaDec, gmst_deg
from .validate_maxwell import DEFAULT_RESTARTS, DEFAULT_SEEDS, evaluate_maxwell
from .validate_maxwell_c2 import (
    SAMPLE_IDS,
    SELECTED_CENTRE_Z_KM,
    SELECTED_RADIUS_KM,
    _disk_shape,
)
from .validate_v1 import (
    DEFAULT_SOLAR_RADIUS_DEG,
    _visible_observers,
    build_target_group,
    observer_grid,
    solar_disk_samples,
)


DECLINATIONS_DEG = (
    -23.44,
    -17.58,
    -11.72,
    -5.86,
    0.0,
    5.86,
    11.72,
    17.58,
    23.44,
)
REFERENCE_MOMENT = datetime(2026, 3, 20, 13, 0, tzinfo=timezone.utc)
MINIMUM_LINEAR_R_SQUARED = 0.95


def build_declination_groups(
    angular_radius_deg: float = DEFAULT_SOLAR_RADIUS_DEG,
) -> tuple[tuple[float, dict[str, object]], ...]:
    right_ascension = gmst_deg(REFERENCE_MOMENT)
    samples = {
        declination: solar_disk_samples(
            RaDec(ra_deg=right_ascension, dec_deg=declination),
            angular_radius_deg,
        )
        for declination in DECLINATIONS_DEG
    }
    all_targets = [
        target
        for declination in DECLINATIONS_DEG
        for target in samples[declination].values()
    ]
    observers = _visible_observers(
        all_targets,
        REFERENCE_MOMENT,
        observer_grid(),
        2.0,
    )
    return tuple(
        (
            declination,
            {
                "observer_coordinates_deg": observers,
                "groups": {
                    sample_id: build_target_group(
                        f"declination_{declination:+.2f}:{sample_id}",
                        samples[declination][sample_id],
                        REFERENCE_MOMENT,
                        observers,
                    )
                    for sample_id in SAMPLE_IDS
                },
            },
        )
        for declination in DECLINATIONS_DEG
    )


def _trend(values: list[float]) -> dict[str, object]:
    x = np.asarray(DECLINATIONS_DEG, dtype=float)
    y = np.asarray(values, dtype=float)
    differences = np.diff(y)
    increasing = bool(np.all(differences > 0.0))
    decreasing = bool(np.all(differences < 0.0))
    coefficients = np.polyfit(x, y, 1)
    fitted = np.polyval(coefficients, x)
    total = float(np.sum((y - np.mean(y)) ** 2))
    residual = float(np.sum((y - fitted) ** 2))
    r_squared = 1.0 - residual / total if total > 0.0 else 1.0
    return {
        "strictly_monotonic": increasing or decreasing,
        "direction": "increasing" if increasing else "decreasing" if decreasing else None,
        "linear_slope_km_per_radian_per_degree": float(coefficients[0]),
        "linear_r_squared": r_squared,
        "minimum_required_linear_r_squared": MINIMUM_LINEAR_R_SQUARED,
        "hypothesis_supported": bool(
            (increasing or decreasing) and r_squared >= MINIMUM_LINEAR_R_SQUARED
        ),
    }


def run_declination_scan(output: Path) -> dict[str, object]:
    design = build_declination_groups()
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    records = []
    transfer_scales = []
    complete = True
    for declination, item in design:
        targets = {
            sample_id: evaluate_maxwell(
                item["groups"][sample_id],
                SELECTED_RADIUS_KM,
                centre,
                DEFAULT_SEEDS,
                DEFAULT_RESTARTS,
            )
            for sample_id in SAMPLE_IDS
        }
        shape = _disk_shape(targets)
        valid = bool(
            shape is not None
            and all(target.get("restart_seed_consensus") for target in targets.values())
            and all(
                target.get("restart_branch_assignment_consensus")
                for target in targets.values()
            )
        )
        transfer_scale = (
            shape["mean_diameter_km"]
            / (2.0 * math.radians(DEFAULT_SOLAR_RADIUS_DEG))
            if shape is not None
            else None
        )
        if transfer_scale is not None:
            transfer_scales.append(transfer_scale)
        complete = complete and valid
        records.append(
            {
                "declination_deg": declination,
                "valid": valid,
                "observer_count": len(item["observer_coordinates_deg"]),
                "input_angular_radius_deg": DEFAULT_SOLAR_RADIUS_DEG,
                "reconstructed_disk": shape,
                "normalised_transfer_scale_km_per_radian": transfer_scale,
                "minimum_forward_sine": min(
                    target.get("minimum_forward_sine", -math.inf)
                    for target in targets.values()
                ),
                "all_restart_points_agree": all(
                    target.get("restart_seed_consensus") for target in targets.values()
                ),
                "all_branch_assignments_agree": all(
                    target.get("restart_branch_assignment_consensus")
                    for target in targets.values()
                ),
                "targets": targets,
            }
        )
        print(f"delta={declination:+.2f} deg: {'OK' if valid else 'INVALID'}")

    trend = _trend(transfer_scales) if complete and len(transfer_scales) == 9 else None
    payload = {
        "schema_version": 1,
        "model": "maxwell-v2-declination-transfer-scale-scan",
        "status": "completed",
        "pre_registered_contract": "docs/V2_MAXWELL_DECLINATION_SCAN.md",
        "design": {
            "radius_km": SELECTED_RADIUS_KM,
            "centre_z_km": SELECTED_CENTRE_Z_KM,
            "declinations_deg": list(DECLINATIONS_DEG),
            "reference_moment_utc": REFERENCE_MOMENT.isoformat(),
            "input_angular_radius_deg": DEFAULT_SOLAR_RADIUS_DEG,
            "common_observer_count": records[0]["observer_count"] if records else 0,
            "samples_per_declination": list(SAMPLE_IDS),
            "seeds": list(DEFAULT_SEEDS),
            "restarts_per_seed": DEFAULT_RESTARTS,
        },
        "complete": complete,
        "records": records,
        "trend": trend,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run_declination_scan(args.output)
    supported = bool(payload.get("trend") and payload["trend"]["hypothesis_supported"])
    print(f"Hipoteza monotoniczna: {'SUPPORTED' if supported else 'NOT SUPPORTED'}")
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
