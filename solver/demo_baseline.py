"""Baseline triangulation of the Sun with straight rays on the AE plane."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from .ephemeris import MeeusLowPrecision
from .field import FieldParams
from .geometry_flat import altaz_of_radec, observer_xy, sky_direction_3d
from .raytrace import IntegrationOptions, trace_ray, triangulate_detailed


OBSERVERS = [
    (30.0, 0.0),
    (45.0, 20.0),
    (50.0, -30.0),
    (10.0, 60.0),
    (-10.0, 10.0),
]
INSTANT = datetime(2026, 6, 21, 15, 0, tzinfo=timezone.utc)


def run_baseline() -> tuple[np.ndarray, float]:
    ephemeris = MeeusLowPrecision()
    radec = ephemeris.sun_radec(INSTANT)
    no_field = FieldParams(k=0, H=8, A=0, rho0=5000, s=1000)
    options = IntegrationOptions()

    points: list[np.ndarray] = []
    directions: list[np.ndarray] = []
    print(
        f"Slonce {INSTANT.isoformat()}: "
        f"RA={radec.ra_deg:.2f} dec={radec.dec_deg:.2f}\n"
    )
    for latitude, longitude in OBSERVERS:
        altitude, azimuth = altaz_of_radec(
            radec,
            latitude,
            longitude,
            INSTANT,
        )
        if altitude < 0:
            print(
                f"  ({latitude:+.0f},{longitude:+.0f}): "
                "Slonce pod horyzontem, pomijam"
            )
            continue
        origin = observer_xy(latitude, longitude)
        direction = sky_direction_3d(
            altitude,
            azimuth,
            latitude,
            longitude,
        )
        ray = trace_ray(origin, direction, no_field, options)
        points.append(ray.point)
        directions.append(ray.direction)
        print(
            f"  obserwator ({latitude:+.0f}N,{longitude:+.0f}E)  "
            f"alt={altitude:6.2f} az={azimuth:6.2f}"
        )

    fit = triangulate_detailed(points, directions)
    print()
    print(f"Triangulowana pozycja Slonca: {np.round(fit.point, 0)} km")
    print(f"Wysokosc nad plaszczyzna (Z): {fit.point[2]:.0f} km")
    print(f"RMS rozrzutu: {fit.rms_km:.0f} km")
    return fit.point, fit.rms_km


if __name__ == "__main__":
    run_baseline()
