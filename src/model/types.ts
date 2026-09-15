export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface GeoCoordinate {
  latitudeDeg: number;
  longitudeDeg: number;
}

export interface CelestialSource {
  declinationDeg: number;
  hourAngleDeg: number;
}

export interface HorizontalAngles {
  azimuthDeg: number;
  elevationDeg: number;
}

export interface ViewOptions {
  showMapGrid: boolean;
  showCoastline: boolean;
  showDomeGrid: boolean;
  showStraightComparison: boolean;
  showRayTangent: boolean;
}

export interface ModelState {
  observer: GeoCoordinate;
  source: CelestialSource;
  mapRadiusKm: number;
  domeHeightKm: number;
  domeRadiusScale: number;
  rayParameter: number;
  view: ViewOptions;
}

export interface BaselineRay {
  points: Vec3[];
  controlPoint: Vec3;
}

export interface ComputedModel {
  observerPoint: Vec3;
  sourcePoint: Vec3;
  sourceEarthFixedLongitudeDeg: number;
  horizontal: HorizontalAngles;
  initialDirection: Vec3;
  baselineRay: BaselineRay;
}

export const DEFAULT_MODEL_STATE: ModelState = {
  observer: {
    latitudeDeg: 50.6751,
    longitudeDeg: 17.9213,
  },
  source: {
    declinationDeg: 15,
    hourAngleDeg: -25,
  },
  mapRadiusKm: 20_015,
  domeHeightKm: 9_000,
  domeRadiusScale: 1,
  rayParameter: 1,
  view: {
    showMapGrid: true,
    showCoastline: true,
    showDomeGrid: true,
    showStraightComparison: true,
    showRayTangent: true,
  },
};
