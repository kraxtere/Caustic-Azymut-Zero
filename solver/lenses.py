"""Analytic reference models for spherical gradient-index lenses.

This module intentionally contains no numerical ray integrator.  It provides
closed-form invariants and trajectories that can certify a future numerical
implementation before Maxwell or Luneburg profiles are adapted to the
plane-plus-dome geometry used by the inverse solver.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _unit(vector: np.ndarray, name: str) -> np.ndarray:
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite three-vector")
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError(f"{name} cannot be zero")
    return vector / norm


def maxwell_fisheye_index(
    radial_distance: float,
    scale_radius: float,
    n0: float = 1.0,
) -> float:
    """Return ``2 n0 / (1 + (r/R0)^2)`` for Maxwell's fish eye."""

    radial_distance = float(radial_distance)
    scale_radius = _positive(scale_radius, "scale_radius")
    n0 = _positive(n0, "n0")
    if not math.isfinite(radial_distance) or radial_distance < 0:
        raise ValueError("radial_distance must be finite and non-negative")
    return 2.0 * n0 / (1.0 + (radial_distance / scale_radius) ** 2)


def stereographic_to_sphere(
    point_xy: np.ndarray,
    sphere_radius: float = 1.0,
) -> np.ndarray:
    """Map the fish-eye plane to its native virtual sphere.

    The plane origin maps to the south pole, the circle ``r=R`` to the
    equator, and infinity to the north pole.
    """

    point_xy = np.asarray(point_xy, dtype=float)
    sphere_radius = _positive(sphere_radius, "sphere_radius")
    if point_xy.shape != (2,) or not np.all(np.isfinite(point_xy)):
        raise ValueError("point_xy must be a finite two-vector")
    x, y = (float(value) for value in point_xy)
    radius_squared = x * x + y * y
    denominator = radius_squared + sphere_radius**2
    return np.array(
        [
            2.0 * sphere_radius**2 * x / denominator,
            2.0 * sphere_radius**2 * y / denominator,
            sphere_radius
            * (radius_squared - sphere_radius**2)
            / denominator,
        ],
        dtype=float,
    )


def stereographic_from_sphere(
    point_xyz: np.ndarray,
    sphere_radius: float = 1.0,
) -> np.ndarray:
    """Map a point on the virtual sphere back to the fish-eye plane."""

    point_xyz = np.asarray(point_xyz, dtype=float)
    sphere_radius = _positive(sphere_radius, "sphere_radius")
    if point_xyz.shape != (3,) or not np.all(np.isfinite(point_xyz)):
        raise ValueError("point_xyz must be a finite three-vector")
    if not math.isclose(
        float(np.linalg.norm(point_xyz)),
        sphere_radius,
        rel_tol=1e-10,
        abs_tol=1e-12,
    ):
        raise ValueError("point_xyz must lie on the requested sphere")
    denominator = sphere_radius - float(point_xyz[2])
    if denominator <= 1e-14 * sphere_radius:
        raise ValueError("the north pole maps to infinity")
    return sphere_radius * point_xyz[0:2] / denominator


def maxwell_spherical_ray(
    source_xyz: np.ndarray,
    tangent_xyz: np.ndarray,
    central_angle_rad: float,
    sphere_radius: float = 1.0,
) -> np.ndarray:
    """Evaluate the great-circle ray on the fish eye's virtual sphere."""

    sphere_radius = _positive(sphere_radius, "sphere_radius")
    source_direction = _unit(source_xyz, "source_xyz")
    if not math.isclose(
        float(np.linalg.norm(source_xyz)),
        sphere_radius,
        rel_tol=1e-10,
        abs_tol=1e-12,
    ):
        raise ValueError("source_xyz must lie on the requested sphere")
    tangent_xyz = np.asarray(tangent_xyz, dtype=float)
    tangent_xyz = tangent_xyz - np.dot(tangent_xyz, source_direction) * (
        source_direction
    )
    tangent_direction = _unit(tangent_xyz, "tangent_xyz")
    angle = float(central_angle_rad)
    if not math.isfinite(angle):
        raise ValueError("central_angle_rad must be finite")
    return sphere_radius * (
        source_direction * math.cos(angle)
        + tangent_direction * math.sin(angle)
    )


def maxwell_mirror_image(point_xy: np.ndarray, mirror_radius: float) -> np.ndarray:
    """Return the diametrically opposite image inside a fish-eye mirror."""

    point_xy = np.asarray(point_xy, dtype=float)
    mirror_radius = _positive(mirror_radius, "mirror_radius")
    if point_xy.shape != (2,) or not np.all(np.isfinite(point_xy)):
        raise ValueError("point_xy must be a finite two-vector")
    if float(np.linalg.norm(point_xy)) > mirror_radius * (1.0 + 1e-12):
        raise ValueError("point_xy must be inside the mirror")
    return -point_xy


def luneburg_index(radial_distance: float, lens_radius: float) -> float:
    """Return the standard Luneburg profile inside a sphere and 1 outside."""

    radial_distance = float(radial_distance)
    lens_radius = _positive(lens_radius, "lens_radius")
    if not math.isfinite(radial_distance) or radial_distance < 0:
        raise ValueError("radial_distance must be finite and non-negative")
    if radial_distance >= lens_radius:
        return 1.0
    return math.sqrt(2.0 - (radial_distance / lens_radius) ** 2)


@dataclass(frozen=True)
class LuneburgRayState:
    point: np.ndarray
    optical_momentum: np.ndarray


def luneburg_ray_state(
    entry_point: np.ndarray,
    incoming_direction: np.ndarray,
    optical_parameter: float,
    lens_radius: float = 1.0,
) -> LuneburgRayState:
    """Evaluate the exact interior ray of a standard Luneburg lens.

    With Hamiltonian ``(|p|^2-n^2)/2=0`` and
    ``n^2=2-|r|^2/R^2``, the ray obeys ``r''=-r/R^2``.  At the boundary
    ``n=1``, so optical momentum equals the incoming unit direction.
    """

    lens_radius = _positive(lens_radius, "lens_radius")
    entry_point = np.asarray(entry_point, dtype=float)
    incoming_direction = _unit(incoming_direction, "incoming_direction")
    if entry_point.shape != (3,) or not np.all(np.isfinite(entry_point)):
        raise ValueError("entry_point must be a finite three-vector")
    if not math.isclose(
        float(np.linalg.norm(entry_point)),
        lens_radius,
        rel_tol=1e-10,
        abs_tol=1e-12,
    ):
        raise ValueError("entry_point must lie on the lens surface")
    if float(np.dot(entry_point, incoming_direction)) >= 0:
        raise ValueError("incoming_direction must point into the lens")
    optical_parameter = float(optical_parameter)
    if not math.isfinite(optical_parameter):
        raise ValueError("optical_parameter must be finite")

    phase = optical_parameter / lens_radius
    point = (
        entry_point * math.cos(phase)
        + lens_radius * incoming_direction * math.sin(phase)
    )
    momentum = (
        incoming_direction * math.cos(phase)
        - (entry_point / lens_radius) * math.sin(phase)
    )
    return LuneburgRayState(point=point, optical_momentum=momentum)


def luneburg_surface_focus(
    incoming_direction: np.ndarray,
    lens_radius: float = 1.0,
) -> np.ndarray:
    """Return the common surface focus of a parallel incoming ray bundle."""

    lens_radius = _positive(lens_radius, "lens_radius")
    return lens_radius * _unit(incoming_direction, "incoming_direction")
