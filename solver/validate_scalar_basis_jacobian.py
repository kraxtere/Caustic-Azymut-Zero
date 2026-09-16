"""Validate finite-difference ray sensitivities for the scalar n(x) basis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .field_lens import LensFieldParams
from .maxwell_numeric import trace_local_maxwell_to_central_angle
from .validate_maxwell_c2 import SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM


BASE_DIPOLES = (0.0, 0.2, 0.4)
STEP = 0.02
MAXIMUM_RELATIVE_DIFFERENCE = 0.01
BASIS_TERM = (1, 1)


def _unit(value: np.ndarray) -> np.ndarray:
    return value / np.linalg.norm(value)


def _state(dipole: float, coefficient: float):
    radius = SELECTED_RADIUS_KM
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    position = centre + radius * np.array([0.10, -0.07, -0.20])
    direction = _unit(np.array([0.40, 0.20, 0.90]))
    params = LensFieldParams(
        "maxwell",
        radius,
        centre_km=tuple(centre),
        dipole_epsilon=dipole,
        scalar_basis_terms=((BASIS_TERM[0], BASIS_TERM[1], coefficient),),
    )
    return trace_local_maxwell_to_central_angle(position, direction, params, 1.1)


def _derivative(dipole: float, step: float):
    minus = _state(dipole, -step)
    plus = _state(dipole, step)
    return (
        (plus.point_xyz - minus.point_xyz) / (2.0 * step),
        (plus.direction_xyz - minus.direction_xyz) / (2.0 * step),
    )


def _relative(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.linalg.norm(first - second) / max(np.linalg.norm(second), 1e-15))


def run(output: Path) -> dict[str, object]:
    records = []
    for dipole in BASE_DIPOLES:
        coarse_point, coarse_direction = _derivative(dipole, STEP)
        fine_point, fine_direction = _derivative(dipole, STEP / 2.0)
        point_difference = _relative(coarse_point, fine_point)
        direction_difference = _relative(coarse_direction, fine_direction)
        checks = {
            "finite_derivatives": bool(
                np.all(np.isfinite(fine_point)) and np.all(np.isfinite(fine_direction))
            ),
            "point_derivative_converged": point_difference <= MAXIMUM_RELATIVE_DIFFERENCE,
            "direction_derivative_converged": direction_difference <= MAXIMUM_RELATIVE_DIFFERENCE,
        }
        records.append({
            "dipole_epsilon": dipole,
            "coarse_point_derivative": coarse_point.tolist(),
            "fine_point_derivative": fine_point.tolist(),
            "coarse_direction_derivative": coarse_direction.tolist(),
            "fine_direction_derivative": fine_direction.tolist(),
            "point_relative_difference": point_difference,
            "direction_relative_difference": direction_difference,
            "gate": {"passed": all(checks.values()), "checks": checks},
        })
    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_SCALAR_NX_SVD_CONTRACT.md",
        "basis_term": list(BASIS_TERM),
        "step": STEP,
        "maximum_relative_difference": MAXIMUM_RELATIVE_DIFFERENCE,
        "records": records,
        "gate": {"passed": all(record["gate"]["passed"] for record in records)},
        "scope": "technical finite-difference gate; not an observational fit or no-go result",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.output)
    print(f"Technical SVD gate: {'PASS' if payload['gate']['passed'] else 'FAIL'}")
    for record in payload["records"]:
        print(record["dipole_epsilon"], record["point_relative_difference"], record["direction_relative_difference"])


if __name__ == "__main__":
    main()
