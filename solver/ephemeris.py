"""Low-precision solar ephemeris with a replaceable provider interface.

The implementation follows the compact solar-position formulae from
Jean Meeus, *Astronomical Algorithms*, chapter 25.  Its intended accuracy is
about 0.01 degree.  The rest of the solver depends on :class:`Ephemeris`, so a
JPL DE/Skyfield provider can be added without changing the geometry or fit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def julian_day(dt: datetime) -> float:
    """Return the Julian day for a UTC-aware or UTC-assumed datetime."""

    dt = _utc(dt)
    year, month = dt.year, dt.month
    seconds = dt.second + dt.microsecond / 1_000_000
    day = dt.day + (dt.hour + dt.minute / 60 + seconds / 3600) / 24
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (
        int(365.25 * (year + 4716))
        + int(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


@dataclass(frozen=True)
class RaDec:
    ra_deg: float
    dec_deg: float


class Ephemeris:
    """Provider contract.  Replace ``sun_radec`` to change ephemeris source."""

    def sun_radec(self, dt: datetime) -> RaDec:
        raise NotImplementedError


class MeeusLowPrecision(Ephemeris):
    def sun_radec(self, dt: datetime) -> RaDec:
        jd = julian_day(dt)
        centuries = (jd - 2451545.0) / 36525.0

        mean_longitude = (
            280.46646
            + 36000.76983 * centuries
            + 0.0003032 * centuries**2
        )
        mean_anomaly = (
            357.52911
            + 35999.05029 * centuries
            - 0.0001537 * centuries**2
        )
        anomaly_rad = math.radians(mean_anomaly % 360)
        equation_of_center = (
            (1.914602 - 0.004817 * centuries - 0.000014 * centuries**2)
            * math.sin(anomaly_rad)
            + (0.019993 - 0.000101 * centuries) * math.sin(2 * anomaly_rad)
            + 0.000289 * math.sin(3 * anomaly_rad)
        )

        true_longitude = (mean_longitude + equation_of_center) % 360
        omega = 125.04 - 1934.136 * centuries
        apparent_longitude = (
            true_longitude
            - 0.00569
            - 0.00478 * math.sin(math.radians(omega))
        )

        mean_obliquity = (
            23
            + 26 / 60
            + 21.448 / 3600
            - (
                46.815 * centuries
                + 0.00059 * centuries**2
                - 0.001813 * centuries**3
            )
            / 3600
        )
        obliquity = mean_obliquity + 0.00256 * math.cos(math.radians(omega))

        longitude_rad = math.radians(apparent_longitude)
        obliquity_rad = math.radians(obliquity)
        ra_deg = math.degrees(
            math.atan2(
                math.cos(obliquity_rad) * math.sin(longitude_rad),
                math.cos(longitude_rad),
            )
        ) % 360
        dec_deg = math.degrees(
            math.asin(math.sin(obliquity_rad) * math.sin(longitude_rad))
        )
        return RaDec(ra_deg=ra_deg, dec_deg=dec_deg)


def gmst_deg(dt: datetime) -> float:
    """Greenwich mean sidereal time in degrees."""

    jd = julian_day(dt)
    centuries = (jd - 2451545.0) / 36525.0
    return (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * centuries**2
        - centuries**3 / 38710000.0
    ) % 360


if __name__ == "__main__":
    instant = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    position = MeeusLowPrecision().sun_radec(instant)
    print(
        "Rownonoc marcowa 2026, 12:00 UTC -> "
        f"RA={position.ra_deg:.3f} deg  dec={position.dec_deg:.3f} deg"
    )
