"""Mirror-aware numerical propagation for the local Maxwell dipole field."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from .field_lens import LensFieldParams, n_and_grad


@dataclass(frozen=True)
class NumericalMaxwellRayState:
    point_xyz: np.ndarray
    direction_xyz: np.ndarray
    optical_path_n0_km: float
    physical_path_km: float
    reflection_count: int
    function_evaluations: int


@dataclass(frozen=True)
class LocalMaxwellCurveSegment:
    optical_start: float
    optical_end: float
    dense_solution: Any


@dataclass(frozen=True)
class LocalMaxwellCurve:
    params: LensFieldParams
    segments: tuple[LocalMaxwellCurveSegment, ...]
    reflection_count: int
    function_evaluations: int

    def state_at_angle(self, central_angle_rad: float) -> tuple[np.ndarray, np.ndarray]:
        angle = float(central_angle_rad)
        if not math.isfinite(angle) or angle < 0.0 or angle > math.pi:
            raise ValueError("central_angle_rad must be finite and in [0, pi]")
        optical_path = self.params.n0 * self.params.radius_km * angle
        segment = next(
            (
                item
                for item in self.segments
                if item.optical_start - 1e-12 <= optical_path
                <= item.optical_end + 1e-12
            ),
            None,
        )
        if segment is None:
            raise RuntimeError("requested angle is outside the integrated curve")
        state = segment.dense_solution(optical_path)
        return state[:3], _unit(state[3:6], "interpolated tangent")


def _unit(vector: np.ndarray, name: str) -> np.ndarray:
    value = np.asarray(vector, dtype=float)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ValueError(f"{name} must be a finite three-vector")
    norm = float(np.linalg.norm(value))
    if norm == 0.0:
        raise ValueError(f"{name} cannot be zero")
    return value / norm


def trace_local_maxwell_to_central_angle(
    position_xyz: np.ndarray,
    direction_xyz: np.ndarray,
    params: LensFieldParams,
    central_angle_rad: float,
    *,
    rtol: float = 1e-10,
    atol: float = 1e-12,
    maximum_step_fraction: float = 1.0 / 500.0,
    maximum_reflections: int = 8,
) -> NumericalMaxwellRayState:
    """Integrate to ``Lopt=n0*R*central_angle`` with mirror reflections."""

    params.validate()
    if params.family != "maxwell":
        raise ValueError("numerical local propagation requires family='maxwell'")
    angle = float(central_angle_rad)
    if not math.isfinite(angle) or angle < 0.0 or angle > math.pi:
        raise ValueError("central_angle_rad must be finite and in [0, pi]")
    if not math.isfinite(maximum_step_fraction) or maximum_step_fraction <= 0.0:
        raise ValueError("maximum_step_fraction must be finite and positive")
    if maximum_reflections < 0:
        raise ValueError("maximum_reflections must be non-negative")

    centre = np.asarray(params.centre_km, dtype=float)
    radius = float(params.radius_km)
    position = np.asarray(position_xyz, dtype=float)
    if position.shape != (3,) or not np.all(np.isfinite(position)):
        raise ValueError("position_xyz must be a finite three-vector")
    if float(np.linalg.norm(position - centre)) >= radius:
        raise ValueError("position_xyz must lie strictly inside the mirror")
    direction = _unit(direction_xyz, "direction_xyz")
    target_optical_path = params.n0 * radius * angle
    if target_optical_path == 0.0:
        return NumericalMaxwellRayState(
            point_xyz=position.copy(),
            direction_xyz=direction,
            optical_path_n0_km=0.0,
            physical_path_km=0.0,
            reflection_count=0,
            function_evaluations=0,
        )

    optical_path = 0.0
    physical_path = 0.0
    reflections = 0
    evaluations = 0
    maximum_step = radius * maximum_step_fraction
    boundary_nudge = radius * 1e-11

    while optical_path < target_optical_path:
        initial = np.concatenate(
            (position, direction, np.array([optical_path], dtype=float))
        )

        def rhs(_path: float, state: np.ndarray) -> np.ndarray:
            tangent = _unit(state[3:6], "integrated tangent")
            index, gradient = n_and_grad(state[0:3], params)
            acceleration = (
                gradient - float(np.dot(gradient, tangent)) * tangent
            ) / index
            return np.concatenate((tangent, acceleration, np.array([index])))

        def reached_target(_path: float, state: np.ndarray) -> float:
            return float(state[6] - target_optical_path)

        reached_target.terminal = True
        reached_target.direction = 1

        def reached_mirror(_path: float, state: np.ndarray) -> float:
            return float(np.linalg.norm(state[0:3] - centre) - radius)

        reached_mirror.terminal = True
        reached_mirror.direction = 1

        remaining_scale = max(1.0, target_optical_path - optical_path)
        solution = solve_ivp(
            rhs,
            (0.0, 4.0 * radius + remaining_scale / params.n0),
            initial,
            method="DOP853",
            rtol=rtol,
            atol=atol,
            max_step=maximum_step,
            events=(reached_target, reached_mirror),
        )
        evaluations += solution.nfev
        if not solution.success:
            raise RuntimeError(f"local Maxwell integration failed: {solution.message}")
        physical_path += float(solution.t[-1])
        state = solution.y[:, -1]
        position = state[0:3]
        direction = _unit(state[3:6], "final integrated tangent")
        optical_path = float(state[6])

        hit_target = len(solution.t_events[0]) > 0
        hit_mirror = len(solution.t_events[1]) > 0
        if hit_target:
            break
        if not hit_mirror:
            raise RuntimeError("integration reached neither target nor mirror")
        if reflections >= maximum_reflections:
            raise RuntimeError("maximum_reflections exceeded")

        normal = _unit(position - centre, "mirror normal")
        position = centre + radius * normal
        direction = _unit(
            direction - 2.0 * float(np.dot(direction, normal)) * normal,
            "reflected direction",
        )
        position = position + boundary_nudge * direction
        reflections += 1

    return NumericalMaxwellRayState(
        point_xyz=position,
        direction_xyz=direction,
        optical_path_n0_km=optical_path,
        physical_path_km=physical_path,
        reflection_count=reflections,
        function_evaluations=evaluations,
    )


def build_local_maxwell_curve(
    position_xyz: np.ndarray,
    direction_xyz: np.ndarray,
    params: LensFieldParams,
    *,
    rtol: float = 1e-9,
    atol: float = 1e-11,
    maximum_step_fraction: float = 1.0 / 300.0,
    maximum_reflections: int = 8,
) -> LocalMaxwellCurve:
    """Integrate one complete first-interval curve, dense in optical angle."""

    params.validate()
    if params.family != "maxwell":
        raise ValueError("curve construction requires family='maxwell'")
    centre = np.asarray(params.centre_km, dtype=float)
    radius = params.radius_km
    position = np.asarray(position_xyz, dtype=float)
    direction = _unit(direction_xyz, "direction_xyz")
    if float(np.linalg.norm(position - centre)) >= radius:
        raise ValueError("position_xyz must lie strictly inside the mirror")
    target = params.n0 * radius * math.pi
    optical = 0.0
    physical = 0.0
    reflections = 0
    evaluations = 0
    segments: list[LocalMaxwellCurveSegment] = []
    nudge = radius * 1e-11

    while optical < target - 1e-12:
        initial = np.concatenate((position, direction, np.array([physical])))

        def rhs(_optical: float, state: np.ndarray) -> np.ndarray:
            tangent = _unit(state[3:6], "integrated tangent")
            index, gradient = n_and_grad(state[:3], params)
            perpendicular = gradient - float(np.dot(gradient, tangent)) * tangent
            return np.concatenate(
                (tangent / index, perpendicular / index**2, np.array([1.0 / index]))
            )

        def mirror(_optical: float, state: np.ndarray) -> float:
            return float(np.linalg.norm(state[:3] - centre) - radius)

        mirror.terminal = True
        mirror.direction = 1
        solution = solve_ivp(
            rhs,
            (optical, target),
            initial,
            method="DOP853",
            rtol=rtol,
            atol=atol,
            max_step=params.n0 * radius * maximum_step_fraction,
            events=(mirror,),
            dense_output=True,
        )
        if not solution.success or solution.sol is None:
            raise RuntimeError(f"curve integration failed: {solution.message}")
        evaluations += solution.nfev
        end = float(solution.t[-1])
        segments.append(LocalMaxwellCurveSegment(optical, end, solution.sol))
        state = solution.y[:, -1]
        position = state[:3]
        direction = _unit(state[3:6], "curve tangent")
        physical = float(state[6])
        optical = end
        if optical >= target - 1e-12:
            break
        if reflections >= maximum_reflections:
            raise RuntimeError("maximum_reflections exceeded")
        normal = _unit(position - centre, "mirror normal")
        position = centre + radius * normal
        direction = _unit(
            direction - 2.0 * float(np.dot(direction, normal)) * normal,
            "reflected direction",
        )
        position = position + nudge * direction
        reflections += 1
    return LocalMaxwellCurve(params, tuple(segments), reflections, evaluations)
