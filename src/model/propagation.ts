import type { Vec3 } from './types';

export interface RayState {
  position: Vec3;
  direction: Vec3;
  pathLengthKm: number;
}

/**
 * Contract for future physical or phenomenological field models.
 * The returned vector describes the local change of ray direction per km.
 */
export interface PropagationField<Parameters> {
  readonly id: string;
  readonly label: string;
  directionDerivative(
    state: Readonly<RayState>,
    parameters: Readonly<Parameters>,
  ): Vec3;
}

export interface IntegrationOptions {
  stepKm: number;
  maximumPathLengthKm: number;
  maximumSteps: number;
}
