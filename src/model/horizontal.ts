import {
  clamp,
  normalize,
  normalizeAzimuth,
  toDegrees,
  toRadians,
} from './math';
import type { HorizontalAngles, Vec3 } from './types';

/**
 * Converts declination and local hour angle to horizontal coordinates.
 * Positive hour angle means that the source is west of the meridian.
 */
export function equatorialToHorizontal(
  observerLatitudeDeg: number,
  declinationDeg: number,
  hourAngleDeg: number,
): HorizontalAngles {
  const latitude = toRadians(clamp(observerLatitudeDeg, -90, 90));
  const declination = toRadians(clamp(declinationDeg, -90, 90));
  const hourAngle = toRadians(hourAngleDeg);

  const east = -Math.cos(declination) * Math.sin(hourAngle);
  const north =
    Math.cos(latitude) * Math.sin(declination) -
    Math.sin(latitude) * Math.cos(declination) * Math.cos(hourAngle);
  const up =
    Math.sin(latitude) * Math.sin(declination) +
    Math.cos(latitude) * Math.cos(declination) * Math.cos(hourAngle);

  return {
    azimuthDeg: normalizeAzimuth(toDegrees(Math.atan2(east, north))),
    elevationDeg: toDegrees(Math.asin(clamp(up, -1, 1))),
  };
}

/**
 * Expresses a local azimuth/elevation direction in the global map frame.
 */
export function horizontalDirectionOnMap(
  observerLongitudeDeg: number,
  horizontal: HorizontalAngles,
): Vec3 {
  const longitude = toRadians(observerLongitudeDeg);
  const azimuth = toRadians(horizontal.azimuthDeg);
  const elevation = toRadians(horizontal.elevationDeg);

  const north: Vec3 = {
    x: -Math.sin(longitude),
    y: 0,
    z: Math.cos(longitude),
  };
  const east: Vec3 = {
    x: Math.cos(longitude),
    y: 0,
    z: Math.sin(longitude),
  };

  const horizontalMagnitude = Math.cos(elevation);
  return normalize({
    x:
      north.x * horizontalMagnitude * Math.cos(azimuth) +
      east.x * horizontalMagnitude * Math.sin(azimuth),
    y: Math.sin(elevation),
    z:
      north.z * horizontalMagnitude * Math.cos(azimuth) +
      east.z * horizontalMagnitude * Math.sin(azimuth),
  });
}
