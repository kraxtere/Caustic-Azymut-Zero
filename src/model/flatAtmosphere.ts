import { toRadians } from './math';

export interface AtmosphericSample {
  refractiveIndex: number;
  indexGradientPerKm: number;
  extinctionPerKm: number;
}

export interface StratifiedAtmosphere {
  readonly id: string;
  sample(heightKm: number): AtmosphericSample;
}

export interface ExponentialAtmosphereParameters {
  surfaceRefractivity: number;
  refractivityScaleHeightKm: number;
  surfaceExtinctionPerKm?: number;
  extinctionScaleHeightKm?: number;
}

export interface FlatRayPoint {
  horizontalKm: number;
  heightKm: number;
  intensity: number;
}

export type FlatRayTermination = 'surface' | 'range' | 'path-limit';

export interface FlatRayResult {
  points: FlatRayPoint[];
  termination: FlatRayTermination;
  pathLengthKm: number;
  opticalDepth: number;
  finalElevationDeg: number;
}

export interface FlatRayOptions {
  observerHeightKm: number;
  apparentElevationDeg: number;
  maximumHorizontalKm: number;
  atmosphere: StratifiedAtmosphere;
  stepKm?: number;
  maximumPathKm?: number;
  surfaceHeightKm?: number;
}

export interface FlatConnectionOptions {
  observerHeightKm: number;
  targetHorizontalKm: number;
  targetHeightKm: number;
  atmosphere: StratifiedAtmosphere;
  minimumElevationDeg?: number;
  maximumElevationDeg?: number;
  scanStepDeg?: number;
  stepKm?: number;
  heightToleranceKm?: number;
  maximumSolutions?: number;
}

export interface FlatRayConnection {
  observerElevationDeg: number;
  ray: FlatRayResult;
  heightResidualKm: number;
}

interface DifferentialState {
  x: number;
  z: number;
  ux: number;
  uz: number;
  opticalDepth: number;
}

interface Differential {
  x: number;
  z: number;
  ux: number;
  uz: number;
  opticalDepth: number;
}

const RADIANS_TO_DEGREES = 180 / Math.PI;

export function createExponentialAtmosphere(
  parameters: Readonly<ExponentialAtmosphereParameters>,
): StratifiedAtmosphere {
  const {
    surfaceRefractivity,
    refractivityScaleHeightKm,
    surfaceExtinctionPerKm = 0,
    extinctionScaleHeightKm = refractivityScaleHeightKm,
  } = parameters;

  if (surfaceRefractivity < 0) {
    throw new Error('Refraktywność powierzchniowa nie może być ujemna.');
  }
  if (refractivityScaleHeightKm <= 0 || extinctionScaleHeightKm <= 0) {
    throw new Error('Wysokość skali musi być dodatnia.');
  }
  if (surfaceExtinctionPerKm < 0) {
    throw new Error('Ekstynkcja nie może być ujemna.');
  }

  return {
    id: 'flat-exponential-atmosphere',
    sample(heightKm: number): AtmosphericSample {
      const height = Math.max(0, heightKm);
      const refractivity =
        surfaceRefractivity * Math.exp(-height / refractivityScaleHeightKm);
      return {
        refractiveIndex: 1 + refractivity,
        indexGradientPerKm: -refractivity / refractivityScaleHeightKm,
        extinctionPerKm:
          surfaceExtinctionPerKm * Math.exp(-height / extinctionScaleHeightKm),
      };
    },
  };
}

export const VACUUM_ATMOSPHERE: StratifiedAtmosphere = {
  id: 'vacuum',
  sample: () => ({
    refractiveIndex: 1,
    indexGradientPerKm: 0,
    extinctionPerKm: 0,
  }),
};

function derivative(
  state: Readonly<DifferentialState>,
  atmosphere: StratifiedAtmosphere,
): Differential {
  const sample = atmosphere.sample(state.z);
  const gradientLnN = sample.indexGradientPerKm / sample.refractiveIndex;
  const projection = state.uz * gradientLnN;

  return {
    x: state.ux,
    z: state.uz,
    ux: -state.ux * projection,
    uz: gradientLnN - state.uz * projection,
    opticalDepth: sample.extinctionPerKm,
  };
}

function offsetState(
  state: Readonly<DifferentialState>,
  change: Readonly<Differential>,
  factor: number,
): DifferentialState {
  return {
    x: state.x + change.x * factor,
    z: state.z + change.z * factor,
    ux: state.ux + change.ux * factor,
    uz: state.uz + change.uz * factor,
    opticalDepth: state.opticalDepth + change.opticalDepth * factor,
  };
}

function rk4Step(
  state: Readonly<DifferentialState>,
  stepKm: number,
  atmosphere: StratifiedAtmosphere,
): DifferentialState {
  const k1 = derivative(state, atmosphere);
  const k2 = derivative(offsetState(state, k1, stepKm / 2), atmosphere);
  const k3 = derivative(offsetState(state, k2, stepKm / 2), atmosphere);
  const k4 = derivative(offsetState(state, k3, stepKm), atmosphere);

  const next = {
    x: state.x + (stepKm / 6) * (k1.x + 2 * k2.x + 2 * k3.x + k4.x),
    z: state.z + (stepKm / 6) * (k1.z + 2 * k2.z + 2 * k3.z + k4.z),
    ux: state.ux + (stepKm / 6) * (k1.ux + 2 * k2.ux + 2 * k3.ux + k4.ux),
    uz: state.uz + (stepKm / 6) * (k1.uz + 2 * k2.uz + 2 * k3.uz + k4.uz),
    opticalDepth:
      state.opticalDepth +
      (stepKm / 6) *
        (k1.opticalDepth +
          2 * k2.opticalDepth +
          2 * k3.opticalDepth +
          k4.opticalDepth),
  };
  const directionLength = Math.hypot(next.ux, next.uz);
  next.ux /= directionLength;
  next.uz /= directionLength;
  return next;
}

function interpolateBoundary(
  before: Readonly<DifferentialState>,
  after: Readonly<DifferentialState>,
  fraction: number,
): DifferentialState {
  const mix = (start: number, end: number) => start + (end - start) * fraction;
  return {
    x: mix(before.x, after.x),
    z: mix(before.z, after.z),
    ux: mix(before.ux, after.ux),
    uz: mix(before.uz, after.uz),
    opticalDepth: mix(before.opticalDepth, after.opticalDepth),
  };
}

function pointFromState(state: Readonly<DifferentialState>): FlatRayPoint {
  return {
    horizontalKm: state.x,
    heightKm: state.z,
    intensity: Math.exp(-state.opticalDepth),
  };
}

export function traceFlatAtmosphereRay(
  options: Readonly<FlatRayOptions>,
): FlatRayResult {
  const {
    observerHeightKm,
    apparentElevationDeg,
    maximumHorizontalKm,
    atmosphere,
    stepKm = 0.01,
    maximumPathKm = maximumHorizontalKm * 2 + 10,
    surfaceHeightKm = 0,
  } = options;
  if (observerHeightKm <= surfaceHeightKm) {
    throw new Error('Obserwator musi znajdować się nad powierzchnią.');
  }
  if (maximumHorizontalKm <= 0 || stepKm <= 0 || maximumPathKm <= 0) {
    throw new Error('Zakres i krok całkowania muszą być dodatnie.');
  }

  const elevation = toRadians(apparentElevationDeg);
  let state: DifferentialState = {
    x: 0,
    z: observerHeightKm,
    ux: Math.cos(elevation),
    uz: Math.sin(elevation),
    opticalDepth: 0,
  };
  const points = [pointFromState(state)];
  let pathLengthKm = 0;

  while (pathLengthKm < maximumPathKm) {
    const previous = state;
    const actualStep = Math.min(stepKm, maximumPathKm - pathLengthKm);
    state = rk4Step(previous, actualStep, atmosphere);
    pathLengthKm += actualStep;

    if (state.z <= surfaceHeightKm) {
      const fraction =
        (surfaceHeightKm - previous.z) / (state.z - previous.z);
      state = interpolateBoundary(previous, state, fraction);
      state.z = surfaceHeightKm;
      points.push(pointFromState(state));
      return buildResult(points, 'surface', pathLengthKm, state);
    }

    if (state.x >= maximumHorizontalKm) {
      const fraction =
        (maximumHorizontalKm - previous.x) / (state.x - previous.x);
      state = interpolateBoundary(previous, state, fraction);
      state.x = maximumHorizontalKm;
      points.push(pointFromState(state));
      return buildResult(points, 'range', pathLengthKm, state);
    }

    points.push(pointFromState(state));
  }

  return buildResult(points, 'path-limit', pathLengthKm, state);
}

function buildResult(
  points: FlatRayPoint[],
  termination: FlatRayTermination,
  pathLengthKm: number,
  state: Readonly<DifferentialState>,
): FlatRayResult {
  return {
    points,
    termination,
    pathLengthKm,
    opticalDepth: state.opticalDepth,
    finalElevationDeg: Math.atan2(state.uz, state.ux) * RADIANS_TO_DEGREES,
  };
}

export function terminalHeightKm(result: Readonly<FlatRayResult>): number {
  return result.points.at(-1)?.heightKm ?? Number.NaN;
}

/**
 * Finds every ray connecting a finite object point with the observer.
 * Internally we shoot from the observer because the local boundary condition is
 * convenient; the returned path is physically reversible in a stationary,
 * scalar medium and may be displayed from the object toward the observer.
 */
export function findFlatRayConnections(
  options: Readonly<FlatConnectionOptions>,
): FlatRayConnection[] {
  const {
    observerHeightKm,
    targetHorizontalKm,
    targetHeightKm,
    atmosphere,
    minimumElevationDeg = -2,
    maximumElevationDeg = 8,
    scanStepDeg = 0.05,
    stepKm = Math.max(0.001, targetHorizontalKm / 4000),
    heightToleranceKm = 1e-7,
    maximumSolutions = 8,
  } = options;
  if (targetHorizontalKm <= 0 || targetHeightKm < 0) {
    throw new Error('Położenie punktu obiektu jest nieprawidłowe.');
  }
  if (scanStepDeg <= 0 || maximumElevationDeg <= minimumElevationDeg) {
    throw new Error('Zakres skanowania kątów jest nieprawidłowy.');
  }

  const evaluate = (elevationDeg: number) => {
    const ray = traceFlatAtmosphereRay({
      observerHeightKm,
      apparentElevationDeg: elevationDeg,
      maximumHorizontalKm: targetHorizontalKm,
      atmosphere,
      stepKm,
    });
    return {
      elevationDeg,
      ray,
      residual:
        ray.termination === 'range'
          ? terminalHeightKm(ray) - targetHeightKm
          : Number.NaN,
    };
  };

  const solutions: FlatRayConnection[] = [];
  let previous = evaluate(minimumElevationDeg);
  for (
    let angle = minimumElevationDeg + scanStepDeg;
    angle <= maximumElevationDeg + scanStepDeg * 1e-6;
    angle += scanStepDeg
  ) {
    const current = evaluate(Math.min(angle, maximumElevationDeg));
    if (Number.isFinite(previous.residual) && Number.isFinite(current.residual)) {
      if (Math.abs(previous.residual) <= heightToleranceKm) {
        appendUniqueSolution(solutions, previous.elevationDeg, previous.ray, previous.residual);
      } else if (previous.residual * current.residual < 0) {
        let low = previous;
        let high = current;
        for (let iteration = 0; iteration < 60; iteration += 1) {
          const midpoint = evaluate((low.elevationDeg + high.elevationDeg) / 2);
          if (!Number.isFinite(midpoint.residual)) break;
          if (Math.abs(midpoint.residual) <= heightToleranceKm) {
            low = midpoint;
            high = midpoint;
            break;
          }
          if (low.residual * midpoint.residual <= 0) high = midpoint;
          else low = midpoint;
        }
        const best =
          Math.abs(low.residual) <= Math.abs(high.residual) ? low : high;
        appendUniqueSolution(solutions, best.elevationDeg, best.ray, best.residual);
      }
    }
    if (solutions.length >= maximumSolutions) break;
    previous = current;
  }
  return solutions;
}

function appendUniqueSolution(
  solutions: FlatRayConnection[],
  observerElevationDeg: number,
  ray: FlatRayResult,
  heightResidualKm: number,
): void {
  if (
    solutions.some(
      (solution) =>
        Math.abs(solution.observerElevationDeg - observerElevationDeg) < 1e-5,
    )
  ) {
    return;
  }
  solutions.push({ observerElevationDeg, ray, heightResidualKm });
}
