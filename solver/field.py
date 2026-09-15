"""Axisymmetric refractive-index field used by the first fit family.

The five fitted parameters define a vertically stratified background and a
Gaussian toroidal ring::

    n(rho, z) = 1 + k exp(-z/H)
                  + A exp(-((rho-rho0)^2 + z^2)/(2 s^2))

The model domain is z >= 0.  Rays which return below the map plane are rejected
by the tracer.  The ring gradient is analytic; no finite differencing is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FieldParams:
    k: float = 0.0003
    H: float = 8.0
    A: float = 0.0
    rho0: float = 5000.0
    s: float = 1500.0

    def validate(self) -> None:
        if self.H <= 0:
            raise ValueError("H must be positive")
        if self.s <= 0:
            raise ValueError("s must be positive")
        if self.rho0 < 0:
            raise ValueError("rho0 cannot be negative")
        # With k >= 0, the smallest possible index is bounded by 1 + A.
        if self.k < 0:
            raise ValueError("k cannot be negative in this field family")
        if 1.0 + self.A <= 0.05:
            raise ValueError("A makes the refractive index non-positive")


def n_and_grad(pos: np.ndarray, params: FieldParams) -> tuple[float, np.ndarray]:
    """Return refractive index and Cartesian gradient at ``pos``."""

    x, y, z = (float(value) for value in pos)
    rho = math.hypot(x, y)

    # The atmosphere is only defined above the map.  Extending it as a constant
    # for the tiny below-ground trial steps used by an event detector prevents
    # exponential overflow without changing any accepted ray.
    atmospheric_z = max(z, 0.0)
    background = params.k * math.exp(-atmospheric_z / params.H)
    background_dz = (
        -params.k / params.H * math.exp(-z / params.H) if z >= 0 else 0.0
    )

    radial_offset = rho - params.rho0
    exponent = -(
        radial_offset**2 + z**2
    ) / (2 * params.s**2)
    ring = params.A * math.exp(max(exponent, -745.0))
    ring_drho = ring * (-radial_offset / params.s**2)
    ring_dz = ring * (-z / params.s**2)

    if rho > 1e-12:
        radial_x, radial_y = x / rho, y / rho
    else:
        radial_x = radial_y = 0.0

    refractive_index = 1.0 + background + ring
    gradient = np.array(
        [
            ring_drho * radial_x,
            ring_drho * radial_y,
            background_dz + ring_dz,
        ],
        dtype=float,
    )
    return refractive_index, gradient


if __name__ == "__main__":
    parameters = FieldParams(A=0.002, rho0=5000.0, s=1000.0)
    for test_rho in [0, 3000, 5000, 7000, 15000]:
        n_value, gradient = n_and_grad(
            np.array([test_rho, 0.0, 0.1]),
            parameters,
        )
        print(
            f"rho={test_rho:6.0f} km   n={n_value:.6f}   "
            f"|grad n|={np.linalg.norm(gradient):.3e}"
        )
