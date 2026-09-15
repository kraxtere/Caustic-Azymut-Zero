"""Analytic first-image contract for the three-dimensional Maxwell mirror.

The isotropic 3D fish-eye profile is the stereographic image of a three-sphere
S^3 embedded in R^4.  A physical ray is therefore a great circle on S^3.  The
spherical mirror at ``|x-centre|=R`` corresponds to the equator of S^3; folding
the northern hemisphere onto the southern one implements its specular
reflection without RK45 or event stepping.

One observation (position and direction) determines a folded great-circle
locus, not a unique arbitrary source.  Advancing exactly one imaging interval,
``central_angle=pi``, always reaches the conjugate point ``2*centre-position``
independently of direction.  That point is unique only if the observer is
assumed to sit at the perfect image of the source.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np


MODEL_STATUS = "v2-primary-analytic-first-image"


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _vector(value: np.ndarray, dimension: int, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.shape != (dimension,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite {dimension}-vector")
    return result


def _unit(value: np.ndarray, dimension: int, name: str) -> np.ndarray:
    result = _vector(value, dimension, name)
    norm = float(np.linalg.norm(result))
    if norm == 0.0:
        raise ValueError(f"{name} cannot be zero")
    return result / norm


def stereographic_to_three_sphere(
    point_xyz: np.ndarray,
    sphere_radius: float,
) -> np.ndarray:
    """Map physical R^3 to the auxiliary S^3 embedded in R^4."""

    point = _vector(point_xyz, 3, "point_xyz")
    radius = _positive(sphere_radius, "sphere_radius")
    norm_squared = float(np.dot(point, point))
    denominator = norm_squared + radius**2
    return np.concatenate(
        (
            2.0 * radius**2 * point / denominator,
            np.array(
                [radius * (norm_squared - radius**2) / denominator],
                dtype=float,
            ),
        )
    )


def stereographic_from_three_sphere(
    point_xyzw: np.ndarray,
    sphere_radius: float,
) -> np.ndarray:
    """Map a finite point of the auxiliary S^3 back to physical R^3."""

    point = _vector(point_xyzw, 4, "point_xyzw")
    radius = _positive(sphere_radius, "sphere_radius")
    if not math.isclose(
        float(np.linalg.norm(point)),
        radius,
        rel_tol=1e-10,
        abs_tol=1e-10 * radius,
    ):
        raise ValueError("point_xyzw must lie on the requested three-sphere")
    denominator = radius - float(point[3])
    if denominator <= 1e-14 * radius:
        raise ValueError("the north pole maps to infinity")
    return radius * point[:3] / denominator


def lift_direction_to_three_sphere(
    point_xyz: np.ndarray,
    direction_xyz: np.ndarray,
    sphere_radius: float,
) -> np.ndarray:
    """Push a physical ray direction through the stereographic differential."""

    point = _vector(point_xyz, 3, "point_xyz")
    direction = _unit(direction_xyz, 3, "direction_xyz")
    radius = _positive(sphere_radius, "sphere_radius")
    norm_squared = float(np.dot(point, point))
    point_direction = float(np.dot(point, direction))
    denominator = norm_squared + radius**2
    spatial = 2.0 * radius**2 * (
        direction * denominator - 2.0 * point * point_direction
    ) / denominator**2
    fourth = 4.0 * radius**3 * point_direction / denominator**2
    tangent = np.concatenate((spatial, np.array([fourth], dtype=float)))
    return _unit(tangent, 4, "lifted tangent")


def _lower_hemisphere_fold(
    point_xyzw: np.ndarray,
    tangent_xyzw: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    point = point_xyzw.copy()
    tangent = tangent_xyzw.copy()
    if point[3] > 0.0:
        point[3] *= -1.0
        tangent[3] *= -1.0
        return point, tangent, 1
    return point, tangent, 0


def _physical_direction_from_three_sphere(
    point_xyzw: np.ndarray,
    tangent_xyzw: np.ndarray,
    sphere_radius: float,
) -> np.ndarray:
    radius = _positive(sphere_radius, "sphere_radius")
    denominator = radius - float(point_xyzw[3])
    derivative = radius * (
        tangent_xyzw[:3] * denominator
        + point_xyzw[:3] * tangent_xyzw[3]
    ) / denominator**2
    return _unit(derivative, 3, "physical tangent")


@dataclass(frozen=True)
class MaxwellGreatCircleConstraint:
    """The S^3 great-circle plane supplied by one observation."""

    sphere_point: np.ndarray
    sphere_tangent: np.ndarray

    @property
    def plane_projector(self) -> np.ndarray:
        basis = np.column_stack((self.sphere_point, self.sphere_tangent))
        basis, _ = np.linalg.qr(basis)
        return basis @ basis.T


@dataclass(frozen=True)
class MaxwellMirrorRayState:
    """Analytic state along the first positive imaging interval."""

    point_xyz: np.ndarray
    direction_xyz: np.ndarray
    central_angle_rad: float
    optical_path_n0_km: float
    reflection_count: int
    unfolded_point_xyzw: np.ndarray
    folded_point_xyzw: np.ndarray


@dataclass(frozen=True)
class MaxwellGreatCircleFit:
    """Closed-form common point of consistently unfolded great circles."""

    point_xyzw: np.ndarray
    point_xyz: np.ndarray
    rms_plane_distance: float
    eigenvalues: np.ndarray
    forward_observation_count: int
    observation_count: int
    sign_margin: float
    inside_mirror: bool


@dataclass(frozen=True)
class MaxwellBranchRun:
    """One alternating discrete/continuous mirror-branch run."""

    initial_reflection_parities: tuple[bool, ...]
    reflection_parities: tuple[bool, ...]
    fit: MaxwellGreatCircleFit
    objective_history: tuple[float, ...]
    iterations: int
    converged: bool


@dataclass(frozen=True)
class MaxwellBranchSearchResult:
    """Best branch fit plus all auditable restart outcomes."""

    best: MaxwellBranchRun
    runs: tuple[MaxwellBranchRun, ...]
    seed: int


def maxwell_great_circle_constraint(
    position_xyz: np.ndarray,
    direction_xyz: np.ndarray,
    mirror_radius: float,
    centre_xyz: np.ndarray | None = None,
) -> MaxwellGreatCircleConstraint:
    """Return the analytic ray locus determined by one 3D observation."""

    centre = (
        np.zeros(3)
        if centre_xyz is None
        else _vector(centre_xyz, 3, "centre_xyz")
    )
    relative = _vector(position_xyz, 3, "position_xyz") - centre
    radius = _positive(mirror_radius, "mirror_radius")
    if float(np.linalg.norm(relative)) >= radius:
        raise ValueError("position_xyz must lie strictly inside the mirror")
    sphere_point = stereographic_to_three_sphere(relative, radius)
    sphere_tangent = lift_direction_to_three_sphere(
        relative,
        direction_xyz,
        radius,
    )
    sphere_tangent -= (
        float(np.dot(sphere_tangent, sphere_point)) / radius**2
    ) * sphere_point
    sphere_tangent = _unit(sphere_tangent, 4, "sphere_tangent")
    return MaxwellGreatCircleConstraint(sphere_point, sphere_tangent)


def triangulate_maxwell_great_circles(
    constraints: Sequence[MaxwellGreatCircleConstraint],
    *,
    reflection_parities: Sequence[bool] | None = None,
    centre_xyz: np.ndarray | None = None,
    degeneracy_tolerance: float = 1e-10,
) -> MaxwellGreatCircleFit:
    """Fit one point on S^3 to consistently unfolded ray planes.

    A great circle on S^3 is a two-dimensional plane in R^4.  If ``P_i`` is
    its orthogonal projector, the constrained least-squares problem is

    ``min X.T @ sum(I-P_i) @ X`` subject to ``|X|=R``.

    Its solution is the eigenvector belonging to the smallest eigenvalue of
    the 4x4 matrix.  The antipodal sign is selected by the oriented tangents:
    on the first positive interval, ``t_i dot X`` must be non-negative.

    ``reflection_parities[i]`` selects the equator-reflected representation
    ``J P_i J`` for observation ``i``.  Once this discrete assignment is
    fixed, mixed branches are still solved by one eigendecomposition.
    """

    items = tuple(constraints)
    if len(items) < 2:
        raise ValueError("at least two great-circle constraints are required")
    tolerance = _positive(degeneracy_tolerance, "degeneracy_tolerance")
    parities = (
        (False,) * len(items)
        if reflection_parities is None
        else tuple(bool(value) for value in reflection_parities)
    )
    if len(parities) != len(items):
        raise ValueError("reflection_parities must match constraints")
    centre = (
        np.zeros(3)
        if centre_xyz is None
        else _vector(centre_xyz, 3, "centre_xyz")
    )

    radii = np.array(
        [float(np.linalg.norm(item.sphere_point)) for item in items],
        dtype=float,
    )
    radius = _positive(float(radii[0]), "constraint sphere radius")
    if not np.allclose(radii, radius, rtol=1e-10, atol=1e-12 * radius):
        raise ValueError("all constraints must use the same sphere radius")

    identity = np.eye(4)
    equator_reflection = np.diag([1.0, 1.0, 1.0, -1.0])
    normal_matrix = np.zeros((4, 4), dtype=float)
    fitted_projectors: list[np.ndarray] = []
    fitted_tangents: list[np.ndarray] = []
    for item, reflected in zip(items, parities, strict=True):
        point = _vector(item.sphere_point, 4, "constraint sphere_point")
        tangent = _unit(item.sphere_tangent, 4, "constraint sphere_tangent")
        if not math.isclose(
            float(np.dot(point, tangent)),
            0.0,
            rel_tol=0.0,
            abs_tol=1e-10 * radius,
        ):
            raise ValueError("constraint tangent must be orthogonal to point")
        projector = item.plane_projector
        if reflected:
            projector = equator_reflection @ projector @ equator_reflection
            tangent = equator_reflection @ tangent
        fitted_projectors.append(projector)
        fitted_tangents.append(tangent)
        normal_matrix += identity - projector

    normal_matrix = 0.5 * (normal_matrix + normal_matrix.T)
    eigenvalues, eigenvectors = np.linalg.eigh(normal_matrix)
    scale = max(1.0, float(eigenvalues[-1]))
    if float(eigenvalues[1] - eigenvalues[0]) <= tolerance * scale:
        raise ValueError("great-circle constraints do not define a unique axis")

    candidate = radius * eigenvectors[:, 0]
    signed_sines = np.array(
        [float(np.dot(tangent, candidate) / radius) for tangent in fitted_tangents]
    )
    positive_count = int(np.count_nonzero(signed_sines >= -tolerance))
    negative_count = int(np.count_nonzero(signed_sines <= tolerance))
    signed_sum = float(np.sum(signed_sines))
    if negative_count > positive_count or (
        negative_count == positive_count and signed_sum < 0.0
    ):
        candidate *= -1.0
        signed_sines *= -1.0
        positive_count, negative_count = negative_count, positive_count

    residual_squares = np.array(
        [
            float(
                np.dot(
                    (identity - projector) @ candidate,
                    (identity - projector) @ candidate,
                )
            )
            for projector in fitted_projectors
        ],
        dtype=float,
    )
    point_xyz = stereographic_from_three_sphere(candidate, radius) + centre
    return MaxwellGreatCircleFit(
        point_xyzw=candidate,
        point_xyz=point_xyz,
        rms_plane_distance=float(math.sqrt(np.mean(residual_squares))),
        eigenvalues=eigenvalues,
        forward_observation_count=positive_count,
        observation_count=len(items),
        sign_margin=abs(float(np.sum(signed_sines))),
        inside_mirror=bool(candidate[3] <= tolerance * radius),
    )


def solve_maxwell_mirror_branches(
    constraints: Sequence[MaxwellGreatCircleConstraint],
    *,
    restarts: int = 8,
    seed: int = 0,
    max_iterations: int = 100,
    switch_tolerance: float = 1e-12,
    centre_xyz: np.ndarray | None = None,
    degeneracy_tolerance: float = 1e-10,
) -> MaxwellBranchSearchResult:
    """Alternate a 4x4 fit with independent mirror-branch assignments.

    The first run starts with every observation on ``P_i``.  Remaining runs
    use distinct seeded random assignments.  At fixed ``X``, a branch changes
    only when its alternative lowers the squared plane distance by more than
    ``switch_tolerance * R^2``.  The following eigensolve cannot increase the
    objective, so every accepted state change is monotonic.
    """

    items = tuple(constraints)
    if len(items) < 2:
        raise ValueError("at least two great-circle constraints are required")
    if isinstance(restarts, bool) or int(restarts) != restarts or restarts <= 0:
        raise ValueError("restarts must be a positive integer")
    if (
        isinstance(max_iterations, bool)
        or int(max_iterations) != max_iterations
        or max_iterations <= 0
    ):
        raise ValueError("max_iterations must be a positive integer")
    tolerance = float(switch_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("switch_tolerance must be finite and non-negative")
    if isinstance(seed, bool) or int(seed) != seed or seed < 0:
        raise ValueError("seed must be a non-negative integer")

    radius = _positive(
        float(np.linalg.norm(items[0].sphere_point)),
        "constraint sphere radius",
    )
    requested_restarts = int(restarts)
    maximum_distinct = 1 << len(items)
    target_restarts = min(requested_restarts, maximum_distinct)
    seed_value = int(seed)
    rng = np.random.default_rng(seed_value)
    starts: list[tuple[bool, ...]] = [(False,) * len(items)]
    seen = set(starts)
    while len(starts) < target_restarts:
        candidate = tuple(
            bool(value) for value in rng.integers(0, 2, size=len(items))
        )
        if candidate not in seen:
            seen.add(candidate)
            starts.append(candidate)

    identity = np.eye(4)
    equator_reflection = np.diag([1.0, 1.0, 1.0, -1.0])
    base_projectors = tuple(item.plane_projector for item in items)
    reflected_projectors = tuple(
        equator_reflection @ projector @ equator_reflection
        for projector in base_projectors
    )
    threshold = tolerance * radius**2
    runs: list[MaxwellBranchRun] = []

    for initial in starts:
        parities = initial
        history: list[float] = []
        converged = False
        fit: MaxwellGreatCircleFit | None = None
        for _ in range(int(max_iterations)):
            fit = triangulate_maxwell_great_circles(
                items,
                reflection_parities=parities,
                centre_xyz=centre_xyz,
                degeneracy_tolerance=degeneracy_tolerance,
            )
            history.append(fit.rms_plane_distance**2)
            point = fit.point_xyzw
            updated = list(parities)
            for index, reflected in enumerate(parities):
                current_projector = (
                    reflected_projectors[index]
                    if reflected
                    else base_projectors[index]
                )
                alternate_projector = (
                    base_projectors[index]
                    if reflected
                    else reflected_projectors[index]
                )
                current_residual = (identity - current_projector) @ point
                alternate_residual = (identity - alternate_projector) @ point
                current_squared = float(np.dot(current_residual, current_residual))
                alternate_squared = float(
                    np.dot(alternate_residual, alternate_residual)
                )
                if alternate_squared + threshold < current_squared:
                    updated[index] = not reflected
            updated_parities = tuple(updated)
            if updated_parities == parities:
                converged = True
                break
            parities = updated_parities

        if fit is None:
            raise RuntimeError("branch solver did not execute")
        if not converged:
            fit = triangulate_maxwell_great_circles(
                items,
                reflection_parities=parities,
                centre_xyz=centre_xyz,
                degeneracy_tolerance=degeneracy_tolerance,
            )
            history.append(fit.rms_plane_distance**2)
        runs.append(
            MaxwellBranchRun(
                initial_reflection_parities=initial,
                reflection_parities=parities,
                fit=fit,
                objective_history=tuple(history),
                iterations=len(history),
                converged=converged,
            )
        )

    physical_runs = [run for run in runs if run.fit.inside_mirror]
    eligible_runs = physical_runs if physical_runs else runs
    best = min(
        eligible_runs,
        key=lambda run: (
            run.fit.rms_plane_distance,
            -run.fit.forward_observation_count,
            -run.fit.sign_margin,
        ),
    )
    return MaxwellBranchSearchResult(
        best=best,
        runs=tuple(runs),
        seed=seed_value,
    )


def trace_maxwell_mirror_analytic(
    position_xyz: np.ndarray,
    direction_xyz: np.ndarray,
    mirror_radius: float,
    central_angle_rad: float,
    *,
    n0: float = 1.0,
    centre_xyz: np.ndarray | None = None,
) -> MaxwellMirrorRayState:
    """Evaluate a reflected ray for ``0 <= central_angle_rad <= pi``.

    ``central_angle_rad`` is a forward-only path parameter on the auxiliary
    sphere.  The corresponding optical path is ``n0 * R * angle``.
    """

    angle = float(central_angle_rad)
    if not math.isfinite(angle) or angle < 0.0 or angle > math.pi:
        raise ValueError("central_angle_rad must be finite and in [0, pi]")
    radius = _positive(mirror_radius, "mirror_radius")
    index_scale = _positive(n0, "n0")
    centre = (
        np.zeros(3)
        if centre_xyz is None
        else _vector(centre_xyz, 3, "centre_xyz")
    )
    constraint = maxwell_great_circle_constraint(
        position_xyz,
        direction_xyz,
        radius,
        centre,
    )
    sphere_point = constraint.sphere_point
    sphere_tangent = constraint.sphere_tangent
    unfolded_point = (
        sphere_point * math.cos(angle)
        + radius * sphere_tangent * math.sin(angle)
    )
    unfolded_tangent = (
        -sphere_point * math.sin(angle) / radius
        + sphere_tangent * math.cos(angle)
    )
    folded_point, folded_tangent, reflection_count = _lower_hemisphere_fold(
        unfolded_point,
        unfolded_tangent,
    )
    physical_point = (
        stereographic_from_three_sphere(folded_point, radius) + centre
    )
    physical_direction = _physical_direction_from_three_sphere(
        folded_point,
        folded_tangent,
        radius,
    )
    return MaxwellMirrorRayState(
        point_xyz=physical_point,
        direction_xyz=physical_direction,
        central_angle_rad=angle,
        optical_path_n0_km=index_scale * radius * angle,
        reflection_count=reflection_count,
        unfolded_point_xyzw=unfolded_point,
        folded_point_xyzw=folded_point,
    )


def maxwell_mirror_conjugate(
    position_xyz: np.ndarray,
    centre_xyz: np.ndarray | None = None,
) -> np.ndarray:
    """Return the first perfect-image conjugate ``2*centre-position``.

    The formula does not accept a direction on purpose: after one imaging
    interval every great circle through the position reaches this same point.
    It is not a unique arbitrary-source estimate from a single observation.
    """

    position = _vector(position_xyz, 3, "position_xyz")
    centre = (
        np.zeros(3)
        if centre_xyz is None
        else _vector(centre_xyz, 3, "centre_xyz")
    )
    return 2.0 * centre - position
