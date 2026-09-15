"""Quantify smooth and discrete parts of Maxwell's seasonal scale error.

The diagnostic uses one observer cohort for every March, June and December
target. For each target it compares the selected branch assignment with a
forced continuation on the all-direct ``P`` branch. Counterfactual backward
fits are retained and their physical admissibility is reported separately.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Sequence

import numpy as np

from .ephemeris import MeeusLowPrecision
from .maxwell_mirror import (
    maxwell_direction_to_auxiliary_target,
    maxwell_great_circle_constraint,
    triangulate_maxwell_great_circles,
)
from .validate_maxwell import (
    DEFAULT_RESTARTS,
    DEFAULT_SEEDS,
    FORWARD_TOLERANCE,
    GROUND_TOLERANCE_KM,
    _direction_rms_deg,
    evaluate_maxwell,
)
from .validate_maxwell_c2 import (
    SAMPLE_IDS,
    SELECTED_CENTRE_Z_KM,
    SELECTED_RADIUS_KM,
    _disk_shape,
    build_c2_tracks,
)
from .validate_v1 import TargetGroup, build_target_group, solar_disk_samples


MODEL_STATUS = "v2-maxwell-forced-branch-continuation-preregistered"
TRACK_IDS = ("march_equinox", "june_solstice", "december_solstice")


def common_observer_cohort(
    tracks: Sequence[dict[str, object]],
) -> tuple[tuple[float, float], ...]:
    """Return the ordered observer intersection shared by every input track."""

    if not tracks:
        raise ValueError("at least one track is required")
    common = set(map(tuple, tracks[0]["fixed_observers_deg"]))
    for track in tracks[1:]:
        common &= set(map(tuple, track["fixed_observers_deg"]))
    if len(common) < 2:
        raise ValueError("common observer cohort needs at least two observers")
    return tuple(sorted((float(lat), float(lon)) for lat, lon in common))


def build_common_cohort_tracks(
    minimum_altitude_deg: float = 2.0,
) -> tuple[dict[str, object], ...]:
    """Rebuild all C-2 targets using one observer cohort across seasons."""

    source_tracks = build_c2_tracks(minimum_altitude_deg)
    cohort = common_observer_cohort(source_tracks)
    ephemeris = MeeusLowPrecision()
    rebuilt = []
    for track in source_tracks:
        moments = []
        for moment in track["moments"]:
            instant = datetime.fromisoformat(str(moment["timestamp_utc"]))
            angular_radius_deg = ephemeris.sun_angular_radius_deg(instant)
            samples = solar_disk_samples(
                ephemeris.sun_radec(instant), angular_radius_deg
            )
            moments.append(
                {
                    "timestamp_utc": instant.isoformat(),
                    "input_angular_radius_deg": angular_radius_deg,
                    "groups": {
                        sample_id: build_target_group(
                            f"{track['track_id']}:{sample_id}:common-cohort",
                            samples[sample_id],
                            instant,
                            cohort,
                        )
                        for sample_id in SAMPLE_IDS
                    },
                }
            )
        rebuilt.append(
            {
                "track_id": track["track_id"],
                "fixed_observer_count": len(cohort),
                "fixed_observers_deg": [list(observer) for observer in cohort],
                "moments": moments,
            }
        )
    return tuple(rebuilt)


def evaluate_fixed_branches(
    group: TargetGroup,
    radius_km: float,
    centre_km: np.ndarray,
    reflection_parities: Sequence[bool],
) -> dict[str, object]:
    """Fit a prescribed ``P/JPJ`` assignment without branch optimisation."""

    parities = tuple(bool(value) for value in reflection_parities)
    if len(parities) != len(group.origins):
        raise ValueError("reflection_parities must match observer count")
    constraints = tuple(
        maxwell_great_circle_constraint(origin, direction, radius_km, centre_km)
        for origin, direction in zip(group.origins, group.directions, strict=True)
    )
    fit = triangulate_maxwell_great_circles(
        constraints,
        reflection_parities=parities,
        centre_xyz=centre_km,
    )
    predicted = []
    central_angles = []
    signed_sines = []
    for origin, constraint, reflected in zip(
        group.origins, constraints, parities, strict=True
    ):
        direction, angle = maxwell_direction_to_auxiliary_target(
            origin,
            fit.point_xyzw,
            radius_km,
            reflected_branch=reflected,
            centre_xyz=centre_km,
        )
        predicted.append(direction)
        central_angles.append(angle)
        unfolded_target = fit.point_xyzw.copy()
        if reflected:
            unfolded_target[3] *= -1.0
        signed_sines.append(
            float(np.dot(constraint.sphere_tangent, unfolded_target) / radius_km)
        )
    direction_rms, residuals = _direction_rms_deg(group.directions, predicted)
    all_forward = bool(
        fit.forward_observation_count == fit.observation_count
        and all(value >= -FORWARD_TOLERANCE for value in signed_sines)
    )
    source_above_map = bool(fit.point_xyz[2] >= -GROUND_TOLERANCE_KM)
    return {
        "fit_valid": True,
        "physically_admissible": bool(
            fit.inside_mirror and source_above_map and all_forward
        ),
        "common_point_km": fit.point_xyz.tolist(),
        "common_point_s3_km": fit.point_xyzw.tolist(),
        "native_s3_plane_rms_km": fit.rms_plane_distance,
        "direction_rms_deg": direction_rms,
        "maximum_direction_residual_deg": max(residuals),
        "all_rays_forward": all_forward,
        "minimum_forward_sine": min(signed_sines),
        "minimum_central_angle_rad": min(central_angles),
        "maximum_central_angle_rad": max(central_angles),
        "inside_mirror": fit.inside_mirror,
        "source_above_map": source_above_map,
        "spectral_gap": float(fit.eigenvalues[1] - fit.eigenvalues[0]),
        "reflected_branch_count": sum(parities),
        "reflection_parities": list(parities),
    }


def multiplicative_decomposition(
    selected_december_diameter: float,
    direct_december_diameter: float,
    direct_june_diameter: float,
    expected_input_ratio: float,
) -> dict[str, float]:
    """Split the residual ratio into direct continuation and branch factors."""

    values = (
        selected_december_diameter,
        direct_december_diameter,
        direct_june_diameter,
        expected_input_ratio,
    )
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        raise ValueError("diameters and expected_input_ratio must be positive")
    total = selected_december_diameter / direct_june_diameter / expected_input_ratio
    smooth = direct_december_diameter / direct_june_diameter / expected_input_ratio
    branch = selected_december_diameter / direct_december_diameter
    output = {
        "total_unexplained_ratio": total,
        "total_unexplained_fraction": total - 1.0,
        "smooth_direct_continuation_ratio": smooth,
        "smooth_direct_continuation_fraction": smooth - 1.0,
        "discrete_branch_multiplier": branch,
        "branch_increment_after_smooth_fraction_points": total - smooth,
        "factorisation_identity_error": total - smooth * branch,
    }
    if total > 0.0 and not math.isclose(total, 1.0) and smooth > 0.0 and branch > 0.0:
        denominator = math.log(total)
        output["smooth_log_share"] = math.log(smooth) / denominator
        output["branch_log_share"] = math.log(branch) / denominator
    return output


def _shape_from_fixed_targets(
    targets: dict[str, dict[str, object]],
) -> dict[str, float] | None:
    compatible = {
        name: {
            "valid": bool(targets[name].get("fit_valid")),
            "common_point_km": targets[name].get("common_point_km"),
        }
        for name in SAMPLE_IDS
    }
    return _disk_shape(compatible)


def _track_mean(track: dict[str, object], mode: str) -> float:
    diameters = [
        moment[mode]["reconstructed_disk"]["mean_diameter_km"]
        for moment in track["moments"]
        if moment[mode]["reconstructed_disk"] is not None
    ]
    if len(diameters) != len(track["moments"]):
        raise ValueError(f"{mode} did not produce every disk")
    return float(np.mean(diameters))


def run_forced_continuation(
    output: Path,
    *,
    radius_km: float = SELECTED_RADIUS_KM,
    centre_z_km: float = SELECTED_CENTRE_Z_KM,
    restarts: int = DEFAULT_RESTARTS,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    minimum_altitude_deg: float = 2.0,
) -> dict[str, object]:
    """Run the pre-registered common-cohort continuation diagnostic."""

    tracks = build_common_cohort_tracks(minimum_altitude_deg)
    centre = np.array([0.0, 0.0, centre_z_km])
    output_tracks = []
    for track in tracks:
        moments = []
        for moment in track["moments"]:
            selected_targets = {}
            direct_targets = {}
            selectors = {}
            for sample_id in SAMPLE_IDS:
                group = moment["groups"][sample_id]
                selected = evaluate_maxwell(
                    group, radius_km, centre, seeds, restarts
                )
                if "selected_reflection_parities" not in selected:
                    raise ValueError(
                        f"branch selection failed for {group.target_id}"
                    )
                parities = tuple(selected["selected_reflection_parities"])
                selected_targets[sample_id] = evaluate_fixed_branches(
                    group, radius_km, centre, parities
                )
                direct_targets[sample_id] = evaluate_fixed_branches(
                    group, radius_km, centre, (False,) * len(group.origins)
                )
                selectors[sample_id] = {
                    "restart_seed_consensus": selected[
                        "restart_seed_consensus"
                    ],
                    "restart_branch_assignment_consensus": selected[
                        "restart_branch_assignment_consensus"
                    ],
                    "maximum_seed_point_spread_s3_km": selected[
                        "maximum_seed_point_spread_s3_km"
                    ],
                    "selected_reflection_parities": list(parities),
                    "selected_reflected_branch_count": sum(parities),
                }
            moments.append(
                {
                    "timestamp_utc": moment["timestamp_utc"],
                    "input_angular_radius_deg": moment[
                        "input_angular_radius_deg"
                    ],
                    "branch_selector": selectors,
                    "selected_branch": {
                        "targets": selected_targets,
                        "reconstructed_disk": _shape_from_fixed_targets(
                            selected_targets
                        ),
                    },
                    "forced_direct_branch": {
                        "targets": direct_targets,
                        "reconstructed_disk": _shape_from_fixed_targets(
                            direct_targets
                        ),
                    },
                }
            )
        output_tracks.append(
            {
                "track_id": track["track_id"],
                "fixed_observer_count": track["fixed_observer_count"],
                "fixed_observers_deg": track["fixed_observers_deg"],
                "moments": moments,
            }
        )

    by_id = {track["track_id"]: track for track in output_tracks}
    means = {
        track_id: {
            "selected_branch_mean_diameter_km": _track_mean(
                by_id[track_id], "selected_branch"
            ),
            "forced_direct_mean_diameter_km": _track_mean(
                by_id[track_id], "forced_direct_branch"
            ),
            "mean_input_angular_diameter_deg": float(
                np.mean(
                    [
                        2.0 * moment["input_angular_radius_deg"]
                        for moment in by_id[track_id]["moments"]
                    ]
                )
            ),
        }
        for track_id in TRACK_IDS
    }
    expected_ratio = (
        means["december_solstice"]["mean_input_angular_diameter_deg"]
        / means["june_solstice"]["mean_input_angular_diameter_deg"]
    )
    decomposition = multiplicative_decomposition(
        means["december_solstice"]["selected_branch_mean_diameter_km"],
        means["december_solstice"]["forced_direct_mean_diameter_km"],
        means["june_solstice"]["forced_direct_mean_diameter_km"],
        expected_ratio,
    )
    selectors = [
        selector
        for track in output_tracks
        for moment in track["moments"]
        for selector in moment["branch_selector"].values()
    ]
    payload = {
        "schema_version": 1,
        "model": MODEL_STATUS,
        "status": "completed",
        "pre_registered_contract": (
            "docs/V2_MAXWELL_FORCED_BRANCH_CONTINUATION.md"
        ),
        "design": {
            "radius_km": radius_km,
            "centre_z_km": centre_z_km,
            "observer_cohort_controlled": True,
            "common_observer_count": tracks[0]["fixed_observer_count"],
            "common_observers_deg": tracks[0]["fixed_observers_deg"],
            "restarts_per_seed": restarts,
            "seeds": list(seeds),
            "forced_path": "all-direct P branch; backward fits retained",
            "rk45_used": False,
        },
        "all_selected_branch_assignments_agree_across_seeds": all(
            bool(selector["restart_branch_assignment_consensus"])
            for selector in selectors
        ),
        "seasonal_track_means": means,
        "december_to_june_decomposition": decomposition,
        "daily_tracks": output_tracks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--radius-km", type=float, default=SELECTED_RADIUS_KM)
    parser.add_argument("--centre-z-km", type=float, default=SELECTED_CENTRE_Z_KM)
    parser.add_argument("--restarts", type=int, default=DEFAULT_RESTARTS)
    args = parser.parse_args()
    payload = run_forced_continuation(
        args.output,
        radius_km=args.radius_km,
        centre_z_km=args.centre_z_km,
        restarts=args.restarts,
    )
    result = payload["december_to_june_decomposition"]
    print(
        "Wspolna kohorta: "
        f"{payload['design']['common_observer_count']} obserwatorow"
    )
    print(
        "Niewyjasniony czynnik: "
        f"{result['total_unexplained_ratio']:.9f}; "
        "gladka kontynuacja: "
        f"{result['smooth_direct_continuation_ratio']:.9f}; "
        f"galaz: {result['discrete_branch_multiplier']:.9f}"
    )
    print(f"Zapisano: {args.output}")


if __name__ == "__main__":
    main()
