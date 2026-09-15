"""Audit Maxwell branch scale, aperture ratios, and winding interpretation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .geometry_flat import R_MAP


def legendre_modes(declination_deg: float) -> dict[str, float]:
    """Return the first three axial Legendre modes at ``x=sin(delta)``."""

    x = math.sin(math.radians(float(declination_deg)))
    return {
        "x_sin_delta": x,
        "p1": x,
        "p2": (3.0 * x**2 - 1.0) / 2.0,
        "p3": (5.0 * x**3 - 3.0 * x) / 2.0,
    }


def effective_image_distance_km(
    reconstructed_diameter_km: float,
    input_angular_radius_deg: float,
) -> float:
    """Return diameter divided by the full input angular diameter in radians."""

    diameter = float(reconstructed_diameter_km)
    angular_diameter = math.radians(2.0 * float(input_angular_radius_deg))
    if not math.isfinite(diameter) or diameter <= 0.0:
        raise ValueError("reconstructed_diameter_km must be positive")
    if not math.isfinite(angular_diameter) or angular_diameter <= 0.0:
        raise ValueError("input angular diameter must be positive")
    return diameter / angular_diameter


def disk_uses_one_branch_signature(
    selectors: dict[str, dict[str, object]],
) -> bool:
    """Check whether centre and four limbs use exactly the same parity vector."""

    signatures = {
        tuple(bool(value) for value in selector["selected_reflection_parities"])
        for selector in selectors.values()
    }
    return len(signatures) == 1


def analyse(payload: dict[str, object]) -> dict[str, object]:
    map_diameter = 2.0 * R_MAP
    records = []
    central_angles = []
    parity_values = []
    for track in payload["daily_tracks"]:
        for moment in track["moments"]:
            radius_deg = float(moment["input_angular_radius_deg"])
            selected_shape = moment["selected_branch"]["reconstructed_disk"]
            direct_shape = moment["forced_direct_branch"]["reconstructed_disk"]
            selected_diameter = float(selected_shape["mean_diameter_km"])
            direct_diameter = float(direct_shape["mean_diameter_km"])
            selected_effective = effective_image_distance_km(
                selected_diameter, radius_deg
            )
            direct_effective = effective_image_distance_km(
                direct_diameter, radius_deg
            )
            for target in moment["selected_branch"]["targets"].values():
                central_angles.extend(
                    (
                        float(target["minimum_central_angle_rad"]),
                        float(target["maximum_central_angle_rad"]),
                    )
                )
                parity_values.extend(target["reflection_parities"])
            records.append(
                {
                    "track_id": track["track_id"],
                    "timestamp_utc": moment["timestamp_utc"],
                    "selected_to_direct_disk_ratio": (
                        selected_diameter / direct_diameter
                    ),
                    "selected_effective_image_distance_km": selected_effective,
                    "direct_effective_image_distance_km": direct_effective,
                    "selected_effective_distance_to_map_diameter_ratio": (
                        selected_effective / map_diameter
                    ),
                    "direct_effective_distance_to_map_diameter_ratio": (
                        direct_effective / map_diameter
                    ),
                    "one_branch_signature_across_disk": (
                        disk_uses_one_branch_signature(moment["branch_selector"])
                    ),
                    "all_selectors_consensus": all(
                        bool(selector["restart_branch_assignment_consensus"])
                        for selector in moment["branch_selector"].values()
                    ),
                    "selected_reflected_branch_counts": {
                        sample: int(selector["selected_reflected_branch_count"])
                        for sample, selector in moment["branch_selector"].items()
                    },
                }
            )

    factor = float(
        payload["december_to_june_decomposition"]["discrete_branch_multiplier"]
    )
    nearest_integer = round(factor)
    multipole_probes = {
        str(declination): legendre_modes(declination)
        for declination in (-23.44, -11.7, 0.0, 11.7, 23.44)
    }
    return {
        "schema_version": 1,
        "status": "completed",
        "source": "solver/results/v2-maxwell-forced-branch-continuation.json",
        "map_diameter_km": map_diameter,
        "records": records,
        "near_integer_branch_factor": {
            "value": factor,
            "nearest_integer": nearest_integer,
            "relative_distance_to_nearest_integer": abs(factor - nearest_integer)
            / nearest_integer,
        },
        "winding_audit": {
            "winding_index_exists_in_current_model": False,
            "reflection_state_is_boolean": all(
                isinstance(value, bool) for value in parity_values
            ),
            "all_reported_central_angles_within_first_interval_0_to_pi": all(
                0.0 <= angle <= math.pi for angle in central_angles
            ),
            "maximum_reported_central_angle_rad": max(central_angles),
            "conclusion": (
                "The near-six aggregate is not a winding number in this "
                "first-interval, boolean P/JPJ representation."
            ),
        },
        "map_chord_ratio_policy": {
            "status": "diagnostic-only",
            "reason": (
                "An effective image distance is a local angular-to-linear "
                "scale and is not bounded by the physical aperture diameter "
                "without a separately derived Maxwell-map magnification bound."
            ),
        },
        "multipole_probe": {
            "values": multipole_probes,
            "p2_equal_at_opposite_solstices": math.isclose(
                multipole_probes["-23.44"]["p2"],
                multipole_probes["23.44"]["p2"],
                rel_tol=0.0,
                abs_tol=1e-15,
            ),
            "p3_to_p1_ratio_at_23_44": (
                multipole_probes["23.44"]["p3"]
                / multipole_probes["23.44"]["p1"]
            ),
            "p3_to_p1_ratio_at_11_7": (
                multipole_probes["11.7"]["p3"]
                / multipole_probes["11.7"]["p1"]
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = analyse(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        "Mnoznik bliski liczbie calkowitej: "
        f"{payload['near_integer_branch_factor']['value']:.9f}; "
        "indeks nawiniecia: nieobecny w modelu"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
