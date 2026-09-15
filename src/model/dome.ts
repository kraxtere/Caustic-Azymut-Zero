import { clamp, normalizeDegrees, toRadians } from './math';
import type { Vec3 } from './types';

export interface DomeParameters {
  mapRadiusKm: number;
  domeHeightKm: number;
  domeRadiusScale: number;
}

/**
 * Maps celestial latitude/longitude onto the upper half of an ellipsoid.
 * This is the same geometric construction used by the FE-Dome baseline.
 */
export function pointOnDome(
  celestialLatitudeDeg: number,
  earthFixedLongitudeDeg: number,
  parameters: DomeParameters,
): Vec3 {
  const { mapRadiusKm, domeHeightKm, domeRadiusScale } = parameters;
  if (mapRadiusKm <= 0 || domeHeightKm <= 0 || domeRadiusScale < 1) {
    throw new Error('Nieprawidłowe parametry kopuły.');
  }

  const latitudeDeg = clamp(celestialLatitudeDeg, -90, 90);
  const longitude = toRadians(normalizeDegrees(earthFixedLongitudeDeg));
  const radialDistance = ((90 - latitudeDeg) / 180) * mapRadiusKm;
  const domeRadius = domeRadiusScale * mapRadiusKm;
  const radialRatio = clamp(radialDistance / domeRadius, 0, 1);
  const height = Math.sqrt(1 - radialRatio * radialRatio) * domeHeightKm;

  return {
    x: radialDistance * Math.sin(longitude),
    y: height,
    z: -radialDistance * Math.cos(longitude),
  };
}
