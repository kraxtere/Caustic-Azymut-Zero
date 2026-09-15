import { describe, expect, it } from 'vitest';
import { projectAzimuthal, unprojectAzimuthal } from '../src/model/azimuthal';
import { sampleBaselineRay } from '../src/model/baselineRay';
import { computeModel } from '../src/model/compute';
import { pointOnDome } from '../src/model/dome';
import { equatorialToHorizontal } from '../src/model/horizontal';
import { DEFAULT_MODEL_STATE } from '../src/model/types';

describe('azimuthal equidistant projection', () => {
  it('places the north pole at the origin', () => {
    expect(
      projectAzimuthal({ latitudeDeg: 90, longitudeDeg: 123 }, 20_015),
    ).toEqual({ x: 0, y: 0, z: 0 });
  });

  it('places the equator at half of the map radius', () => {
    const point = projectAzimuthal(
      { latitudeDeg: 0, longitudeDeg: 90 },
      20_000,
    );
    expect(point.x).toBeCloseTo(10_000, 8);
    expect(point.z).toBeCloseTo(0, 8);
  });

  it('round-trips a geographic coordinate', () => {
    const original = { latitudeDeg: 50.6751, longitudeDeg: 17.9213 };
    const restored = unprojectAzimuthal(
      projectAzimuthal(original, 20_015),
      20_015,
    );
    expect(restored.latitudeDeg).toBeCloseTo(original.latitudeDeg, 10);
    expect(restored.longitudeDeg).toBeCloseTo(original.longitudeDeg, 10);
  });
});

describe('horizontal coordinates', () => {
  it('puts a source at the zenith when declination equals latitude on transit', () => {
    const result = equatorialToHorizontal(50, 50, 0);
    expect(result.elevationDeg).toBeCloseTo(90, 8);
  });

  it('puts an equatorial source on the eastern horizon at hour angle -90°', () => {
    const result = equatorialToHorizontal(0, 0, -90);
    expect(result.azimuthDeg).toBeCloseTo(90, 8);
    expect(result.elevationDeg).toBeCloseTo(0, 8);
  });
});

describe('dome geometry', () => {
  const parameters = {
    mapRadiusKm: 20_015,
    domeHeightKm: 9_000,
    domeRadiusScale: 1,
  };

  it('places the north celestial pole at the top', () => {
    const point = pointOnDome(90, 0, parameters);
    expect(point.x).toBeCloseTo(0, 10);
    expect(point.z).toBeCloseTo(0, 10);
    expect(point.y).toBeCloseTo(9_000, 10);
  });

  it('places the south celestial pole on the rim for a unit dome', () => {
    const point = pointOnDome(-90, 0, parameters);
    expect(Math.hypot(point.x, point.z)).toBeCloseTo(20_015, 8);
    expect(point.y).toBeCloseTo(0, 8);
  });
});

describe('FE-Dome baseline ray', () => {
  it('preserves the requested endpoints', () => {
    const start = { x: 0, y: 0, z: 0 };
    const end = { x: 10, y: 5, z: -2 };
    const ray = sampleBaselineRay({
      observerPoint: start,
      sourcePoint: end,
      initialDirection: { x: 1, y: 1, z: 0 },
      rayParameter: 1,
      sampleCount: 20,
    });
    expect(ray.points[0]).toEqual(start);
    expect(ray.points.at(-1)).toEqual(end);
    expect(ray.points).toHaveLength(20);
  });
});

describe('composed model', () => {
  it('produces finite coordinates for the default state', () => {
    const result = computeModel(structuredClone(DEFAULT_MODEL_STATE));
    const values = [
      ...Object.values(result.observerPoint),
      ...Object.values(result.sourcePoint),
      result.horizontal.azimuthDeg,
      result.horizontal.elevationDeg,
    ];
    expect(values.every(Number.isFinite)).toBe(true);
    expect(result.baselineRay.points.length).toBeGreaterThan(10);
  });
});
