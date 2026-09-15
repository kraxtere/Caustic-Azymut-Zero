"""Mirror-aware numerical propagation for the local Maxwell dipole field."""

from __future__ import annotations

import math
from dataclasses import dataclass

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
