import { toRadians } from './math';
import type { GeoCoordinate, Vec3 } from './types';

export const EARTH_RADIUS_KM = 6_371;
export const AU_KM = 149_597_870.7;
export const SUN_RADIUS_KM = 695_700;

export interface TransformedSphere {
  centre: Vec3;
  radiusKm: number;
}

export function globePoint(
  coordinate: GeoCoordinate,
  altitudeKm = 0,
  radiusKm = EARTH_RADIUS_KM,
): Vec3 {
  const latitude = toRadians(coordinate.latitudeDeg);
  const longitude = toRadians(coordinate.longitudeDeg);
  const radius = radiusKm + altitudeKm;
  const cosLatitude = Math.cos(latitude);
  return {
    x: radius * cosLatitude * Math.cos(longitude),
    y: radius * cosLatitude * Math.sin(longitude),
    z: radius * Math.sin(latitude),
  };
}

export function conformalForward(point: Vec3, radiusKm = EARTH_RADIUS_KM): Vec3 {
  const relative = { x: point.x, y: point.y, z: point.z + radiusKm };
  const squaredDistance =
    relative.x ** 2 + relative.y ** 2 + relative.z ** 2;
  if (squaredDistance <= 0) {
    throw new Error('Południowy punkt inwersji przechodzi do nieskończoności.');
  }
  const factor = (4 * radiusKm ** 2) / squaredDistance;
  return {
    x: factor * relative.x,
    y: factor * relative.y,
    z: 2 * radiusKm - factor * relative.z,
  };
}

export function conformalInverse(point: Vec3, radiusKm = EARTH_RADIUS_KM): Vec3 {
  const reflected = { x: point.x, y: point.y, z: 2 * radiusKm - point.z };
  const squaredDistance =
    reflected.x ** 2 + reflected.y ** 2 + reflected.z ** 2;
  if (squaredDistance <= 0) {
    throw new Error('Ten punkt płaski reprezentuje nieskończoność.');
  }
  const factor = (4 * radiusKm ** 2) / squaredDistance;
  return {
    x: factor * reflected.x,
    y: factor * reflected.y,
    z: -radiusKm + factor * reflected.z,
  };
}

export function transformSphereConformal(
  centre: Vec3,
  objectRadiusKm: number,
  radiusKm = EARTH_RADIUS_KM,
): TransformedSphere {
  if (objectRadiusKm <= 0) throw new Error('Promień obiektu musi być dodatni.');
  const relative = { x: centre.x, y: centre.y, z: centre.z + radiusKm };
  const denominator =
    relative.x ** 2 + relative.y ** 2 + relative.z ** 2 - objectRadiusKm ** 2;
  if (Math.abs(denominator) <= Number.EPSILON) {
    throw new Error('Kula przechodząca przez centrum inwersji mapuje się na płaszczyznę.');
  }
  const factor = (4 * radiusKm ** 2) / denominator;
  return {
    centre: {
      x: factor * relative.x,
      y: factor * relative.y,
      z: 2 * radiusKm - factor * relative.z,
    },
    radiusKm: Math.abs(factor * objectRadiusKm),
  };
}

export function scalarIndexFlat(point: Vec3, radiusKm = EARTH_RADIUS_KM): number {
  const denominator = point.x ** 2 + point.y ** 2 + (2 * radiusKm - point.z) ** 2;
  return denominator === 0 ? Number.POSITIVE_INFINITY : (4 * radiusKm ** 2) / denominator;
}

export function projectStereographicSurface(
  coordinate: GeoCoordinate,
  radiusKm = EARTH_RADIUS_KM,
): Vec3 {
  return conformalForward(globePoint(coordinate, 0, radiusKm), radiusKm);
}

export function conformalToScene(point: Vec3): Vec3 {
  // Match the existing map convention: longitude 0° points towards the top
  // and positive/east longitudes run clockwise in the top camera view.
  return { x: point.y, y: point.z, z: -point.x };
}

export function stereographicRadiusForLatitude(
  latitudeDeg: number,
  radiusKm = EARTH_RADIUS_KM,
): number {
  const colatitude = toRadians(90 - latitudeDeg);
  return 2 * radiusKm * Math.tan(colatitude / 2);
}
