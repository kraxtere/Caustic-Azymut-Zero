import { projectAzimuthal } from './azimuthal';
import { sampleBaselineRay } from './baselineRay';
import { pointOnDome } from './dome';
import { equatorialToHorizontal, horizontalDirectionOnMap } from './horizontal';
import { normalizeDegrees } from './math';
import type { ComputedModel, ModelState } from './types';

export function computeModel(state: ModelState): ComputedModel {
  const observerPoint = projectAzimuthal(state.observer, state.mapRadiusKm);
  const sourceEarthFixedLongitudeDeg = normalizeDegrees(
    state.observer.longitudeDeg - state.source.hourAngleDeg,
  );
  const sourcePoint = pointOnDome(
    state.source.declinationDeg,
    sourceEarthFixedLongitudeDeg,
    state,
  );
  const horizontal = equatorialToHorizontal(
    state.observer.latitudeDeg,
    state.source.declinationDeg,
    state.source.hourAngleDeg,
  );
  const initialDirection = horizontalDirectionOnMap(
    state.observer.longitudeDeg,
    horizontal,
  );
  const baselineRay = sampleBaselineRay({
    observerPoint,
    sourcePoint,
    initialDirection,
    rayParameter: state.rayParameter,
  });

  return {
    observerPoint,
    sourcePoint,
    sourceEarthFixedLongitudeDeg,
    horizontal,
    initialDirection,
    baselineRay,
  };
}
