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
