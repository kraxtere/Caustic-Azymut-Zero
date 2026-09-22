import { describe, expect, it } from 'vitest';
import {
  createExponentialAtmosphere,
  findFlatRayConnections,
  terminalHeightKm,
  traceFlatAtmosphereRay,
  VACUUM_ATMOSPHERE,
} from '../src/model/flatAtmosphere';

describe('flat stratified atmosphere', () => {
  it('preserves a horizontal straight ray in a uniform medium', () => {
    const result = traceFlatAtmosphereRay({
      observerHeightKm: 0.0005,
      apparentElevationDeg: 0,
      maximumHorizontalKm: 7.1,
      atmosphere: VACUUM_ATMOSPHERE,
      stepKm: 0.01,
    });

    expect(result.termination).toBe('range');
    expect(terminalHeightKm(result)).toBeCloseTo(0.0005, 10);
    expect(result.finalElevationDeg).toBeCloseTo(0, 10);
  });

  it('bends an eye-level ray toward a denser near-surface layer', () => {
    const atmosphere = createExponentialAtmosphere({
      surfaceRefractivity: 0.0003,
      refractivityScaleHeightKm: 3,
    });
    const low = traceFlatAtmosphereRay({
      observerHeightKm: 0.0005,
      apparentElevationDeg: 0,
      maximumHorizontalKm: 7.1,
      atmosphere,
      stepKm: 0.002,
    });
    const raised = traceFlatAtmosphereRay({
      observerHeightKm: 0.002,
      apparentElevationDeg: 0,
      maximumHorizontalKm: 7.1,
      atmosphere,
      stepKm: 0.002,
    });

    expect(low.termination).toBe('surface');
    expect(raised.termination).toBe('surface');
    expect(raised.points.at(-1)!.horizontalKm).toBeGreaterThan(
      low.points.at(-1)!.horizontalKm,
    );
  });

  it('uses the same profile for direction change and transmission', () => {
    const atmosphere = createExponentialAtmosphere({
      surfaceRefractivity: 0.0003,
      refractivityScaleHeightKm: 3,
      surfaceExtinctionPerKm: 0.08,
      extinctionScaleHeightKm: 0.2,
    });
    const short = traceFlatAtmosphereRay({
      observerHeightKm: 0.05,
      apparentElevationDeg: 0.2,
      maximumHorizontalKm: 1,
      atmosphere,
      stepKm: 0.002,
    });
    const long = traceFlatAtmosphereRay({
      observerHeightKm: 0.05,
      apparentElevationDeg: 0.2,
      maximumHorizontalKm: 5,
      atmosphere,
      stepKm: 0.002,
    });

    expect(short.termination).toBe('range');
    expect(long.termination).toBe('range');
    expect(long.opticalDepth).toBeGreaterThan(short.opticalDepth);
    expect(long.points.at(-1)!.intensity).toBeLessThan(
      short.points.at(-1)!.intensity,
    );
    expect(long.finalElevationDeg).toBeLessThan(short.finalElevationDeg);
  });

  it('is numerically stable when the integration step is halved', () => {
    const atmosphere = createExponentialAtmosphere({
      surfaceRefractivity: 0.00025,
      refractivityScaleHeightKm: 5,
    });
    const trace = (stepKm: number) =>
      traceFlatAtmosphereRay({
        observerHeightKm: 0.1,
        apparentElevationDeg: 0.5,
        maximumHorizontalKm: 20,
        atmosphere,
        stepKm,
      });

    const coarse = trace(0.01);
    const fine = trace(0.005);
    expect(coarse.termination).toBe(fine.termination);
    expect(terminalHeightKm(coarse)).toBeCloseTo(terminalHeightKm(fine), 7);
    expect(coarse.finalElevationDeg).toBeCloseTo(fine.finalElevationDeg, 7);
  });

  it('connects finite object points and preserves optical reciprocity', () => {
    const atmosphere = createExponentialAtmosphere({
      surfaceRefractivity: 0.0003,
      refractivityScaleHeightKm: 3,
    });
    const connections = findFlatRayConnections({
      observerHeightKm: 0.0005,
      targetHorizontalKm: 7.1,
      targetHeightKm: 0.05,
      atmosphere,
      minimumElevationDeg: -0.5,
      maximumElevationDeg: 2,
      scanStepDeg: 0.05,
    });

    expect(connections.length).toBeGreaterThan(0);
    const connection = connections[0]!;
    expect(connection.ray.termination).toBe('range');
    expect(terminalHeightKm(connection.ray)).toBeCloseTo(0.05, 6);
    expect(Math.abs(connection.heightResidualKm)).toBeLessThan(1e-6);
  });
});
