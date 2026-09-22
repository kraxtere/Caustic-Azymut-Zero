import { describe, expect, it } from 'vitest';
import { celestialObjectState, planetTrajectoryFrame } from './celestial';
import { computeModel } from './compute';
import { DEFAULT_MODEL_STATE } from './types';

describe('celestial catalogue and transformed path', () => {
  const utc = new Date('2026-09-16T12:00:00Z');

  it('produces finite, distinct coordinates for all three trajectory views', () => {
    const frame = planetTrajectoryFrame('mars', utc);
    for (const point of [frame.heliocentricAu, frame.geocentricAu, frame.invertedOffsetKm]) {
      expect(Number.isFinite(point.x)).toBe(true);
      expect(Number.isFinite(point.y)).toBe(true);
      expect(Number.isFinite(point.z)).toBe(true);
    }
    expect(Math.hypot(frame.heliocentricAu.x-frame.geocentricAu.x, frame.heliocentricAu.y-frame.geocentricAu.y)).toBeGreaterThan(0.1);
    expect(Math.hypot(frame.invertedOffsetKm.x,frame.invertedOffsetKm.y,frame.invertedOffsetKm.z)).toBeGreaterThan(0);
  });

  it('keeps the Moon on a finite measured-distance shell', () => {
    const moon = celestialObjectState('moon', utc);
    expect(moon.distanceKm).toBeGreaterThan(350_000);
    expect(moon.distanceKm).toBeLessThan(410_000);
    expect(moon.angularRadiusDeg).toBeGreaterThan(0.23);
    expect(moon.angularRadiusDeg).toBeLessThan(0.29);
  });

  it('uses catalogue parallax distances for fixed stars', () => {
    const sirius = celestialObjectState('sirius', utc);
    const polaris = celestialObjectState('polaris', utc);
    expect(sirius.distanceKm).toBeGreaterThan(8 * 9.46e12);
    expect(polaris.distanceKm).toBeGreaterThan(sirius.distanceKm);
  });

  it('computes finite geocentric states for every planet', () => {
    const ids = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'] as const;
    for (const id of ids) {
      const planet = celestialObjectState(id, utc);
      expect(planet.kind).toBe('planet');
      expect(Number.isFinite(planet.raDeg)).toBe(true);
      expect(planet.declinationDeg).toBeGreaterThanOrEqual(-90);
      expect(planet.declinationDeg).toBeLessThanOrEqual(90);
      expect(planet.distanceKm).toBeGreaterThan(30_000_000);
    }
  });

  it('returns all enabled objects while tracing only the selected path', () => {
    const state = structuredClone(DEFAULT_MODEL_STATE);
    state.selectedObject = 'mars';
    state.visibleObjectIds = ['sun', 'moon', 'mars', 'jupiter'];
    const computed = computeModel(state);
    expect(computed.conformalObjects).toHaveLength(4);
    expect(computed.conformalObjects?.find((object) => object.id === 'mars')?.transformedPath.length)
      .toBeGreaterThan(200);
    expect(computed.conformalObjects?.find((object) => object.id === 'jupiter')?.transformedPath)
      .toHaveLength(0);
  });

  it('maps one source-observer segment without a fitted ray solver', () => {
    const state = structuredClone(DEFAULT_MODEL_STATE);
    state.selectedObject = 'moon';
    const computed = computeModel(state);
    expect(computed.conformalObject?.transformedPath.length).toBeGreaterThan(200);
    const last = computed.conformalObject!.transformedPath.at(-1)!;
    expect(last.x).toBeCloseTo(computed.observerPoint.x, 6);
    expect(last.y).toBeCloseTo(computed.observerPoint.y, 6);
    expect(last.z).toBeCloseTo(computed.observerPoint.z, 6);
  });
});
