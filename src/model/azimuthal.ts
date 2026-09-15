import { clamp, normalizeDegrees, toDegrees, toRadians } from './math';
import type { GeoCoordinate, Vec3 } from './types';

/**
 * North-pole-centred azimuthal equidistant projection.
 *
 * Longitude 0° points towards the top of the map in the top camera view.
 * Positive/east longitudes run clockwise.
 */
export function projectAzimuthal(
  coordinate: GeoCoordinate,
  mapRadiusKm: number,
): Vec3 {
  if (mapRadiusKm <= 0) {
    throw new Error('Promień mapy musi być dodatni.');
  }

  const latitudeDeg = clamp(coordinate.latitudeDeg, -90, 90);
  const longitudeRad = toRadians(normalizeDegrees(coordinate.longitudeDeg));
  const radialDistance = ((90 - latitudeDeg) / 180) * mapRadiusKm;

  return {
    x: radialDistance * Math.sin(longitudeRad),
    y: 0,
    z: -radialDistance * Math.cos(longitudeRad),
  };
}

export function unprojectAzimuthal(point: Vec3, mapRadiusKm: number): GeoCoordinate {
  if (mapRadiusKm <= 0) {
    throw new Error('Promień mapy musi być dodatni.');
  }

  const radialDistance = Math.hypot(point.x, point.z);
  const latitudeDeg = 90 - (radialDistance / mapRadiusKm) * 180;
  const longitudeDeg = normalizeDegrees(toDegrees(Math.atan2(point.x, -point.z)));

  return {
    latitudeDeg,
    longitudeDeg,
  };
}
