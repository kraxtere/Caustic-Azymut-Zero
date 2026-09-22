import { normalizeAzimuth, normalizeDegrees, toDegrees, toRadians } from './math';
import type { Vec3 } from './types';

export interface SolarEphemeris {
  utc: Date;
  raDeg: number;
  declinationDeg: number;
  distanceAu: number;
  angularRadiusDeg: number;
  gmstDeg: number;
  earthFixedLongitudeDeg: number;
  earthFixedDirection: Vec3;
}

export function julianDay(date: Date): number {
  return date.getTime() / 86_400_000 + 2_440_587.5;
}

export function gmstDegrees(date: Date): number {
  const jd = julianDay(date);
  const centuries = (jd - 2_451_545) / 36_525;
  return normalizeAzimuth(
    280.46061837 +
      360.98564736629 * (jd - 2_451_545) +
      0.000387933 * centuries ** 2 -
      centuries ** 3 / 38_710_000,
  );
}

export function solarEphemeris(date: Date): SolarEphemeris {
  if (!Number.isFinite(date.getTime())) throw new Error('Nieprawidłowa data UTC.');
  const jd = julianDay(date);
  const centuries = (jd - 2_451_545) / 36_525;
  const meanLongitude =
    280.46646 + 36_000.76983 * centuries + 0.0003032 * centuries ** 2;
  const meanAnomaly =
    357.52911 + 35_999.05029 * centuries - 0.0001537 * centuries ** 2;
  const anomaly = toRadians(normalizeAzimuth(meanAnomaly));
  const equationOfCentre =
    (1.914602 - 0.004817 * centuries - 0.000014 * centuries ** 2) * Math.sin(anomaly) +
    (0.019993 - 0.000101 * centuries) * Math.sin(2 * anomaly) +
    0.000289 * Math.sin(3 * anomaly);
  const trueAnomaly = normalizeAzimuth(meanAnomaly + equationOfCentre);
  const eccentricity =
    0.016708634 - 0.000042037 * centuries - 0.0000001267 * centuries ** 2;
  const distanceAu =
    (1.000001018 * (1 - eccentricity ** 2)) /
    (1 + eccentricity * Math.cos(toRadians(trueAnomaly)));

  const trueLongitude = normalizeAzimuth(meanLongitude + equationOfCentre);
  const omega = 125.04 - 1934.136 * centuries;
  const apparentLongitude =
    trueLongitude - 0.00569 - 0.00478 * Math.sin(toRadians(omega));
  const meanObliquity =
    23 +
    26 / 60 +
    21.448 / 3600 -
    (46.815 * centuries + 0.00059 * centuries ** 2 - 0.001813 * centuries ** 3) /
      3600;
  const obliquity = meanObliquity + 0.00256 * Math.cos(toRadians(omega));
  const longitude = toRadians(apparentLongitude);
  const obliquityRad = toRadians(obliquity);
  const raDeg = normalizeAzimuth(
    toDegrees(
      Math.atan2(
        Math.cos(obliquityRad) * Math.sin(longitude),
        Math.cos(longitude),
      ),
    ),
  );
  const declinationDeg = toDegrees(
    Math.asin(Math.sin(obliquityRad) * Math.sin(longitude)),
  );
  const gmstDeg = gmstDegrees(date);
  const earthFixedLongitudeDeg = normalizeDegrees(raDeg - gmstDeg);
  const declination = toRadians(declinationDeg);
  const earthLongitude = toRadians(earthFixedLongitudeDeg);
  const earthFixedDirection = {
    x: Math.cos(declination) * Math.cos(earthLongitude),
    y: Math.cos(declination) * Math.sin(earthLongitude),
    z: Math.sin(declination),
  };
  const angularRadiusDeg = toDegrees(
    Math.asin(Math.sin(toRadians(0.2666)) / distanceAu),
  );
  return {
    utc: date,
    raDeg,
    declinationDeg,
    distanceAu,
    angularRadiusDeg,
    gmstDeg,
    earthFixedLongitudeDeg,
    earthFixedDirection,
  };
}

export function parseUtcMinute(value: string): Date {
  const normalized = value.endsWith('Z') ? value : `${value}:00Z`;
  return new Date(normalized);
}

