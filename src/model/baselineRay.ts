import {
  add,
  cubicBezierPoint,
  distance,
  normalize,
  scale,
} from './math';
import type { BaselineRay, Vec3 } from './types';

export interface BaselineRayInput {
  observerPoint: Vec3;
  sourcePoint: Vec3;
  initialDirection: Vec3;
  rayParameter: number;
  sampleCount?: number;
}

/**
 * Reproduces the FE-Dome ray construction: one tangent control point at the
 * observer and a duplicated source control point. It is a geometric curve,
 * not the numerical integration of a physical field.
 */
export function sampleBaselineRay(input: BaselineRayInput): BaselineRay {
  const sampleCount = Math.max(2, Math.round(input.sampleCount ?? 96));
  const controlDistance =
    (distance(input.observerPoint, input.sourcePoint) * input.rayParameter) / 3;
  const controlPoint = add(
    input.observerPoint,
    scale(normalize(input.initialDirection), controlDistance),
  );

  const points = Array.from({ length: sampleCount }, (_, index) => {
    const t = index / (sampleCount - 1);
    return cubicBezierPoint(
      input.observerPoint,
      controlPoint,
      input.sourcePoint,
      input.sourcePoint,
      t,
    );
  });

  return { points, controlPoint };
}
