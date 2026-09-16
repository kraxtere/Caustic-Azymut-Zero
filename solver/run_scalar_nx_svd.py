"""Run the resumable multi-base scalar n(rho,z) reachability experiment."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import math
import os
import time
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import numpy as np

from .field_lens import LensFieldParams
from .maxwell_mirror import maxwell_direction_to_auxiliary_target
from .maxwell_numeric import build_local_maxwell_curve
from .scan_local_dipole_c3 import ALPHA_MARGIN, _curve_point, _fit_from_start
from .scan_local_dipole_scale import _disk_shape
from .scan_luneburg import build_scan_groups
from .scan_maxwell_declination import build_declination_groups
from .validate_maxwell import DEFAULT_RESTARTS, DEFAULT_SEEDS, evaluate_maxwell
from .validate_maxwell_c2 import SAMPLE_IDS, SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM
from .validate_v1 import DEFAULT_SOLAR_RADIUS_DEG, TargetGroup


BASE_DIPOLES = (0.0, 0.2, 0.4)
COLUMN_STEP = 0.01
SVD_RELATIVE_CUTOFF = 1e-8
TRUST_RADIUS = 0.25
AXIS_RATIO_LIMIT = 1.10
FIT_DECLINATIONS = (-23.44, 23.44)
HOLDOUT_DECLINATIONS = (-11.72, 11.72)
ALL_TERMS = tuple((a, total - a) for total in range(4) for a in range(total + 1))
BASIS_LEVELS = {
    "degree_1": ALL_TERMS[:3],
    "degree_2": ALL_TERMS[:6],
    "degree_3": ALL_TERMS[:10],
}
ANCHOR_EPSILONS = tuple(round(value, 2) for value in np.arange(0.0, 0.401, 0.05))


def _slug(value: str) -> str:
    return value.replace(":", "__").replace("+", "p").replace("-", "m").replace(".", "_")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _subset_group(group: TargetGroup, count: int | None) -> TargetGroup:
    if count is None or count >= len(group.origins):
        return group
    return replace(
        group,
        origins=group.origins[:count],
        directions=group.directions[:count],
        observer_coordinates_deg=group.observer_coordinates_deg[:count],
    )


def build_groups(observer_limit: int | None = None) -> dict[str, TargetGroup]:
    _, poles = build_scan_groups(2.0, DEFAULT_SOLAR_RADIUS_DEG)
    output = {f"pole:{group.target_id}": _subset_group(group, observer_limit) for group in poles}
    design = dict(build_declination_groups(DEFAULT_SOLAR_RADIUS_DEG))
    for delta in FIT_DECLINATIONS + HOLDOUT_DECLINATIONS:
        for sample in SAMPLE_IDS:
            output[f"disk:{delta:+.2f}:{sample}"] = _subset_group(design[delta]["groups"][sample], observer_limit)
    return output


def _analytic_alphas(group: TargetGroup, centre: np.ndarray) -> np.ndarray:
    seed = evaluate_maxwell(group, SELECTED_RADIUS_KM, centre, DEFAULT_SEEDS, DEFAULT_RESTARTS)
    target = np.asarray(seed["common_point_s3_km"], dtype=float)
    return np.asarray([
        maxwell_direction_to_auxiliary_target(
            origin, target, SELECTED_RADIUS_KM,
            reflected_branch=bool(reflected), centre_xyz=centre,
        )[1]
        for origin, reflected in zip(group.origins, seed["selected_reflection_parities"], strict=True)
    ])


def _fit(group: TargetGroup, params: LensFieldParams, initial_alphas: np.ndarray) -> dict[str, object]:
    curves = tuple(
        build_local_maxwell_curve(origin, direction, params)
        for origin, direction in zip(group.origins, group.directions, strict=True)
    )
    grid = np.linspace(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, 129)
    sampled = tuple(np.array([_curve_point(curve, alpha) for alpha in grid]) for curve in curves)
    run = _fit_from_start(curves, grid, sampled, initial_alphas, SELECTED_RADIUS_KM)
    return {
        "source_km": np.asarray(run["source_km"]).tolist(),
        "alphas_rad": np.asarray(run["alphas_rad"]).tolist(),
        "rms_km": float(run["rms_km"]),
        "iterations": int(run["iterations"]),
        "converged": bool(run["converged"]),
    }


def _anchor_task(
    group_id: str,
    observer_limit: int | None,
    requested_bases: tuple[float, ...],
) -> dict[str, object]:
    group = build_groups(observer_limit)[group_id]
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    alphas = _analytic_alphas(group, centre)
    anchors = {}
    for epsilon in (value for value in ANCHOR_EPSILONS if value <= max(requested_bases)):
        params = LensFieldParams("maxwell", SELECTED_RADIUS_KM, centre_km=tuple(centre), dipole_epsilon=epsilon)
        result = _fit(group, params, alphas)
        alphas = np.asarray(result["alphas_rad"])
        if epsilon in requested_bases:
            anchors[str(epsilon)] = result
    return {"group_id": group_id, "anchors": anchors}


def _evaluation_task(
    group_id: str,
    observer_limit: int | None,
    dipole: float,
    terms: tuple[tuple[int, int, float], ...],
    initial_alphas: list[float],
) -> dict[str, object]:
    group = build_groups(observer_limit)[group_id]
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    params = LensFieldParams(
        "maxwell", SELECTED_RADIUS_KM, centre_km=tuple(centre),
        dipole_epsilon=dipole, scalar_basis_terms=terms,
    )
    return _fit(group, params, np.asarray(initial_alphas, dtype=float))


def _candidate_task(
    group_id: str,
    observer_limit: int | None,
    dipole: float,
    terms: tuple[tuple[int, int, float], ...],
    initial_alphas: list[float],
) -> dict[str, object]:
    """Continue the nonlinear validation from zero to the proposed step."""

    group = build_groups(observer_limit)[group_id]
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    alphas = np.asarray(initial_alphas, dtype=float)
    result = None
    for fraction in (0.25, 0.50, 0.75, 1.0):
        scaled = tuple((a, b, coefficient * fraction) for a, b, coefficient in terms)
        params = LensFieldParams(
            "maxwell", SELECTED_RADIUS_KM, centre_km=tuple(centre),
            dipole_epsilon=dipole, scalar_basis_terms=scaled,
        )
        result = _fit(group, params, alphas)
        alphas = np.asarray(result["alphas_rad"])
    assert result is not None
    return result


def _disk(results: dict[str, dict[str, object]], delta: float):
    return _disk_shape({sample: {"source_km": results[f"disk:{delta:+.2f}:{sample}"]["source_km"]} for sample in SAMPLE_IDS})


def _observables(results: dict[str, dict[str, object]], fit: bool) -> np.ndarray:
    deltas = FIT_DECLINATIONS if fit else HOLDOUT_DECLINATIONS
    minus, plus = (_disk(results, delta) for delta in deltas)
    values = [
        math.log(minus["mean_diameter_km"] / plus["mean_diameter_km"]),
        math.log(minus["axis_ratio"]),
        math.log(plus["axis_ratio"]),
    ]
    if fit:
        values = [
            math.log(results["pole:north_celestial_pole"]["rms_km"]),
            math.log(results["pole:south_celestial_pole"]["rms_km"]),
            *values,
        ]
    return np.asarray(values, dtype=float)


def _residual(observables: np.ndarray, fit: bool, c3_target: tuple[float, float]) -> np.ndarray:
    if fit:
        return np.asarray([
            max(0.0, observables[0] - math.log(c3_target[0])),
            max(0.0, observables[1] - math.log(c3_target[1])),
            observables[2],
            max(0.0, observables[3] - math.log(AXIS_RATIO_LIMIT)),
            max(0.0, observables[4] - math.log(AXIS_RATIO_LIMIT)),
        ])
    return np.asarray([
        observables[0],
        max(0.0, observables[1] - math.log(AXIS_RATIO_LIMIT)),
        max(0.0, observables[2] - math.log(AXIS_RATIO_LIMIT)),
    ])


def _duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _checkpointed_tasks(
    specs,
    worker,
    checkpoint_dir: Path,
    workers: int,
    stage_name: str,
):
    results = {}
    pending = []
    for key, arguments in specs:
        path = checkpoint_dir / f"{_slug(key)}.json"
        if path.exists():
            results[key] = _read_json(path)
        else:
            pending.append((key, arguments))
    total = len(specs)
    completed = len(results)
    print(
        f"[{stage_name}] start: {completed}/{total} z checkpointów, "
        f"pozostało {len(pending)}, workers={workers}",
        flush=True,
    )
    if not pending:
        print(f"[{stage_name}] 100.0% ({total}/{total}) — gotowe z checkpointów", flush=True)
        return results

    started = time.monotonic()
    newly_completed = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, *arguments): key for key, arguments in pending}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            result = future.result()
            path = checkpoint_dir / f"{_slug(key)}.json"
            _write_json(path, result)
            results[key] = result
            completed += 1
            newly_completed += 1
            elapsed = time.monotonic() - started
            rate = newly_completed / elapsed if elapsed > 0.0 else 0.0
            eta = (total - completed) / rate if rate > 0.0 else 0.0
            print(
                f"[{stage_name}] {100.0 * completed / total:6.2f}% "
                f"({completed}/{total}) | czas {_duration(elapsed)} | "
                f"ETA {_duration(eta)} | {key}",
                flush=True,
            )
    return results


def run(output: Path, checkpoint_dir: Path, workers: int, smoke: bool = False) -> dict[str, object]:
    observer_limit = 4 if smoke else None
    base_dipoles = (0.0,) if smoke else BASE_DIPOLES
    terms = ALL_TERMS[:1] if smoke else ALL_TERMS
    levels = {"smoke_degree_0": terms} if smoke else BASIS_LEVELS
    group_ids = tuple(build_groups(observer_limit))

    anchor_specs = [(group_id, (group_id, observer_limit, base_dipoles)) for group_id in group_ids]
    anchor_payloads = _checkpointed_tasks(
        anchor_specs, _anchor_task, checkpoint_dir / "anchors", workers, "1/3 kotwice"
    )
    anchors = {
        dipole: {group_id: anchor_payloads[group_id]["anchors"][str(dipole)] for group_id in group_ids}
        for dipole in base_dipoles
    }
    base_observables = {dipole: {"fit": _observables(anchors[dipole], True), "heldout": _observables(anchors[dipole], False)} for dipole in base_dipoles}
    c3_target = (
        min(math.exp(base_observables[d]["fit"][0]) for d in base_dipoles),
        min(math.exp(base_observables[d]["fit"][1]) for d in base_dipoles),
    )

    column_specs = []
    for dipole, (a, b), sign, group_id in itertools.product(base_dipoles, terms, (-1, 1), group_ids):
        key = f"base={dipole}:term={a}_{b}:sign={sign}:group={group_id}"
        amplitudes = ((a, b, sign * COLUMN_STEP),)
        column_specs.append((key, (group_id, observer_limit, dipole, amplitudes, anchors[dipole][group_id]["alphas_rad"])))
    column_results = _checkpointed_tasks(
        column_specs, _evaluation_task, checkpoint_dir / "columns", workers, "2/3 Jacobian"
    )

    analyses = []
    candidate_specs = []
    candidate_metadata = {}
    for dipole in base_dipoles:
        for level_name, level_terms in levels.items():
            fit_columns = []
            heldout_columns = []
            for a, b in level_terms:
                signed = {}
                for sign in (-1, 1):
                    prefix = f"base={dipole}:term={a}_{b}:sign={sign}:group="
                    signed[sign] = {group_id: column_results[prefix + group_id] for group_id in group_ids}
                fit_columns.append((_observables(signed[1], True) - _observables(signed[-1], True)) / (2.0 * COLUMN_STEP))
                heldout_columns.append((_observables(signed[1], False) - _observables(signed[-1], False)) / (2.0 * COLUMN_STEP))
            fit_jacobian = np.column_stack(fit_columns)
            heldout_jacobian = np.column_stack(heldout_columns)
            singular_values = np.linalg.svd(fit_jacobian, compute_uv=False)
            cutoff = SVD_RELATIVE_CUTOFF * singular_values[0] if singular_values.size else 0.0
            rank = int(np.sum(singular_values > cutoff))
            base_fit_residual = _residual(base_observables[dipole]["fit"], True, c3_target)
            base_heldout_residual = _residual(base_observables[dipole]["heldout"], False, c3_target)
            coefficients = np.linalg.lstsq(fit_jacobian, -base_fit_residual, rcond=SVD_RELATIVE_CUTOFF)[0]
            unconstrained_norm = float(np.linalg.norm(coefficients))
            if unconstrained_norm > TRUST_RADIUS:
                coefficients *= TRUST_RADIUS / unconstrained_norm
            predicted_fit = base_fit_residual + fit_jacobian @ coefficients
            predicted_heldout = base_heldout_residual + heldout_jacobian @ coefficients
            candidate_id = f"base={dipole}:level={level_name}"
            scalar_terms = tuple((a, b, float(value)) for (a, b), value in zip(level_terms, coefficients, strict=True))
            for group_id in group_ids:
                key = f"{candidate_id}:group={group_id}"
                candidate_specs.append((key, (group_id, observer_limit, dipole, scalar_terms, anchors[dipole][group_id]["alphas_rad"])))
            candidate_metadata[candidate_id] = {
                "dipole_epsilon": dipole,
                "basis_level": level_name,
                "basis_terms": [list(term) for term in level_terms],
                "coefficients": coefficients.tolist(),
                "unconstrained_coefficient_norm": unconstrained_norm,
                "coefficient_norm": float(np.linalg.norm(coefficients)),
                "singular_values": singular_values.tolist(),
                "effective_rank": rank,
                "fit_jacobian": fit_jacobian.tolist(),
                "heldout_jacobian": heldout_jacobian.tolist(),
                "base_fit_residual": base_fit_residual.tolist(),
                "base_heldout_residual": base_heldout_residual.tolist(),
                "predicted_fit_residual": predicted_fit.tolist(),
                "predicted_heldout_residual": predicted_heldout.tolist(),
            }

    candidate_results = _checkpointed_tasks(
        candidate_specs, _candidate_task, checkpoint_dir / "candidates", workers, "3/3 walidacja nieliniowa"
    )
    for candidate_id, metadata in candidate_metadata.items():
        results = {group_id: candidate_results[f"{candidate_id}:group={group_id}"] for group_id in group_ids}
        nonlinear_fit = _residual(_observables(results, True), True, c3_target)
        nonlinear_heldout = _residual(_observables(results, False), False, c3_target)
        metadata["nonlinear_fit_residual"] = nonlinear_fit.tolist()
        metadata["nonlinear_heldout_residual"] = nonlinear_heldout.tolist()
        metadata["base_fit_norm"] = float(np.linalg.norm(metadata["base_fit_residual"]))
        metadata["base_heldout_norm"] = float(np.linalg.norm(metadata["base_heldout_residual"]))
        metadata["predicted_fit_norm"] = float(np.linalg.norm(metadata["predicted_fit_residual"]))
        metadata["predicted_heldout_norm"] = float(np.linalg.norm(metadata["predicted_heldout_residual"]))
        metadata["nonlinear_fit_norm"] = float(np.linalg.norm(nonlinear_fit))
        metadata["nonlinear_heldout_norm"] = float(np.linalg.norm(nonlinear_heldout))
        metadata["improves_fit_and_heldout_nonlinearly"] = bool(
            metadata["nonlinear_fit_norm"] < metadata["base_fit_norm"]
            and metadata["nonlinear_heldout_norm"] < metadata["base_heldout_norm"]
        )
        analyses.append(metadata)

    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_SCALAR_NX_SVD_CONTRACT.md",
        "smoke_mode": smoke,
        "workers": workers,
        "base_dipoles": list(base_dipoles),
        "basis_levels": {name: [list(term) for term in values] for name, values in levels.items()},
        "column_step": COLUMN_STEP,
        "trust_radius": TRUST_RADIUS,
        "c3_target_rms_km": list(c3_target),
        "analyses": analyses,
        "scope": "multi-base scalar reachability experiment; interpretation requires cross-base and cross-resolution consistency",
    }
    _write_json(output, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    payload = run(args.output, args.checkpoint_dir, max(1, args.workers), args.smoke)
    print(f"Completed {len(payload['analyses'])} base/level analyses -> {args.output}")


if __name__ == "__main__":
    main()
