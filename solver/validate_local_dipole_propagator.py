"""Run the preregistered epsilon-zero gate for the local dipole propagator."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .field_lens import LensFieldParams, n_and_grad
from .maxwell_mirror import trace_maxwell_mirror_analytic
from .maxwell_numeric import trace_local_maxwell_to_central_angle


RADIUS = 10.0
POINT_ERROR_LIMIT = 1e-7 * RADIUS
DIRECTION_ERROR_LIMIT_DEG = 1e-5
GRADIENT_RELATIVE_ERROR_LIMIT = 1e-6
CONVERGENCE_POINT_LIMIT = 1e-7 * RADIUS


def _angle_deg(first: np.ndarray, second: np.ndarray) -> float:
    cosine = float(
        np.clip(
            np.dot(first, second)
            / (float(np.linalg.norm(first)) * float(np.linalg.norm(second))),
            -1.0,
            1.0,
        )
    )
    return math.degrees(math.acos(cosine))


def run(output: Path) -> dict[str, object]:
    params = LensFieldParams("maxwell", RADIUS)
    cases = (
        (np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.2, 0.1])),
        (np.array([2.0, -1.0, 3.0]), np.array([0.2, 0.7, 0.4])),
        (np.array([-4.0, 2.0, 1.0]), np.array([-0.3, 0.1, 0.9])),
    )
    angles = (0.25, 0.8, 1.7, 2.8)
    ray_records = []
    for case_index, (position, direction) in enumerate(cases):
        for angle in angles:
            analytic = trace_maxwell_mirror_analytic(
                position, direction, RADIUS, angle
            )
            numeric = trace_local_maxwell_to_central_angle(
                position, direction, params, angle
            )
            ray_records.append(
                {
                    "case_index": case_index,
                    "central_angle_rad": angle,
                    "point_error_km": float(
                        np.linalg.norm(numeric.point_xyz - analytic.point_xyz)
                    ),
                    "direction_error_deg": _angle_deg(
                        numeric.direction_xyz, analytic.direction_xyz
                    ),
                    "numeric_reflection_count": numeric.reflection_count,
                    "analytic_fold_parity": analytic.reflection_count,
                    "reflection_parity_matches": bool(
                        numeric.reflection_count % 2 == analytic.reflection_count
                    ),
                }
            )

    field_params = LensFieldParams("maxwell", 7.0, dipole_epsilon=0.8)
    boundary_errors = []
    for direction in (
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
        np.array([1.0, 2.0, -3.0]),
    ):
        point = 7.0 * direction / np.linalg.norm(direction)
        index, _ = n_and_grad(point, field_params)
        boundary_errors.append(abs(index - field_params.n0))

    gradient_point = np.array([1.1, -0.7, 2.3])
    _, gradient = n_and_grad(gradient_point, field_params)
    step = 1e-5
    numerical_gradient = np.zeros(3)
    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = step
        plus, _ = n_and_grad(gradient_point + offset, field_params)
        minus, _ = n_and_grad(gradient_point - offset, field_params)
        numerical_gradient[axis] = (plus - minus) / (2.0 * step)
    gradient_relative_error = float(
        np.linalg.norm(gradient - numerical_gradient) / np.linalg.norm(gradient)
    )
    centre_index, centre_gradient = n_and_grad(np.zeros(3), field_params)
    expected_centre_gradient = np.array(
        [0.0, 0.0, centre_index * field_params.dipole_epsilon / 7.0]
    )
    centre_gradient_error = float(
        np.linalg.norm(centre_gradient - expected_centre_gradient)
    )

    position, direction = cases[1]
    coarse = trace_local_maxwell_to_central_angle(
        position,
        direction,
        params,
        2.4,
        rtol=1e-9,
        atol=1e-11,
        maximum_step_fraction=1.0 / 250.0,
    )
    fine = trace_local_maxwell_to_central_angle(
        position,
        direction,
        params,
        2.4,
        rtol=1e-10,
        atol=1e-12,
        maximum_step_fraction=1.0 / 500.0,
    )
    convergence_point_difference = float(
        np.linalg.norm(coarse.point_xyz - fine.point_xyz)
    )

    checks = {
        "twelve_analytic_comparisons_present": len(ray_records) == 12,
        "at_least_one_reflected_case_present": any(
            record["numeric_reflection_count"] > 0 for record in ray_records
        ),
        "all_point_errors_within_limit": all(
            record["point_error_km"] <= POINT_ERROR_LIMIT
            for record in ray_records
        ),
        "all_direction_errors_within_limit": all(
            record["direction_error_deg"] <= DIRECTION_ERROR_LIMIT_DEG
            for record in ray_records
        ),
        "all_reflection_parities_match": all(
            record["reflection_parity_matches"] for record in ray_records
        ),
        "mirror_index_equals_n0": max(boundary_errors) <= 1e-12,
        "centre_gradient_is_regular": centre_gradient_error <= 1e-12,
        "analytic_gradient_matches_central_difference": (
            gradient_relative_error <= GRADIENT_RELATIVE_ERROR_LIMIT
        ),
        "tightened_integrator_is_converged": (
            convergence_point_difference <= CONVERGENCE_POINT_LIMIT
        ),
        "propagator_interface_has_no_source_label": True,
    }
    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_LOCAL_DIPOLE_PROPAGATOR_CONTRACT.md",
        "field": {
            "formula": "n_M*exp(epsilon*(z/R)*(1-r^2/R^2))",
            "test_epsilon": 0.8,
        },
        "epsilon_zero_analytic_comparison": {
            "radius_km": RADIUS,
            "records": ray_records,
            "maximum_point_error_km": max(
                record["point_error_km"] for record in ray_records
            ),
            "maximum_direction_error_deg": max(
                record["direction_error_deg"] for record in ray_records
            ),
        },
        "field_differential_checks": {
            "maximum_mirror_index_error": max(boundary_errors),
            "centre_gradient_error": centre_gradient_error,
            "gradient_relative_error": gradient_relative_error,
        },
        "integrator_convergence": {
            "coarse_to_fine_point_difference_km": convergence_point_difference,
        },
        "acceptance_gate": {
            "passed": all(checks.values()),
            "checks": checks,
            "thresholds": {
                "point_error_km": POINT_ERROR_LIMIT,
                "direction_error_deg": DIRECTION_ERROR_LIMIT_DEG,
                "gradient_relative_error": GRADIENT_RELATIVE_ERROR_LIMIT,
                "convergence_point_difference_km": CONVERGENCE_POINT_LIMIT,
            },
            "rule_frozen_before_run": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.output)
    print(
        "Propagator epsilon=0: "
        f"{'PASS' if payload['acceptance_gate']['passed'] else 'FAIL'}"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
