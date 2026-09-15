"""Maxwell v2 field and archived Luneburg hybrid reference.

The refractive-index functions expose the same ``n_and_grad`` and
``n_and_grad_components`` call shape as the archived Gaussian-ring field. No
numerical ray integration is used by the native focusing helpers: Maxwell is
evaluated as great circles on its virtual sphere and Luneburg as an exact
harmonic Hamiltonian trajectory.

Hybrid use needs an explicit boundary contract. A Luneburg sphere naturally
joins an exterior ``n=1`` medium at ``r=R``. An exact Maxwell fish eye either
extends over the whole stereographic plane or uses the equatorial mirror from
Leonhardt (2009); silently truncating it at ``R0`` would change the model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np


LensFamily = Literal["maxwell", "luneburg"]
MODEL_STATUS = "v2-maxwell-primary"
FAMILY_STATUS = {
    "maxwell": "v2-primary-analytic-mirror-contract",
    "luneburg": "v2-falsified-hybrid",
}


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


@dataclass(frozen=True)
class LensFieldParams:
    """Spherically symmetric v2 field parameters.

    ``centre_km`` is deliberately explicit so the later plane-plus-dome
    adapter cannot accidentally assume a lens placement.
    """

    family: LensFamily
    radius_km: float
    n0: float = 1.0
    centre_km: tuple[float, float, float] = (0.0, 0.0, 0.0)
    dipole_epsilon: float = 0.0

    def validate(self) -> None:
        if self.family not in {"maxwell", "luneburg"}:
            raise ValueError("family must be 'maxwell' or 'luneburg'")
        _positive(self.radius_km, "radius_km")
        _positive(self.n0, "n0")
        centre = np.asarray(self.centre_km, dtype=float)
        if centre.shape != (3,) or not np.all(np.isfinite(centre)):
            raise ValueError("centre_km must be a finite three-vector")
        if self.family == "luneburg" and self.n0 != 1.0:
            raise ValueError("the specified Luneburg profile has fixed n0=1")
        if not math.isfinite(self.dipole_epsilon):
            raise ValueError("dipole_epsilon must be finite")
        if self.family == "luneburg" and self.dipole_epsilon != 0.0:
            raise ValueError("dipole_epsilon is only defined for Maxwell")


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


def luneburg_index(radial_distance: float, lens_radius: float) -> float:
    """Return ``sqrt(2-(r/R)^2)`` inside the lens and one outside."""

    radial_distance = float(radial_distance)
    lens_radius = _positive(lens_radius, "lens_radius")
    if not math.isfinite(radial_distance) or radial_distance < 0:
        raise ValueError("radial_distance must be finite and non-negative")
    if radial_distance > lens_radius:
        return 1.0
    return math.sqrt(2.0 - (radial_distance / lens_radius) ** 2)


def n_and_grad(
    position_km: np.ndarray,
    params: LensFieldParams,
) -> tuple[float, np.ndarray]:
    """Return the exact v2 lens index and Cartesian gradient."""

    params.validate()
    position = np.asarray(position_km, dtype=float)
    if position.shape != (3,) or not np.all(np.isfinite(position)):
        raise ValueError("position_km must be a finite three-vector")
    relative = position - np.asarray(params.centre_km, dtype=float)
    radius = float(np.linalg.norm(relative))
    scale = params.radius_km

    if params.family == "maxwell":
        denominator = 1.0 + (radius / scale) ** 2
        base_index = 2.0 * params.n0 / denominator
        epsilon = params.dipole_epsilon
        if epsilon == 0.0:
            gradient = -4.0 * params.n0 * relative / (
                scale**2 * denominator**2
            )
            return base_index, gradient
        relative_z = float(relative[2])
        radius_squared = float(np.dot(relative, relative))
        exponent = epsilon * (relative_z / scale) * (
            1.0 - radius_squared / scale**2
        )
        index = base_index * math.exp(exponent)
        gradient_log_base = -2.0 * relative / (scale**2 * denominator)
        axis = np.array([0.0, 0.0, 1.0])
        gradient_exponent = epsilon * (
            axis / scale * (1.0 - radius_squared / scale**2)
            - 2.0 * relative_z * relative / scale**3
        )
        gradient = index * (gradient_log_base + gradient_exponent)
        return index, gradient

    if radius > scale:
        return 1.0, np.zeros(3)
    index = math.sqrt(2.0 - (radius / scale) ** 2)
    gradient = -relative / (scale**2 * index)
    return index, gradient


def n_and_grad_components(
    position_km: np.ndarray,
    params: LensFieldParams,
) -> tuple[float, np.ndarray, np.ndarray]:
    """Match the v1 interface as ``background + lens`` gradients."""

    index, lens_gradient = n_and_grad(position_km, params)
    return index, np.zeros(3), lens_gradient


def stereographic_to_sphere(
    point_xy: np.ndarray,
    sphere_radius: float = 1.0,
) -> np.ndarray:
    """Map the fish-eye plane to its native virtual sphere."""

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
    """Evaluate a great-circle ray on the fish eye's virtual sphere."""

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
    """Evaluate the exact interior Hamiltonian ray of a Luneburg sphere."""

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
