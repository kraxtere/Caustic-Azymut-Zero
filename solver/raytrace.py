"""Three-dimensional eikonal ray integration and line triangulation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

from .field import (
    FieldParams,
    n_and_grad as gaussian_n_and_grad,
    n_and_grad_components as gaussian_n_and_grad_components,
)
from .field_lens import (
    LensFieldParams,
    n_and_grad as lens_n_and_grad,
    n_and_grad_components as lens_n_and_grad_components,
)


RayStatus = Literal["escaped", "ground_hit", "max_path", "failed"]
FieldParameters = FieldParams | LensFieldParams


@dataclass(frozen=True)
class IntegrationOptions:
    max_path_km: float = 500_000.0
    rtol: float = 1e-5
    atol: float = 1e-8
    gradient_tolerance_per_km: float = 1e-9
    escape_sigma: float = 7.0
    maximum_step_km: float | None = None
    ground_tolerance_km: float = 1e-6


@dataclass(frozen=True)
class RayResult:
    point: np.ndarray
    direction: np.ndarray
    status: RayStatus
    path_length_km: float
    gradient_norm_per_km: float
    function_evaluations: int
    net_direction_change_deg: float | None = None
    background_path_bending_deg: float | None = None
    ring_path_bending_deg: float | None = None
    combined_path_bending_deg: float | None = None


@dataclass(frozen=True)
class TriangulationResult:
    point: np.ndarray
    rms_km: float
    perpendicular_distances_km: np.ndarray
    forward_distances_km: np.ndarray
    matrix_rank: int
    condition_number: float


def _escape_altitude_km(
    params: FieldParameters,
    options: IntegrationOptions,
) -> float:
    """Altitude above which the whole field has negligible gradient."""

    if isinstance(params, LensFieldParams):
        if params.family == "maxwell":
            raise ValueError(
                "exact Maxwell fish eye has no field-free asymptotic region; "
                "the Leonhardt variant requires a mirror boundary"
            )
        return max(0.0, float(params.centre_km[2]) + params.radius_km)

    heights = [0.0]
    tolerance = options.gradient_tolerance_per_km
    if params.k > 0:
        surface_gradient = params.k / params.H
        if surface_gradient > tolerance:
            heights.append(params.H * math.log(surface_gradient / tolerance))
    ring_gradient_scale = abs(params.A) / params.s
    if ring_gradient_scale / math.sqrt(math.e) > tolerance:
        # For v=z/s >= 1, the largest possible ring-gradient magnitude at
        # that altitude is (|A|/s) v exp(-v^2/2).  Find where this envelope
        # drops below tolerance; escape_sigma is a conservative hard cap.
        low, high = 1.0, options.escape_sigma
        for _ in range(48):
            middle = (low + high) / 2
            envelope = ring_gradient_scale * middle * math.exp(-middle**2 / 2)
            if envelope > tolerance:
                low = middle
            else:
                high = middle
        heights.append(high * params.s)
    return max(heights)


def _maximum_step_km(
    params: FieldParameters,
    options: IntegrationOptions,
) -> float:
    if options.maximum_step_km is not None:
        return options.maximum_step_km
    if isinstance(params, LensFieldParams):
        return min(500.0, max(2.0, params.radius_km / 100.0))
    if abs(params.A) > 0:
        # At least six accepted steps across two sigma of the narrowest ring.
        return min(500.0, max(2.0, params.s / 3.0))
    return 500.0


def _bending_diagnostics(
    path_lengths: np.ndarray,
    states: np.ndarray,
    params: FieldParameters,
    initial_direction: np.ndarray,
) -> tuple[float, float, float, float]:
    """Integrate component curvature along an already accepted ray path.

    Diagnostics are calculated after RK45 has finished, so requesting them
    cannot alter adaptive steps, the asymptotic ray, or the optimization cost.
    Each component value is the path integral of the magnitude of that
    component's perpendicular contribution to ``dT/ds``, expressed in degrees.
    Because differently directed curvature may cancel, the component integrals
    need not add up to the net angle between the initial and final directions.
    """

    final_direction = np.asarray(states[3:6, -1], dtype=float)
    final_norm = float(np.linalg.norm(final_direction))
    if final_norm == 0 or not np.all(np.isfinite(final_direction)):
        return math.nan, math.nan, math.nan, math.nan
    final_direction /= final_norm
    cosine = float(np.clip(np.dot(initial_direction, final_direction), -1.0, 1.0))
    net_direction_change_deg = math.degrees(math.acos(cosine))

    if path_lengths.size < 2:
        return net_direction_change_deg, 0.0, 0.0, 0.0

    background_curvature: list[float] = []
    ring_curvature: list[float] = []
    combined_curvature: list[float] = []
    for column in range(states.shape[1]):
        position = states[0:3, column]
        tangent = states[3:6, column]
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm == 0 or not np.all(np.isfinite(tangent)):
            return math.nan, math.nan, math.nan, math.nan
        tangent = tangent / tangent_norm
        if isinstance(params, LensFieldParams):
            refractive_index, background_gradient, ring_gradient = (
                lens_n_and_grad_components(position, params)
            )
        else:
            refractive_index, background_gradient, ring_gradient = (
                gaussian_n_and_grad_components(position, params)
            )
        background_acceleration = (
            background_gradient
            - np.dot(background_gradient, tangent) * tangent
        ) / refractive_index
        ring_acceleration = (
            ring_gradient - np.dot(ring_gradient, tangent) * tangent
        ) / refractive_index
        background_curvature.append(float(np.linalg.norm(background_acceleration)))
        ring_curvature.append(float(np.linalg.norm(ring_acceleration)))
        combined_curvature.append(
            float(np.linalg.norm(background_acceleration + ring_acceleration))
        )

    radians_to_degrees = 180.0 / math.pi
    background_bending = float(
        np.trapezoid(background_curvature, x=path_lengths)
    ) * radians_to_degrees
    ring_bending = float(
        np.trapezoid(ring_curvature, x=path_lengths)
    ) * radians_to_degrees
    combined_bending = float(
        np.trapezoid(combined_curvature, x=path_lengths)
    ) * radians_to_degrees
    return (
        net_direction_change_deg,
        background_bending,
        ring_bending,
        combined_bending,
    )


def trace_ray(
    origin: np.ndarray,
    direction: np.ndarray,
    params: FieldParameters,
    options: IntegrationOptions | None = None,
    *,
    collect_diagnostics: bool = False,
) -> RayResult:
    """Trace a backward ray until it reaches the field-free upper region.

    The returned point and direction define the asymptotic straight line.  A
    ray that returns to the map plane or fails to escape before the path limit
    is explicitly marked invalid rather than silently entering the fit.
    """

    params.validate()
    options = options or IntegrationOptions()
    origin = np.asarray(origin, dtype=float)
    direction = np.asarray(direction, dtype=float)
    direction_norm = float(np.linalg.norm(direction))
    if origin.shape != (3,) or direction.shape != (3,) or direction_norm == 0:
        raise ValueError("origin and non-zero direction must be three-vectors")
    initial_direction = direction / direction_norm

    escape_altitude = _escape_altitude_km(params, options)
    if escape_altitude == 0:
        return RayResult(
            point=origin.copy(),
            direction=initial_direction,
            status="escaped",
            path_length_km=0.0,
            gradient_norm_per_km=0.0,
            function_evaluations=0,
            net_direction_change_deg=0.0 if collect_diagnostics else None,
            background_path_bending_deg=0.0 if collect_diagnostics else None,
            ring_path_bending_deg=0.0 if collect_diagnostics else None,
            combined_path_bending_deg=0.0 if collect_diagnostics else None,
        )

    initial_state = np.concatenate([origin, initial_direction])

    field_n_and_grad = (
        lens_n_and_grad
        if isinstance(params, LensFieldParams)
        else gaussian_n_and_grad
    )

    def rhs(_path_length: float, state: np.ndarray) -> np.ndarray:
        position = state[0:3]
        tangent = state[3:6]
        refractive_index, gradient = field_n_and_grad(position, params)
        if not math.isfinite(refractive_index) or refractive_index <= 0.05:
            return np.full(6, np.nan)
        acceleration = (
            gradient - np.dot(gradient, tangent) * tangent
        ) / refractive_index
        return np.concatenate([tangent, acceleration])

    def escaped(_path_length: float, state: np.ndarray) -> float:
        return float(state[2] - escape_altitude)

    escaped.terminal = True
    escaped.direction = 1

    def hit_ground(_path_length: float, state: np.ndarray) -> float:
        return float(state[2] + options.ground_tolerance_km)

    hit_ground.terminal = True
    hit_ground.direction = -1

    solution = solve_ivp(
        rhs,
        (0.0, options.max_path_km),
        initial_state,
        method="RK45",
        rtol=options.rtol,
        atol=options.atol,
        max_step=_maximum_step_km(params, options),
        events=(escaped, hit_ground),
    )

    end_point = solution.y[0:3, -1]
    end_direction = solution.y[3:6, -1]
    norm = float(np.linalg.norm(end_direction))
    if norm > 0 and np.all(np.isfinite(end_direction)):
        end_direction = end_direction / norm

    _, end_gradient = field_n_and_grad(end_point, params)
    if not solution.success or not np.all(np.isfinite(solution.y[:, -1])):
        status: RayStatus = "failed"
    elif solution.t_events[1].size:
        status = "ground_hit"
    elif solution.t_events[0].size:
        status = "escaped"
    else:
        status = "max_path"

    diagnostics: tuple[float | None, float | None, float | None, float | None]
    if collect_diagnostics:
        diagnostics = _bending_diagnostics(
            solution.t,
            solution.y,
            params,
            initial_direction,
        )
    else:
        diagnostics = (None, None, None, None)

    return RayResult(
        point=end_point,
        direction=end_direction,
        status=status,
        path_length_km=float(solution.t[-1]),
        gradient_norm_per_km=float(np.linalg.norm(end_gradient)),
        function_evaluations=int(solution.nfev),
        net_direction_change_deg=diagnostics[0],
        background_path_bending_deg=diagnostics[1],
        ring_path_bending_deg=diagnostics[2],
        combined_path_bending_deg=diagnostics[3],
    )


def integrate_ray(
    origin: np.ndarray,
    direction: np.ndarray,
    params: FieldParameters,
    s_max: float = 500_000.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compatibility wrapper returning only the asymptotic line pair."""

    result = trace_ray(
        origin,
        direction,
        params,
        IntegrationOptions(max_path_km=s_max),
    )
    return result.point, result.direction


def triangulate_detailed(
    points: list[np.ndarray],
    directions: list[np.ndarray],
) -> TriangulationResult:
    """Least-squares common point of 3D lines, with fit diagnostics."""

    if len(points) != len(directions) or len(points) < 2:
        raise ValueError("triangulation needs matching lists of at least two lines")

    matrix = np.zeros((3, 3))
    right_hand_side = np.zeros(3)
    projectors: list[np.ndarray] = []
    normalized_directions: list[np.ndarray] = []
    for point, direction in zip(points, directions, strict=True):
        unit_direction = np.asarray(direction, dtype=float)
        unit_direction /= np.linalg.norm(unit_direction)
        projector = np.eye(3) - np.outer(unit_direction, unit_direction)
        matrix += projector
        right_hand_side += projector @ np.asarray(point, dtype=float)
        projectors.append(projector)
        normalized_directions.append(unit_direction)

    common_point, _, rank, _ = np.linalg.lstsq(
        matrix,
        right_hand_side,
        rcond=None,
    )
    perpendicular_distances = np.array(
        [
            np.linalg.norm(projector @ (common_point - point))
            for point, projector in zip(points, projectors, strict=True)
        ]
    )
    forward_distances = np.array(
        [
            np.dot(common_point - point, direction)
            for point, direction in zip(
                points,
                normalized_directions,
                strict=True,
            )
        ]
    )
    return TriangulationResult(
        point=common_point,
        rms_km=float(np.sqrt(np.mean(perpendicular_distances**2))),
        perpendicular_distances_km=perpendicular_distances,
        forward_distances_km=forward_distances,
        matrix_rank=int(rank),
        condition_number=float(np.linalg.cond(matrix)),
    )


def triangulate_half_lines_detailed(
    points: list[np.ndarray],
    directions: list[np.ndarray],
) -> TriangulationResult:
    """Best common point of outward half-lines rather than infinite lines.

    For a candidate behind a ray origin, the distance to that ray is the
    distance to its origin.  The resulting sum of squared distances is convex
    and continuously differentiable, so a three-variable BFGS solve is both
    cheap and deterministic.  This prevents a small but non-physical residual
    produced by intersections behind an observer.
    """

    line_result = triangulate_detailed(points, directions)
    point_arrays = [np.asarray(point, dtype=float) for point in points]
    unit_directions = [
        np.asarray(direction, dtype=float) / np.linalg.norm(direction)
        for direction in directions
    ]
    projectors = [
        np.eye(3) - np.outer(direction, direction)
        for direction in unit_directions
    ]

    def value_and_gradient(candidate: np.ndarray) -> tuple[float, np.ndarray]:
        value = 0.0
        gradient = np.zeros(3)
        for origin, direction, projector in zip(
            point_arrays,
            unit_directions,
            projectors,
            strict=True,
        ):
            offset = candidate - origin
            forward = float(np.dot(offset, direction))
            residual = projector @ offset if forward >= 0 else offset
            value += float(np.dot(residual, residual))
            gradient += 2 * residual
        return value, gradient

    optimization = minimize(
        value_and_gradient,
        line_result.point,
        method="BFGS",
        jac=True,
        options={"gtol": 1e-8, "maxiter": 100},
    )
    common_point = np.asarray(optimization.x, dtype=float)
    forward_distances = np.array(
        [
            np.dot(common_point - origin, direction)
            for origin, direction in zip(
                point_arrays,
                unit_directions,
                strict=True,
            )
        ]
    )
    distances = np.array(
        [
            np.linalg.norm(
                projector @ (common_point - origin)
                if forward >= 0
                else common_point - origin
            )
            for origin, projector, forward in zip(
                point_arrays,
                projectors,
                forward_distances,
                strict=True,
            )
        ]
    )
    return TriangulationResult(
        point=common_point,
        rms_km=float(np.sqrt(np.mean(distances**2))),
        perpendicular_distances_km=distances,
        forward_distances_km=forward_distances,
        matrix_rank=line_result.matrix_rank,
        condition_number=line_result.condition_number,
    )


def triangulate(
    points: list[np.ndarray],
    directions: list[np.ndarray],
) -> tuple[np.ndarray, float]:
    result = triangulate_detailed(points, directions)
    return result.point, result.rms_km


if __name__ == "__main__":
    field = FieldParams(k=0, H=8, A=0, rho0=5000, s=1000)
    start = np.array([0.0, 0.0, 0.0])
    initial = np.array([1.0, 0.5, 0.3])
    result = trace_ray(start, initial, field)
    expected = initial / np.linalg.norm(initial)
    print("Test n=1: status =", result.status)
    print("Test n=1: blad kierunku =", np.linalg.norm(result.direction - expected))
