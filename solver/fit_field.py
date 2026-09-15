"""Fit one axisymmetric Gaussian ring to multi-observer solar directions.

The optimizer works exclusively in a normalized [0, 1]^5 cube.  Conversion
to physical units is performed by :class:`ParameterSpace`, which also keeps
the ring genuinely toroidal by enforcing ``rho0 >= 2 s``.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.optimize import OptimizeResult, differential_evolution, minimize

from .ephemeris import Ephemeris, MeeusLowPrecision
from .field import FieldParams
from .geometry_flat import R_MAP, altaz_of_radec, observer_xy, sky_direction_3d
from .raytrace import (
    IntegrationOptions,
    RayResult,
    trace_ray,
    triangulate_detailed,
    triangulate_half_lines_detailed,
)


OBSERVERS = [
    (30.0, 0.0),
    (45.0, 20.0),
    (50.0, -30.0),
    (-10.0, 10.0),
    (20.0, -60.0),
]
MOMENTS = [
    datetime(2026, month, day, hour, 0, tzinfo=timezone.utc)
    for month, day in [(3, 20), (6, 21), (12, 21)]
    for hour in [14, 17]
]


@dataclass(frozen=True)
class ObservationGroup:
    timestamp_utc: datetime
    origins: tuple[np.ndarray, ...]
    directions: tuple[np.ndarray, ...]


@dataclass(frozen=True)
class GroupScore:
    timestamp_utc: datetime
    observer_count: int
    rms_km: float
    common_point_km: np.ndarray
    minimum_forward_distance_km: float
    condition_number: float


@dataclass(frozen=True)
class CostBreakdown:
    cost_km: float
    group_scores: tuple[GroupScore, ...]
    invalid_rays: int
    intersection_mode: str


@dataclass(frozen=True)
class ParameterSpace:
    k_bounds: tuple[float, float] = (0.0, 0.001)
    h_bounds_km: tuple[float, float] = (2.0, 30.0)
    amplitude_bounds: tuple[float, float] = (-0.1, 0.1)
    width_bounds_km: tuple[float, float] = (100.0, 5000.0)
    minimum_ring_radius_km: float = 500.0
    maximum_ring_radius_km: float = math.pi * R_MAP
    minimum_radius_to_width: float = 2.0

    @staticmethod
    def _linear(value: float, bounds: tuple[float, float]) -> float:
        return bounds[0] + value * (bounds[1] - bounds[0])

    @staticmethod
    def _logarithmic(value: float, bounds: tuple[float, float]) -> float:
        return math.exp(
            math.log(bounds[0])
            + value * math.log(bounds[1] / bounds[0])
        )

    def decode(self, normalized: Sequence[float]) -> FieldParams:
        values = np.asarray(normalized, dtype=float)
        if values.shape != (5,) or np.any(values < 0) or np.any(values > 1):
            raise ValueError("normalized parameters must be five values in [0, 1]")

        width = self._logarithmic(float(values[4]), self.width_bounds_km)
        effective_minimum_radius = max(
            self.minimum_ring_radius_km,
            self.minimum_radius_to_width * width,
        )
        radius = self._linear(
            float(values[3]),
            (effective_minimum_radius, self.maximum_ring_radius_km),
        )
        return FieldParams(
            k=self._linear(float(values[0]), self.k_bounds),
            H=self._logarithmic(float(values[1]), self.h_bounds_km),
            A=self._linear(float(values[2]), self.amplitude_bounds),
            rho0=radius,
            s=width,
        )

    def encode(self, params: FieldParams) -> np.ndarray:
        def linear_inverse(value: float, bounds: tuple[float, float]) -> float:
            return (value - bounds[0]) / (bounds[1] - bounds[0])

        def logarithmic_inverse(
            value: float,
            bounds: tuple[float, float],
        ) -> float:
            return math.log(value / bounds[0]) / math.log(bounds[1] / bounds[0])

        width_position = logarithmic_inverse(params.s, self.width_bounds_km)
        effective_minimum_radius = max(
            self.minimum_ring_radius_km,
            self.minimum_radius_to_width * params.s,
        )
        radius_position = linear_inverse(
            params.rho0,
            (effective_minimum_radius, self.maximum_ring_radius_km),
        )
        encoded = np.array(
            [
                linear_inverse(params.k, self.k_bounds),
                logarithmic_inverse(params.H, self.h_bounds_km),
                linear_inverse(params.A, self.amplitude_bounds),
                radius_position,
                width_position,
            ]
        )
        return np.clip(encoded, 0.0, 1.0)


PARAMETER_SPACE = ParameterSpace()
INVALID_COST_KM = 1_000_000.0


def build_dataset(
    ephemeris: Ephemeris | None = None,
    minimum_altitude_deg: float = 2.0,
) -> list[ObservationGroup]:
    """Build groups of simultaneous synthetic Sun observations."""

    ephemeris = ephemeris or MeeusLowPrecision()
    dataset: list[ObservationGroup] = []
    for instant in MOMENTS:
        radec = ephemeris.sun_radec(instant)
        origins: list[np.ndarray] = []
        directions: list[np.ndarray] = []
        for latitude, longitude in OBSERVERS:
            altitude, azimuth = altaz_of_radec(
                radec,
                latitude,
                longitude,
                instant,
            )
            if altitude < minimum_altitude_deg:
                continue
            origins.append(observer_xy(latitude, longitude))
            directions.append(
                sky_direction_3d(
                    altitude,
                    azimuth,
                    latitude,
                    longitude,
                )
            )
        if len(origins) >= 3:
            dataset.append(
                ObservationGroup(
                    timestamp_utc=instant,
                    origins=tuple(origins),
                    directions=tuple(directions),
                )
            )
    return dataset


def evaluate_field(
    params: FieldParams,
    dataset: Sequence[ObservationGroup],
    integration: IntegrationOptions,
    intersection_mode: str = "rays",
) -> CostBreakdown:
    if intersection_mode not in {"lines", "rays"}:
        raise ValueError("intersection_mode must be 'lines' or 'rays'")
    group_scores: list[GroupScore] = []
    invalid_rays = 0

    for group in dataset:
        rays: list[RayResult] = [
            trace_ray(origin, direction, params, integration)
            for origin, direction in zip(
                group.origins,
                group.directions,
                strict=True,
            )
        ]
        invalid_in_group = sum(ray.status != "escaped" for ray in rays)
        invalid_rays += invalid_in_group
        if invalid_in_group:
            continue

        triangulation_function = (
            triangulate_half_lines_detailed
            if intersection_mode == "rays"
            else triangulate_detailed
        )
        triangulation = triangulation_function(
            [ray.point for ray in rays], [ray.direction for ray in rays]
        )
        if (
            triangulation.matrix_rank < 3
            or not math.isfinite(triangulation.rms_km)
            or triangulation.condition_number > 1e14
        ):
            invalid_rays += len(rays)
            continue

        group_scores.append(
            GroupScore(
                timestamp_utc=group.timestamp_utc,
                observer_count=len(rays),
                rms_km=triangulation.rms_km,
                common_point_km=triangulation.point,
                minimum_forward_distance_km=float(
                    np.min(triangulation.forward_distances_km)
                ),
                condition_number=triangulation.condition_number,
            )
        )

    if invalid_rays or len(group_scores) != len(dataset):
        return CostBreakdown(
            cost_km=INVALID_COST_KM + invalid_rays * 10_000.0,
            group_scores=tuple(group_scores),
            invalid_rays=invalid_rays,
            intersection_mode=intersection_mode,
        )

    return CostBreakdown(
        cost_km=float(np.mean([score.rms_km for score in group_scores])),
        group_scores=tuple(group_scores),
        invalid_rays=0,
        intersection_mode=intersection_mode,
    )


@dataclass(frozen=True)
class NormalizedObjective:
    dataset: tuple[ObservationGroup, ...]
    integration: IntegrationOptions
    intersection_mode: str = "rays"

    def __call__(self, normalized: Sequence[float]) -> float:
        try:
            params = PARAMETER_SPACE.decode(normalized)
            return evaluate_field(
                params,
                self.dataset,
                self.integration,
                self.intersection_mode,
            ).cost_km
        except (FloatingPointError, ValueError, np.linalg.LinAlgError):
            return INVALID_COST_KM


def total_cost(
    params_vec: Sequence[float],
    dataset: Sequence[ObservationGroup],
    s_max: float = 500_000.0,
    intersection_mode: str = "rays",
) -> float:
    """Compatibility entry point using physical parameter units."""

    params = FieldParams(*[float(value) for value in params_vec])
    return evaluate_field(
        params,
        dataset,
        IntegrationOptions(max_path_km=s_max),
        intersection_mode,
    ).cost_km


def optimize_de(
    objective: NormalizedObjective,
    *,
    seed: int,
    maxiter: int,
    popsize: int,
    workers: int,
    polish: bool,
    report_every: int,
) -> OptimizeResult:
    generation = 0

    def report(best: np.ndarray, convergence: float) -> bool:
        nonlocal generation
        generation += 1
        if report_every and generation % report_every == 0:
            params = PARAMETER_SPACE.decode(best)
            print(
                f"generacja={generation:4d}  "
                f"RMS={objective(best):10.2f} km  "
                f"zbieznosc={convergence:.3e}  params={params}",
                flush=True,
            )
        return False

    arguments = {
        "func": objective,
        "bounds": [(0.0, 1.0)] * 5,
        "seed": seed,
        "maxiter": maxiter,
        "popsize": popsize,
        "tol": 1e-5,
        "atol": 0.1,
        "polish": polish,
        "workers": workers,
        "updating": "immediate" if workers == 1 else "deferred",
        "callback": report,
    }
    try:
        return differential_evolution(**arguments)
    except (OSError, PermissionError) as error:
        if workers == 1:
            raise
        print(
            f"Praca rownolegla niedostepna ({error}); ponawiam sekwencyjnie.",
            flush=True,
        )
        arguments["workers"] = 1
        arguments["updating"] = "immediate"
        return differential_evolution(**arguments)


def optimize_multistart(
    objective: NormalizedObjective,
    *,
    seed: int,
    starts: int,
    maxiter: int,
) -> OptimizeResult:
    if starts < 1:
        raise ValueError("starts must be at least one")
    random = np.random.default_rng(seed)
    initial = PARAMETER_SPACE.encode(FieldParams())
    candidates = [initial, *(random.random(5) for _ in range(starts - 1))]
    best: OptimizeResult | None = None
    for index, start in enumerate(candidates, start=1):
        result = minimize(
            objective,
            start,
            method="Nelder-Mead",
            bounds=[(0.0, 1.0)] * 5,
            options={
                "maxiter": maxiter,
                "xatol": 1e-5,
                "fatol": 0.1,
            },
        )
        print(
            f"start={index:2d}/{starts}  RMS={result.fun:10.2f} km  "
            f"sukces={result.success}",
            flush=True,
        )
        if best is None or result.fun < best.fun:
            best = result
    assert best is not None
    return best


def _score_to_json(score: GroupScore) -> dict[str, object]:
    return {
        "timestamp_utc": score.timestamp_utc.isoformat(),
        "observer_count": score.observer_count,
        "rms_km": score.rms_km,
        "common_point_km": score.common_point_km.tolist(),
        "minimum_forward_distance_km": score.minimum_forward_distance_km,
        "condition_number": score.condition_number,
    }


def write_result(
    path: Path,
    *,
    method: str,
    result: OptimizeResult,
    params: FieldParams,
    baseline: CostBreakdown,
    fitted: CostBreakdown,
    integration: IntegrationOptions,
) -> None:
    payload = {
        "schema_version": 1,
        "model": "axisymmetric-atmosphere-plus-gaussian-ring-v1",
        "coordinate_system": "x-y map plane, z altitude, kilometres",
        "method": method,
        "intersection_mode": fitted.intersection_mode,
        "optimizer": {
            "success": bool(result.success),
            "message": str(result.message),
            "evaluations": int(result.nfev),
        },
        "parameters": asdict(params),
        "parameter_space": asdict(PARAMETER_SPACE),
        "integration": asdict(integration),
        "baseline_cost_km": baseline.cost_km,
        "fitted_cost_km": fitted.cost_km,
        "invalid_rays": fitted.invalid_rays,
        "groups": [_score_to_json(score) for score in fitted.group_scores],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("de", "multistart"), default="de")
    parser.add_argument("--seed", type=int, default=20260915)
    parser.add_argument("--maxiter", type=int, default=120)
    parser.add_argument("--popsize", type=int, default=12)
    parser.add_argument("--starts", type=int, default=12)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-path-km", type=float, default=500_000.0)
    parser.add_argument("--rtol", type=float, default=1e-4)
    parser.add_argument("--atol", type=float, default=1e-7)
    parser.add_argument("--report-every", type=int, default=5)
    parser.add_argument("--polish", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--intersection",
        choices=("rays", "lines"),
        default="rays",
        help="Use physical outward rays (default) or legacy infinite lines.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = tuple(build_dataset())
    integration = IntegrationOptions(
        max_path_km=args.max_path_km,
        rtol=args.rtol,
        atol=args.atol,
    )
    objective = NormalizedObjective(dataset, integration, args.intersection)
    no_field = FieldParams(k=0, H=8, A=0, rho0=5000, s=1000)
    baseline = evaluate_field(
        no_field,
        dataset,
        integration,
        args.intersection,
    )
    print(
        f"Zbior: {len(dataset)} chwil; obserwatorow: "
        f"{[len(group.origins) for group in dataset]}"
    )
    print(f"Bazowy koszt n=1: {baseline.cost_km:.2f} km RMS srednio")

    if args.method == "de":
        result = optimize_de(
            objective,
            seed=args.seed,
            maxiter=args.maxiter,
            popsize=args.popsize,
            workers=args.workers,
            polish=args.polish,
            report_every=args.report_every,
        )
    else:
        result = optimize_multistart(
            objective,
            seed=args.seed,
            starts=args.starts,
            maxiter=args.maxiter,
        )

    params = PARAMETER_SPACE.decode(result.x)
    fitted = evaluate_field(params, dataset, integration, args.intersection)
    print("\nWynik dopasowania:")
    for name, value in asdict(params).items():
        print(f"  {name:5s} = {value:.9g}")
    print(f"  koszt = {fitted.cost_km:.2f} km RMS srednio")
    print(f"  poprawa = {baseline.cost_km - fitted.cost_km:.2f} km")
    print(f"  sukces optymalizatora = {result.success}: {result.message}")

    if args.output:
        write_result(
            args.output,
            method=args.method,
            result=result,
            params=params,
            baseline=baseline,
            fitted=fitted,
            integration=integration,
        )
        print(f"  zapisano = {args.output}")


if __name__ == "__main__":
    main()
