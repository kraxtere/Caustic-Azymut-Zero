import { describe, expect, it } from 'vitest';
import {
  AU_KM,
  EARTH_RADIUS_KM,
  SUN_RADIUS_KM,
  conformalForward,
  conformalInverse,
  globePoint,
  stereographicRadiusForLatitude,
  transformSphereConformal,
} from './conformal';
import { solarEphemeris } from './solar';

describe('exact conformal inversion', () => {
  it('maps the spherical surface exactly to the plane', () => {
    for (const latitudeDeg of [-85, -45, 0, 45, 85]) {
      const mapped = conformalForward(
        globePoint({ latitudeDeg, longitudeDeg: 37 }),
      );
      expect(mapped.z).toBeCloseTo(0, 8);
    }
  });

  it('matches the stereographic surface law', () => {
    for (const latitudeDeg of [-75, -30, 0, 30, 75]) {
      const mapped = conformalForward(
        globePoint({ latitudeDeg, longitudeDeg: -20 }),
      );
      expect(Math.hypot(mapped.x, mapped.y)).toBeCloseTo(
        stereographicRadiusForLatitude(latitudeDeg),
        8,
      );
    }
  });

  it('round-trips full three-dimensional points', () => {
    const source = globePoint({ latitudeDeg: -42, longitudeDeg: 71 }, 300);
    const restored = conformalInverse(conformalForward(source));
    expect(restored.x).toBeCloseTo(source.x, 8);
    expect(restored.y).toBeCloseTo(source.y, 8);
    expect(restored.z).toBeCloseTo(source.z, 8);
  });

  it('maps the finite Sun to the expected metre-scale image', () => {
    const ephemeris = solarEphemeris(new Date('2026-09-16T12:00:00Z'));
    expect(ephemeris.declinationDeg).toBeCloseTo(2.5234279124, 8);
    expect(ephemeris.distanceAu).toBeCloseTo(1.0053945874, 9);
    const centre = {
      x: ephemeris.earthFixedDirection.x * ephemeris.distanceAu * AU_KM,
      y: ephemeris.earthFixedDirection.y * ephemeris.distanceAu * AU_KM,
      z: ephemeris.earthFixedDirection.z * ephemeris.distanceAu * AU_KM,
    };
    const image = transformSphereConformal(centre, SUN_RADIUS_KM);
    expect(image.centre.x).toBeCloseTo(1.0781775977, 8);
    expect(image.centre.y).toBeCloseTo(-0.0241896156, 8);
    expect(image.centre.z).toBeCloseTo(12_741.9524263569, 8);
    const diameterMetres = image.radiusKm * 2_000;
    expect(diameterMetres).toBeGreaterThan(9.7);
    expect(diameterMetres).toBeLessThan(10.5);
    expect(image.centre.z).toBeGreaterThan(2 * EARTH_RADIUS_KM - 2);
    expect(image.centre.z).toBeLessThan(2 * EARTH_RADIUS_KM + 2);
  });
});
