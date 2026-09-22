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
  showTerminator: boolean;
  showDirectionDome: boolean;
  showPhysicalSun: boolean;
  showTransformedPath: boolean;
  showConnectionLines: boolean;
}

export interface AuxiliaryObserver {
  id: 'north' | 'south';
  name: string;
  enabled: boolean;
  coordinate: GeoCoordinate;
}

export type ObjectId =
  | 'sun'
  | 'moon'
  | 'mercury'
  | 'venus'
  | 'mars'
  | 'jupiter'
  | 'saturn'
  | 'uranus'
  | 'neptune'
  | 'polaris'
  | 'sirius'
  | 'vega'
  | 'betelgeuse'
  | 'alpha-centauri';

export type GeometryMode = 'conformal' | 'fe-dome';

export interface ModelState {
  geometryMode: GeometryMode;
  selectedObject: ObjectId;
  visibleObjectIds: ObjectId[];
  sunUtc: string;
  observer: GeoCoordinate;
  auxiliaryObservers: AuxiliaryObserver[];
  observerDomeRadiusKm: number;
  straightRayBoundaryKm: number;
  objectVisualScale: number;
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

export interface ConformalObjectResult {
  id: ObjectId;
  name: string;
  kind: 'star' | 'planet' | 'moon' | 'sun';
  provenance: string;
  utc: Date;
  raDeg: number;
  declinationDeg: number;
  distanceKm: number;
  sourceRadiusKm: number;
  angularRadiusDeg: number;
  earthFixedLongitudeDeg: number;
  earthFixedDirection: Vec3;
  imageCentreMath: Vec3;
  imageRadiusKm: number;
  distanceFromInfinityKm: number;
  scalarIndex: number;
  directionDomePoint: Vec3;
  transformedPath: Vec3[];
  logDistanceFraction: number;
  solarIlluminationDirection: Vec3;
}

export interface ComputedModel {
  observerPoint: Vec3;
  sourcePoint: Vec3;
  sourceEarthFixedLongitudeDeg: number;
  horizontal: HorizontalAngles;
  initialDirection: Vec3;
  baselineRay: BaselineRay;
  conformalSun?: {
    utc: Date;
    raDeg: number;
    declinationDeg: number;
    distanceAu: number;
    angularRadiusDeg: number;
    earthFixedLongitudeDeg: number;
    earthFixedDirection: Vec3;
    imageCentreMath: Vec3;
    imageRadiusKm: number;
    scalarIndex: number;
    directionDomePoint: Vec3;
  };
  conformalObject?: ConformalObjectResult;
  conformalObjects?: ConformalObjectResult[];
}

export const DEFAULT_MODEL_STATE: ModelState = {
  geometryMode: 'conformal',
  selectedObject: 'sun',
  visibleObjectIds: [
    'sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn',
    'uranus', 'neptune', 'polaris', 'sirius', 'vega', 'betelgeuse', 'alpha-centauri',
  ],
  sunUtc: '2026-09-16T12:00',
  observer: {
    latitudeDeg: 50.6751,
    longitudeDeg: 17.9213,
  },
  auxiliaryObservers: [
    { id: 'north', name: 'Obserwator północny', enabled: false, coordinate: { latitudeDeg: 25, longitudeDeg: 0 } },
    { id: 'south', name: 'Obserwator południowy', enabled: false, coordinate: { latitudeDeg: -25, longitudeDeg: 0 } },
  ],
  observerDomeRadiusKm: 4_800,
  straightRayBoundaryKm: 3_600,
  objectVisualScale: 1,
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
    showTerminator: true,
    showDirectionDome: true,
    showPhysicalSun: true,
    showTransformedPath: true,
    showConnectionLines: true,
  },
};
