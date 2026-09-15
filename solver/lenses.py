"""Compatibility imports for the lens family moved to :mod:`field_lens`.

New code should import :mod:`solver.field_lens` directly. This module remains
so links and imports created during the former v1.5 stage keep working.
"""

from .field_lens import (
    LensFieldParams,
    LuneburgRayState,
    luneburg_index,
    luneburg_ray_state,
    luneburg_surface_focus,
    maxwell_fisheye_index,
    maxwell_mirror_image,
    maxwell_spherical_ray,
    n_and_grad,
    n_and_grad_components,
    stereographic_from_sphere,
    stereographic_to_sphere,
)

__all__ = [
    "LensFieldParams",
    "LuneburgRayState",
    "luneburg_index",
    "luneburg_ray_state",
    "luneburg_surface_focus",
    "maxwell_fisheye_index",
    "maxwell_mirror_image",
    "maxwell_spherical_ray",
    "n_and_grad",
    "n_and_grad_components",
    "stereographic_from_sphere",
    "stereographic_to_sphere",
]
