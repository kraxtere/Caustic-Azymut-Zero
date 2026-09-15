"""Geometry of the north-pole-centred azimuthal equidistant plane.

Solver coordinates use ``x, y`` in the map plane and ``z`` as altitude.  The
viewer intentionally uses another axis ordering (Y-up), so exported solver
data must carry this convention explicitly.
"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np

from .ephemeris import RaDec, gmst_deg


# Radial map scale in kilometres per radian.  Consequently the south-pole
# rim is pi * R_MAP ~= 20,015 km from the north-pole centre.
R_MAP = 6371.0


def observer_xy(lat_deg: float, lon_deg: float, radius: float = R_MAP) -> np.ndarray:
    """Map an observer to ``[x, y, 0]`` on the AE plane."""

    latitude = math.radians(lat_deg)
    longitude = math.radians(lon_deg)
    rho = radius * (math.pi / 2 - latitude)
    return np.array(
        [rho * math.cos(longitude), rho * math.sin(longitude), 0.0],
        dtype=float,
    )


def local_frame(
    lat_deg: float,
    lon_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return local East, North and Up unit vectors in solver coordinates."""

    del lat_deg  # The AE radial north direction depends only on longitude.
    longitude = math.radians(lon_deg)
    east = np.array([-math.sin(longitude), math.cos(longitude), 0.0])
    north = np.array([-math.cos(longitude), -math.sin(longitude), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    return east, north, up


def altaz_of_radec(
    radec: RaDec,
    lat_deg: float,
    lon_deg: float,
    dt: datetime,
) -> tuple[float, float]:
    """Convert equatorial coordinates to altitude and navigation azimuth."""

    local_sidereal_time = (gmst_deg(dt) + lon_deg) % 360
    hour_angle = math.radians((local_sidereal_time - radec.ra_deg) % 360)
    latitude = math.radians(lat_deg)
    declination = math.radians(radec.dec_deg)

    sin_altitude = (
        math.sin(declination) * math.sin(latitude)
        + math.cos(declination) * math.cos(latitude) * math.cos(hour_angle)
    )
    altitude = math.asin(max(-1.0, min(1.0, sin_altitude)))
    azimuth = math.atan2(
        -math.sin(hour_angle) * math.cos(declination),
        math.cos(latitude) * math.sin(declination)
        - math.sin(latitude) * math.cos(declination) * math.cos(hour_angle),
    )
    return math.degrees(altitude), math.degrees(azimuth) % 360


def sky_direction_3d(
    alt_deg: float,
    az_deg: float,
    lat_deg: float,
    lon_deg: float,
) -> np.ndarray:
    """Return the outward unit direction corresponding to measured alt/az."""

    east, north, up = local_frame(lat_deg, lon_deg)
    altitude = math.radians(alt_deg)
    azimuth = math.radians(az_deg)
    direction = (
        math.cos(altitude) * math.sin(azimuth) * east
        + math.cos(altitude) * math.cos(azimuth) * north
        + math.sin(altitude) * up
    )
    return direction / np.linalg.norm(direction)


if __name__ == "__main__":
    from datetime import timezone

    from .ephemeris import MeeusLowPrecision

    instant = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    radec = MeeusLowPrecision().sun_radec(instant)
    solar_noon_lon = (radec.ra_deg - gmst_deg(instant)) % 360
    if solar_noon_lon > 180:
        solar_noon_lon -= 360
    altitude, _ = altaz_of_radec(radec, 0.0, solar_noon_lon, instant)
    altitude_52, _ = altaz_of_radec(radec, 52.0, solar_noon_lon, instant)
    print(f"Rownik, poludnie sloneczne: alt={altitude:.3f} deg")
    print(f"52 N, ta sama chwila: alt={altitude_52:.3f} deg")
