"""Map ICP basin cross-sections for the unstable -11.72 degree disk."""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

from .field_lens import LensFieldParams
from .maxwell_mirror import maxwell_direction_to_auxiliary_target
from .maxwell_numeric import build_local_maxwell_curve
from .scan_local_dipole_c3 import (
    ALPHA_MARGIN,
    CONSENSUS_FRACTION,
    START_SEEDS,
    _curve_point,
    _fit_from_start,
)
from .scan_local_dipole_scale import _disk_shape
from .scan_maxwell_declination import build_declination_groups
from .validate_maxwell import DEFAULT_RESTARTS, DEFAULT_SEEDS, evaluate_maxwell
from .validate_maxwell_c2 import SAMPLE_IDS, SELECTED_CENTRE_Z_KM, SELECTED_RADIUS_KM


DECLINATION = -11.72
DIPOLE_EPSILON = 0.20
CROSS_SECTION_POINTS = 65
COMBINATION_LIMIT = 1024


def _starts(group, analytic_seed, centre):
    target = np.asarray(analytic_seed["common_point_s3_km"], dtype=float)
    parities = analytic_seed["selected_reflection_parities"]
    warm = np.array([
        maxwell_direction_to_auxiliary_target(
            origin, target, SELECTED_RADIUS_KM,
            reflected_branch=bool(reflected), centre_xyz=centre,
        )[1]
        for origin, reflected in zip(group.origins, parities, strict=True)
    ])
    starts = [warm]
    for index, seed in enumerate(START_SEEDS):
        rng = np.random.default_rng(seed)
        if index < 4:
            starts.append(warm + rng.normal(0.0, (0.02, 0.05, 0.10, 0.20)[index], len(warm)))
        else:
            starts.append(rng.uniform(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, len(warm)))
    return starts


def _cluster_runs(runs):
    threshold = CONSENSUS_FRACTION * SELECTED_RADIUS_KM
    clusters = []
    labels = []
    for run in runs:
        source = np.asarray(run["source_km"])
        label = next((i for i, cluster in enumerate(clusters) if np.linalg.norm(source - cluster["source_km"]) <= threshold), None)
        if label is None:
            label = len(clusters)
            clusters.append({"source_km": source, "runs": []})
        clusters[label]["runs"].append(run)
        labels.append(label)
    output = []
    for cluster in clusters:
        best = min(cluster["runs"], key=lambda run: run["rms_km"])
        output.append({"source_km": np.asarray(best["source_km"]), "rms_km": float(best["rms_km"]), "run_count": len(cluster["runs"])})
    return output, labels


def run(output: Path) -> dict[str, object]:
    design = dict(build_declination_groups())[DECLINATION]
    centre = np.array([0.0, 0.0, SELECTED_CENTRE_Z_KM])
    params = LensFieldParams("maxwell", SELECTED_RADIUS_KM, centre_km=tuple(centre), dipole_epsilon=DIPOLE_EPSILON)
    targets = {}
    representatives = {}
    for sample in SAMPLE_IDS:
        group = design["groups"][sample]
        analytic = evaluate_maxwell(group, SELECTED_RADIUS_KM, centre, DEFAULT_SEEDS, DEFAULT_RESTARTS)
        curves = tuple(build_local_maxwell_curve(origin, direction, params) for origin, direction in zip(group.origins, group.directions, strict=True))
        grid = np.linspace(ALPHA_MARGIN, math.pi - ALPHA_MARGIN, 129)
        sampled = tuple(np.array([_curve_point(curve, alpha) for alpha in grid]) for curve in curves)
        starts = _starts(group, analytic, centre)
        initial_runs = [_fit_from_start(curves, grid, sampled, start, SELECTED_RADIUS_KM) for start in starts]
        initial_clusters, labels = _cluster_runs(initial_runs)
        clusters = initial_clusters
        section = None
        alternative = next((i for i, label in enumerate(labels) if label != labels[0]), None)
        if alternative is not None:
            section_runs = [
                _fit_from_start(curves, grid, sampled, (1.0-t)*starts[0] + t*starts[alternative], SELECTED_RADIUS_KM)
                for t in np.linspace(0.0, 1.0, CROSS_SECTION_POINTS)
            ]
            section_clusters, section_labels = _cluster_runs(section_runs)
            transitions = sum(a != b for a, b in zip(section_labels, section_labels[1:]))
            section_sources = [cluster["source_km"] for cluster in section_clusters]
            source_span = max(
                (float(np.linalg.norm(first - second))
                 for i, first in enumerate(section_sources)
                 for second in section_sources[i + 1:]),
                default=0.0,
            )
            rms_values = [cluster["rms_km"] for cluster in section_clusters]
            section = {
                "endpoint_start_index": alternative,
                "cluster_count": len(section_clusters),
                "transition_count": transitions,
                "labels_monotonic": all(a <= b for a, b in zip(section_labels, section_labels[1:])),
                "maximum_source_span_km": source_span,
                "rms_range_km": max(rms_values) - min(rms_values),
                "labels": section_labels,
                "clusters": [{"source_km": c["source_km"].tolist(), "rms_km": c["rms_km"], "run_count": c["run_count"]} for c in section_clusters],
            }
        # Shape enumeration stays on the clusters actually reached by the
        # preregistered eight restarts.  The dense section is diagnostic and
        # must not multiply the combinatorial state space with threshold cuts
        # through a potentially continuous valley.
        representatives[sample] = initial_clusters
        targets[sample] = {
            "initial_cluster_count": len(initial_clusters),
            "initial_labels": labels,
            "initial_clusters": [{"source_km": c["source_km"].tolist(), "rms_km": c["rms_km"], "run_count": c["run_count"]} for c in initial_clusters],
            "cross_section": section,
        }
        print(f"{sample}: initial_clusters={len(initial_clusters)} section={'yes' if section else 'no'}", flush=True)

    counts = [len(representatives[sample]) for sample in SAMPLE_IDS]
    total = math.prod(counts)
    shapes = []
    if total <= COMBINATION_LIMIT:
        for choice in itertools.product(*(range(count) for count in counts)):
            selected = {sample: {"source_km": representatives[sample][index]["source_km"].tolist()} for sample, index in zip(SAMPLE_IDS, choice, strict=True)}
            shapes.append({"choice": list(choice), **_disk_shape(selected)})
    payload = {
        "schema_version": 1,
        "status": "completed",
        "pre_registered_contract": "docs/V2_LOCAL_BASIN_DIAGNOSTIC.md",
        "design": {"declination_deg": DECLINATION, "dipole_epsilon": DIPOLE_EPSILON, "cross_section_points": CROSS_SECTION_POINTS},
        "targets": targets,
        "combination_count": total,
        "shape_combinations_evaluated": len(shapes),
        "shape_summary": ({
            "minimum_axis_ratio": min(shape["axis_ratio"] for shape in shapes),
            "maximum_axis_ratio": max(shape["axis_ratio"] for shape in shapes),
            "minimum_mean_diameter_km": min(shape["mean_diameter_km"] for shape in shapes),
            "maximum_mean_diameter_km": max(shape["mean_diameter_km"] for shape in shapes),
            "any_axis_ratio_at_or_below_1_10": any(shape["axis_ratio"] <= 1.10 for shape in shapes),
        } if shapes else None),
        "shapes": shapes,
        "rule_frozen_before_run": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.output)
    print(json.dumps(payload["shape_summary"], indent=2))


if __name__ == "__main__":
    main()
