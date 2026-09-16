"""Probe the suspected scalar-field branch boundary with two-sided restarts."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import time
from pathlib import Path

import numpy as np

from .ephemeris import RaDec, gmst_deg
from .field_lens import LensFieldParams
from .maxwell_numeric import LocalMaxwellCurve, build_local_maxwell_curve
from .run_scalar_nx_svd import _duration
from .scan_local_dipole_c3 import ALPHA_MARGIN, _curve_point, _fit_from_start
from .scan_maxwell_declination import REFERENCE_MOMENT, build_declination_groups
from .validate_maxwell_c2 import SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG, build_target_group, solar_disk_samples
from .visualize_scalar_trajectory import _candidate_path


DECLINATIONS_DEG = tuple(float(value) for value in np.linspace(-23.44, -11.72, 13))
STRICT_CONSENSUS_FRACTION = 1e-6
CLUSTER_FRACTION = 1e-4
ALPHA_CONSENSUS_RAD = 1e-5
COMPETITIVE_RELATIVE_COST = 0.01
RANDOM_RESTARTS = 3


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_candidate(result_path: Path, dipole: float, level: str) -> tuple[tuple[int, int, float], ...]:
    payload = _read_json(result_path)
    match = next(
        (
            item for item in payload["analyses"]
            if float(item["dipole_epsilon"]) == dipole and item["basis_level"] == level
        ),
        None,
    )
    if match is None:
        raise ValueError(f"Brak kandydata epsilon={dipole}, level={level} w {result_path}")
    return tuple(
        (int(term[0]), int(term[1]), float(coefficient))
        for term, coefficient in zip(match["basis_terms"], match["coefficients"], strict=True)
    )


def _load_endpoint_alphas(
    checkpoint_dir: Path,
    dipole: float,
    level: str,
    declination: float,
) -> np.ndarray:
    path = _candidate_path(checkpoint_dir, dipole, level, declination, "centre")
    if not path.exists():
        raise FileNotFoundError(f"Brak checkpointu końcowego: {path}")
    return np.asarray(_read_json(path)["alphas_rad"], dtype=float)


def _reflection_signature(curves: tuple[LocalMaxwellCurve, ...], alphas: np.ndarray) -> tuple[int, ...]:
    counts = []
    for curve, alpha in zip(curves, alphas, strict=True):
        optical = curve.params.n0 * curve.params.radius_km * float(alpha)
        counts.append(sum(optical > segment.optical_end + 1e-8 for segment in curve.segments[:-1]))
    return tuple(counts)


def _signature_payload(signature: tuple[int, ...]) -> dict[str, object]:
    text = ",".join(str(value) for value in signature)
    return {
        "reflection_counts": list(signature),
        "reflected_observer_count": int(sum(value > 0 for value in signature)),
        "hash": hashlib.sha256(text.encode("ascii")).hexdigest()[:12],
    }


def _cluster_sources(sources: list[np.ndarray], threshold_km: float) -> list[int]:
    centres: list[np.ndarray] = []
    labels: list[int] = []
    members: list[list[np.ndarray]] = []
    for source in sources:
        distances = [float(np.linalg.norm(source - centre)) for centre in centres]
        if distances and min(distances) <= threshold_km:
            label = int(np.argmin(distances))
            members[label].append(source)
            centres[label] = np.mean(members[label], axis=0)
        else:
            label = len(centres)
            centres.append(source.copy())
            members.append([source])
        labels.append(label)
    return labels


def _boundary_task(
    declination: float,
    observers: tuple[tuple[float, float], ...],
    params: LensFieldParams,
    left_alphas: np.ndarray,
    right_alphas: np.ndarray,
) -> dict[str, object]:
    right_ascension = gmst_deg(REFERENCE_MOMENT)
    target = solar_disk_samples(
        RaDec(ra_deg=right_ascension, dec_deg=declination),
        DEFAULT_SOLAR_RADIUS_DEG,
    )["centre"]
    group = build_target_group(
        f"scalar_boundary:{declination:+.2f}:centre",
        target,
        REFERENCE_MOMENT,
        observers,
    )
    curves = tuple(
        build_local_maxwell_curve(origin, direction, params)
        for origin, direction in zip(group.origins, group.directions, strict=True)
    )
    grid = np.linspace(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, 129)
    sampled = tuple(np.array([_curve_point(curve, alpha) for alpha in grid]) for curve in curves)
    fraction = (declination - DECLINATIONS_DEG[0]) / (DECLINATIONS_DEG[-1] - DECLINATIONS_DEG[0])
    midpoint = np.clip((1.0 - fraction) * left_alphas + fraction * right_alphas, ALPHA_MARGIN, math.pi - ALPHA_MARGIN)
    seed_value = int(round((declination + 90.0) * 1000.0))
    rng = np.random.default_rng(seed_value)
    starts: list[tuple[str, np.ndarray]] = [
        ("left_endpoint", left_alphas),
        ("right_endpoint", right_alphas),
        ("linear_midpoint", midpoint),
        ("left_perturbed", left_alphas + rng.normal(0.0, 0.03, len(left_alphas))),
        ("right_perturbed", right_alphas + rng.normal(0.0, 0.03, len(right_alphas))),
    ]
    starts.extend(
        (f"random_{index}", rng.uniform(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, len(left_alphas)))
        for index in range(RANDOM_RESTARTS)
    )
    runs = []
    for label, start in starts:
        result = _fit_from_start(
            curves,
            grid,
            sampled,
            np.clip(start, ALPHA_MARGIN, math.pi - ALPHA_MARGIN),
            SELECTED_RADIUS_KM,
        )
        alphas = np.asarray(result["alphas_rad"], dtype=float)
        signature = _reflection_signature(curves, alphas)
        runs.append({
            "start": label,
            "source_km": np.asarray(result["source_km"], dtype=float),
            "alphas_rad": alphas,
            "rms_km": float(result["rms_km"]),
            "iterations": int(result["iterations"]),
            "converged": bool(result["converged"]),
            "signature": signature,
        })
    best = min(runs, key=lambda item: item["rms_km"])
    best_cost = best["rms_km"] ** 2
    tolerance = max(COMPETITIVE_RELATIVE_COST * best_cost, 1e-12 * SELECTED_RADIUS_KM**2)
    competitive = [item for item in runs if item["rms_km"] ** 2 <= best_cost + tolerance]
    strict_threshold = STRICT_CONSENSUS_FRACTION * SELECTED_RADIUS_KM
    cluster_threshold = CLUSTER_FRACTION * SELECTED_RADIUS_KM
    labels = _cluster_sources([item["source_km"] for item in competitive], cluster_threshold)
    competitive_labels = {id(item): label for item, label in zip(competitive, labels, strict=True)}
    maximum_spread = max(
        (
            float(np.linalg.norm(first["source_km"] - second["source_km"]))
            for index, first in enumerate(competitive)
            for second in competitive[index + 1 :]
        ),
        default=0.0,
    )
    maximum_alpha_rms = max(
        (
            float(np.sqrt(np.mean((first["alphas_rad"] - second["alphas_rad"]) ** 2)))
            for index, first in enumerate(competitive)
            for second in competitive[index + 1 :]
        ),
        default=0.0,
    )
    maximum_alpha_abs = max(
        (
            float(np.max(np.abs(first["alphas_rad"] - second["alphas_rad"])))
            for index, first in enumerate(competitive)
            for second in competitive[index + 1 :]
        ),
        default=0.0,
    )
    signature_hashes = {_signature_payload(item["signature"])["hash"] for item in competitive}
    by_start = {item["start"]: item for item in runs}
    left = by_start["left_endpoint"]
    right = by_start["right_endpoint"]
    two_sided_distance = float(np.linalg.norm(left["source_km"] - right["source_km"]))
    alpha_rms = float(np.sqrt(np.mean((left["alphas_rad"] - right["alphas_rad"]) ** 2)))
    alpha_max_abs = float(np.max(np.abs(left["alphas_rad"] - right["alphas_rad"])))
    return {
        "declination_deg": declination,
        "observer_count": len(observers),
        "best_start": best["start"],
        "best_source_km": best["source_km"].tolist(),
        "best_rms_km": best["rms_km"],
        "best_alphas_rad": best["alphas_rad"].tolist(),
        "best_signature": _signature_payload(best["signature"]),
        "competitive_run_count": len(competitive),
        "competitive_cluster_count": len(set(labels)),
        "competitive_signature_count": len(signature_hashes),
        "maximum_competitive_source_spread_km": maximum_spread,
        "maximum_competitive_alpha_rms_rad": maximum_alpha_rms,
        "maximum_competitive_alpha_abs_rad": maximum_alpha_abs,
        "competitive_alpha_consensus": maximum_alpha_abs <= ALPHA_CONSENSUS_RAD,
        "strict_restart_consensus": bool(
            maximum_spread <= strict_threshold
            and len(signature_hashes) == 1
            and maximum_alpha_abs <= ALPHA_CONSENSUS_RAD
        ),
        "two_sided_source_distance_km": two_sided_distance,
        "two_sided_alpha_rms_rad": alpha_rms,
        "two_sided_alpha_max_abs_rad": alpha_max_abs,
        "two_sided_signature_agreement": left["signature"] == right["signature"],
        "possible_branch_boundary": bool(
            two_sided_distance > cluster_threshold
            or alpha_max_abs > ALPHA_CONSENSUS_RAD
            or left["signature"] != right["signature"]
            or len(set(labels)) > 1
            or len(signature_hashes) > 1
        ),
        "runs": [
            {
                "start": item["start"],
                "source_km": item["source_km"].tolist(),
                "alphas_rad": item["alphas_rad"].tolist(),
                "rms_km": item["rms_km"],
                "iterations": item["iterations"],
                "converged": item["converged"],
                "signature": _signature_payload(item["signature"]),
                "competitive": id(item) in competitive_labels,
                "cluster": competitive_labels.get(id(item)),
            }
            for item in runs
        ],
    }


def _summary(records: list[dict[str, object]]) -> dict[str, object]:
    points = np.asarray([record["best_source_km"] for record in records], dtype=float)
    deltas = np.asarray([record["declination_deg"] for record in records], dtype=float)
    step_speeds = np.linalg.norm(np.diff(points, axis=0), axis=1) / np.diff(deltas)
    turns = []
    segments = np.diff(points, axis=0)
    for first, second in zip(segments[:-1], segments[1:], strict=True):
        cosine = float(np.clip(np.dot(first, second) / np.linalg.norm(first) / np.linalg.norm(second), -1.0, 1.0))
        turns.append(math.degrees(math.acos(cosine)))
    return {
        "possible_boundary_declinations_deg": [
            record["declination_deg"] for record in records if record["possible_branch_boundary"]
        ],
        "strict_consensus_count": sum(bool(record["strict_restart_consensus"]) for record in records),
        "record_count": len(records),
        "step_speed_km_per_degree": step_speeds.tolist(),
        "turn_angles_deg": turns,
        "maximum_step_speed_km_per_degree": float(np.max(step_speeds)),
        "maximum_turn_angle_deg": float(np.max(turns)) if turns else 0.0,
        "maximum_two_sided_source_distance_km": max(
            float(record["two_sided_source_distance_km"]) for record in records
        ),
    }


def run(
    output: Path,
    checkpoint_dir: Path,
    svd_result: Path,
    workers: int,
    dipole: float = 0.4,
    level: str = "degree_3",
) -> dict[str, object]:
    terms = _load_candidate(svd_result, dipole, level)
    left_alphas = _load_endpoint_alphas(checkpoint_dir, dipole, level, DECLINATIONS_DEG[0])
    right_alphas = _load_endpoint_alphas(checkpoint_dir, dipole, level, DECLINATIONS_DEG[-1])
    design = dict(build_declination_groups(DEFAULT_SOLAR_RADIUS_DEG))
    observers = tuple(design[-23.44]["observer_coordinates_deg"])
    params = LensFieldParams(
        "maxwell",
        SELECTED_RADIUS_KM,
        centre_km=(0.0, 0.0, SELECTED_CENTRE_Z_KM),
        dipole_epsilon=dipole,
        scalar_basis_terms=terms,
    )
    scan_dir = checkpoint_dir / "branch-boundary"
    records_by_delta: dict[float, dict[str, object]] = {}
    pending = []
    for delta in DECLINATIONS_DEG:
        path = scan_dir / f"delta_{delta:+.2f}.json"
        if path.exists():
            records_by_delta[delta] = _read_json(path)
        else:
            pending.append(delta)
    print(
        f"[granica gałęzi] {len(records_by_delta)}/{len(DECLINATIONS_DEG)} z checkpointów, "
        f"pozostało {len(pending)}, workers={workers}",
        flush=True,
    )
    started = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_boundary_task, delta, observers, params, left_alphas, right_alphas): delta
            for delta in pending
        }
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            delta = futures[future]
            record = future.result()
            records_by_delta[delta] = record
            _write_json(scan_dir / f"delta_{delta:+.2f}.json", record)
            elapsed = time.monotonic() - started
            eta = elapsed / index * (len(pending) - index) if index else 0.0
            print(
                f"[granica gałęzi] {len(records_by_delta)}/{len(DECLINATIONS_DEG)} | "
                f"czas {_duration(elapsed)} | ETA {_duration(eta)} | delta={delta:+.2f}",
                flush=True,
            )
    records = [records_by_delta[delta] for delta in DECLINATIONS_DEG]
    payload = {
        "schema_version": 1,
        "status": "completed",
        "candidate": {"dipole_epsilon": dipole, "basis_level": level, "scalar_basis_terms": terms},
        "design": {
            "declinations_deg": list(DECLINATIONS_DEG),
            "reference_moment_utc": REFERENCE_MOMENT.isoformat(),
            "observer_count": len(observers),
            "restart_labels": [
                "left_endpoint", "right_endpoint", "linear_midpoint",
                "left_perturbed", "right_perturbed", "random_0", "random_1", "random_2",
            ],
            "strict_consensus_fraction_of_radius": STRICT_CONSENSUS_FRACTION,
            "cluster_fraction_of_radius": CLUSTER_FRACTION,
            "alpha_consensus_rad": ALPHA_CONSENSUS_RAD,
            "p_jpj_note": (
                "The perturbed numerical field has no exact P/JPJ label. "
                "Per-observer mirror-reflection counts and fitted alpha vectors are reported instead."
            ),
        },
        "records": records,
        "summary": _summary(records),
        "scope": "two-sided, restart-controlled centre-only probe of the suspected branch boundary",
    }
    _write_json(output, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("solver/results/v2-scalar-branch-boundary.json"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("solver/results/v2-scalar-nx-svd-checkpoints"))
    parser.add_argument("--svd-result", type=Path, default=Path("solver/results/v2-scalar-nx-svd.json"))
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args()
    payload = run(args.output, args.checkpoint_dir, args.svd_result, max(1, args.workers))
    print(f"Gotowe: {args.output}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
