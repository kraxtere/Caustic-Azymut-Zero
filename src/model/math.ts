import type { Vec3 } from './types';

export const DEGREES_TO_RADIANS = Math.PI / 180;
export const RADIANS_TO_DEGREES = 180 / Math.PI;

export function toRadians(degrees: number): number {
  return degrees * DEGREES_TO_RADIANS;
}

export function toDegrees(radians: number): number {
  return radians * RADIANS_TO_DEGREES;
}

export function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

export function normalizeDegrees(degrees: number): number {
  const normalized = ((degrees + 180) % 360 + 360) % 360 - 180;
  return Object.is(normalized, -0) ? 0 : normalized;
}

export function normalizeAzimuth(degrees: number): number {
  const normalized = ((degrees % 360) + 360) % 360;
  return Object.is(normalized, -0) ? 0 : normalized;
}

export function add(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function subtract(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

export function scale(vector: Vec3, factor: number): Vec3 {
  return { x: vector.x * factor, y: vector.y * factor, z: vector.z * factor };
}

export function length(vector: Vec3): number {
  return Math.hypot(vector.x, vector.y, vector.z);
}

export function distance(a: Vec3, b: Vec3): number {
  return length(subtract(a, b));
}

export function normalize(vector: Vec3): Vec3 {
  const magnitude = length(vector);
  if (magnitude === 0) {
    throw new Error('Nie można znormalizować wektora zerowego.');
  }
  return scale(vector, 1 / magnitude);
}

export function cubicBezierPoint(
  start: Vec3,
  control1: Vec3,
  control2: Vec3,
  end: Vec3,
  t: number,
): Vec3 {
  const u = 1 - t;
  const w0 = u * u * u;
  const w1 = 3 * u * u * t;
  const w2 = 3 * u * t * t;
  const w3 = t * t * t;

  return {
    x: w0 * start.x + w1 * control1.x + w2 * control2.x + w3 * end.x,
    y: w0 * start.y + w1 * control1.y + w2 * control2.y + w3 * end.y,
    z: w0 * start.z + w1 * control1.z + w2 * control2.z + w3 * end.z,
  };
}
