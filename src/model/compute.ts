import { projectAzimuthal } from './azimuthal';
import { sampleBaselineRay } from './baselineRay';
import {
  EARTH_RADIUS_KM,
  conformalForward,
  conformalToScene,
  projectStereographicSurface,
  scalarIndexFlat,
  transformSphereConformal,
} from './conformal';
import { celestialObjectState } from './celestial';
import { pointOnDome } from './dome';
import { equatorialToHorizontal, horizontalDirectionOnMap } from './horizontal';
import { normalizeDegrees } from './math';
import { parseUtcMinute } from './solar';
import type { ComputedModel, ConformalObjectResult, GeoCoordinate, ModelState, Vec3 } from './types';

export function computeModel(state: ModelState): ComputedModel {
  if (state.geometryMode === 'conformal') return computeConformalModel(state);

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

function computeConformalModel(state: ModelState): ComputedModel {
  const utc = parseUtcMinute(state.sunUtc);
  const solarIlluminationDirection = celestialObjectState('sun', utc).earthFixedDirection;
  const observerGlobe = conformalInverseForObserver(state);
  const observerPoint = conformalToScene(projectStereographicSurface(state.observer));
  const conformalObjects = state.visibleObjectIds.map((id) =>
    buildConformalObject(id, utc, state, observerGlobe, solarIlluminationDirection),
  );
  const conformalObject = conformalObjects.find(({ id }) => id === state.selectedObject)
    ?? buildConformalObject(state.selectedObject, utc, state, observerGlobe, solarIlluminationDirection);
  const object = celestialObjectState(state.selectedObject, utc);
  const sourcePoint = conformalToScene(conformalObject.imageCentreMath);
  const hourAngleDeg = normalizeDegrees(state.observer.longitudeDeg - object.earthFixedLongitudeDeg);
  const horizontal = equatorialToHorizontal(state.observer.latitudeDeg, object.declinationDeg, hourAngleDeg);
  const initialDirection = horizontalDirectionOnMap(state.observer.longitudeDeg, horizontal);
  const baselineRay = sampleBaselineRay({ observerPoint, sourcePoint, initialDirection, rayParameter: state.rayParameter });

  return {
    observerPoint, sourcePoint,
    sourceEarthFixedLongitudeDeg: object.earthFixedLongitudeDeg,
    horizontal, initialDirection, baselineRay,
    conformalSun: object.id === 'sun' ? {
      utc, raDeg: object.raDeg, declinationDeg: object.declinationDeg,
      distanceAu: object.distanceKm / 149_597_870.7,
      angularRadiusDeg: object.angularRadiusDeg,
      earthFixedLongitudeDeg: object.earthFixedLongitudeDeg,
      earthFixedDirection: object.earthFixedDirection,
      imageCentreMath: conformalObject.imageCentreMath,
      imageRadiusKm: conformalObject.imageRadiusKm,
      scalarIndex: conformalObject.scalarIndex,
      directionDomePoint: conformalObject.directionDomePoint,
    } : undefined,
    conformalObject,
    conformalObjects,
  };
}

function buildConformalObject(
  id: ModelState['selectedObject'], utc: Date, state: ModelState,
  observerGlobe: {x:number;y:number;z:number}, solarIlluminationDirection: {x:number;y:number;z:number},
): NonNullable<ComputedModel['conformalObject']> {
  const object = celestialObjectState(id, utc);
  const distanceKm = object.distanceKm;
  const sourceCentreGlobe = {
    x: object.earthFixedDirection.x * distanceKm,
    y: object.earthFixedDirection.y * distanceKm,
    z: object.earthFixedDirection.z * distanceKm,
  };
  const objectImage = transformSphereConformal(sourceCentreGlobe, object.radiusKm);
  const directionDomePoint = pointOnDome(
    object.declinationDeg,
    object.earthFixedLongitudeDeg,
    {
      mapRadiusKm: state.mapRadiusKm,
      domeHeightKm: state.domeHeightKm,
      domeRadiusScale: state.domeRadiusScale,
    },
  );
  const transformedPath = id === state.selectedObject
    ? sampleTransformedPath(sourceCentreGlobe, observerGlobe)
    : [];
  const infinity = { x: 0, y: 0, z: 2 * EARTH_RADIUS_KM };
  const distanceFromInfinityKm = Math.hypot(
    objectImage.centre.x - infinity.x,
    objectImage.centre.y - infinity.y,
    objectImage.centre.z - infinity.z,
  );
  const minLog = Math.log10(300_000);
  const maxLog = Math.log10(600 * 9.4607304725808e12);
  const logDistanceFraction = Math.min(1, Math.max(0,
    (Math.log10(distanceKm) - minLog) / (maxLog - minLog),
  ));

  return {
    id: object.id, name: object.name, kind: object.kind, provenance: object.provenance,
    utc, raDeg: object.raDeg, declinationDeg: object.declinationDeg,
    distanceKm, sourceRadiusKm: object.radiusKm, angularRadiusDeg: object.angularRadiusDeg,
    earthFixedLongitudeDeg: object.earthFixedLongitudeDeg,
    earthFixedDirection: object.earthFixedDirection,
    imageCentreMath: objectImage.centre, imageRadiusKm: objectImage.radiusKm,
    distanceFromInfinityKm, scalarIndex: scalarIndexFlat(objectImage.centre),
    directionDomePoint, transformedPath, logDistanceFraction,
    solarIlluminationDirection,
  };
}

function conformalInverseForObserver(state: ModelState) {
  const latitude = state.observer.latitudeDeg * Math.PI / 180;
  const longitude = state.observer.longitudeDeg * Math.PI / 180;
  return {
    x: EARTH_RADIUS_KM * Math.cos(latitude) * Math.cos(longitude),
    y: EARTH_RADIUS_KM * Math.cos(latitude) * Math.sin(longitude),
    z: EARTH_RADIUS_KM * Math.sin(latitude),
  };
}

function sampleTransformedPath(source: {x:number;y:number;z:number}, observer: {x:number;y:number;z:number}) {
  const mapAt = (t: number): Vec3 => conformalToScene(conformalForward({
    x: source.x + (observer.x - source.x) * t,
    y: source.y + (observer.y - source.y) * t,
    z: source.z + (observer.z - source.z) * t,
  }));
  const a = mapAt(0);
  const b = mapAt(0.5);
  const c = mapAt(1);
  return sampleCircleThrough(a, b, c, 720);
}

function sampleCircleThrough(a: Vec3, b: Vec3, c: Vec3, segments: number): Vec3[] {
  const subtract = (p: Vec3, q: Vec3) => ({ x:p.x-q.x, y:p.y-q.y, z:p.z-q.z });
  const dot = (p: Vec3, q: Vec3) => p.x*q.x+p.y*q.y+p.z*q.z;
  const cross = (p: Vec3, q: Vec3) => ({ x:p.y*q.z-p.z*q.y, y:p.z*q.x-p.x*q.z, z:p.x*q.y-p.y*q.x });
  const length = (p: Vec3) => Math.hypot(p.x,p.y,p.z);
  const normalise = (p: Vec3) => { const n=length(p); return { x:p.x/n, y:p.y/n, z:p.z/n }; };
  const ab=subtract(b,a); const ac=subtract(c,a);
  const abLength=length(ab); const normalRaw=cross(ab,ac);
  if (abLength < 1e-9 || length(normalRaw) < 1e-8*abLength*Math.max(length(ac),1)) {
    return Array.from({length:segments+1},(_,index) => {
      const t=index/segments; return {x:a.x+(c.x-a.x)*t,y:a.y+(c.y-a.y)*t,z:a.z+(c.z-a.z)*t};
    });
  }
  const u=normalise(ab); const normal=normalise(normalRaw); const v=normalise(cross(normal,u));
  const bx=abLength;
  const cx=dot(ac,u); const cy=dot(ac,v);
  if (Math.abs(cy)<1e-9) return [a,c];
  const centreX=bx/2;
  const centreY=(cx*cx+cy*cy-2*centreX*cx)/(2*cy);
  const centre={x:a.x+u.x*centreX+v.x*centreY,y:a.y+u.y*centreX+v.y*centreY,z:a.z+u.z*centreX+v.z*centreY};
  const radius=Math.hypot(centreX,centreY);
  const angle=(p:Vec3) => Math.atan2(dot(subtract(p,centre),v),dot(subtract(p,centre),u));
  const start=angle(a); const middle=angle(b); const end=angle(c);
  const positive=(value:number) => ((value%(2*Math.PI))+2*Math.PI)%(2*Math.PI);
  const ccw=positive(end-start);
  const delta=positive(middle-start)<=ccw+1e-7 ? ccw : ccw-2*Math.PI;
  return Array.from({length:segments+1},(_,index) => {
    const theta=start+delta*(index/segments);
    return {x:centre.x+radius*(u.x*Math.cos(theta)+v.x*Math.sin(theta)),y:centre.y+radius*(u.y*Math.cos(theta)+v.y*Math.sin(theta)),z:centre.z+radius*(u.z*Math.cos(theta)+v.z*Math.sin(theta))};
  });
}

/** Exact only for the unperturbed conformal-inversion baseline. */
export function sampleBaselineInversionPath(
  object: ConformalObjectResult,
  observer: GeoCoordinate,
): Vec3[] {
  const source = {
    x: object.earthFixedDirection.x * object.distanceKm,
    y: object.earthFixedDirection.y * object.distanceKm,
    z: object.earthFixedDirection.z * object.distanceKm,
  };
  const latitude = observer.latitudeDeg * Math.PI / 180;
  const longitude = observer.longitudeDeg * Math.PI / 180;
  const observerGlobe = {
    x: EARTH_RADIUS_KM * Math.cos(latitude) * Math.cos(longitude),
    y: EARTH_RADIUS_KM * Math.cos(latitude) * Math.sin(longitude),
    z: EARTH_RADIUS_KM * Math.sin(latitude),
  };
  return sampleTransformedPath(source, observerGlobe);
}
