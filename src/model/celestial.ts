import { AU_KM, EARTH_RADIUS_KM, SUN_RADIUS_KM, transformSphereConformal } from './conformal';
import { normalizeAzimuth, normalizeDegrees, toDegrees, toRadians } from './math';
import { gmstDegrees, julianDay, solarEphemeris } from './solar';
import type { ObjectId, Vec3 } from './types';

const LIGHT_YEAR_KM = 9.4607304725808e12;
const MOON_RADIUS_KM = 1_737.4;

export interface CelestialObjectState {
  id: ObjectId;
  name: string;
  kind: 'star' | 'planet' | 'moon' | 'sun';
  provenance: string;
  raDeg: number;
  declinationDeg: number;
  distanceKm: number;
  radiusKm: number;
  angularRadiusDeg: number;
  earthFixedLongitudeDeg: number;
  earthFixedDirection: Vec3;
}

interface FixedStar {
  id: Exclude<ObjectId, 'sun' | 'moon'>;
  name: string;
  raDeg: number;
  declinationDeg: number;
  distanceLy: number;
  radiusSolar: number;
}

export type PlanetId = Extract<ObjectId, 'mercury' | 'venus' | 'mars' | 'jupiter' | 'saturn' | 'uranus' | 'neptune'>;
interface OrbitalElements {
  id: PlanetId | 'earth'; name: string; radiusKm: number; color: number;
  base: [number, number, number, number, number, number];
  rate: [number, number, number, number, number, number];
}

// JPL SSD approximate Keplerian elements, fit for 1800–2050.
const PLANETS: OrbitalElements[] = [
  { id:'mercury', name:'Merkury', radiusKm:2439.7, color:0xb9b1a6, base:[.38709927,.20563593,7.00497902,252.2503235,77.45779628,48.33076593], rate:[.00000037,.00001906,-.00594749,149472.67411175,.16047689,-.12534081] },
  { id:'venus', name:'Wenus', radiusKm:6051.8, color:0xffd08a, base:[.72333566,.00677672,3.39467605,181.9790995,131.60246718,76.67984255], rate:[.0000039,-.00004107,-.0007889,58517.81538729,.00268329,-.27769418] },
  { id:'earth', name:'Ziemia', radiusKm:6371, color:0x5f8fff, base:[1.00000261,.01671123,-.00001531,100.46457166,102.93768193,0], rate:[.00000562,-.00004392,-.01294668,35999.37244981,.32327364,0] },
  { id:'mars', name:'Mars', radiusKm:3389.5, color:0xff7358, base:[1.52371034,.0933941,1.84969142,-4.55343205,-23.94362959,49.55953891], rate:[.00001847,.00007882,-.00813131,19140.30268499,.44441088,-.29257343] },
  { id:'jupiter', name:'Jowisz', radiusKm:69911, color:0xf0c8a0, base:[5.202887,.04838624,1.30439695,34.39644051,14.72847983,100.47390909], rate:[-.00011607,-.00013253,-.00183714,3034.74612775,.21252668,.20469106] },
  { id:'saturn', name:'Saturn', radiusKm:58232, color:0xf5df9c, base:[9.53667594,.05386179,2.48599187,49.95424423,92.59887831,113.66242448], rate:[-.0012506,-.00050991,.00193609,1222.49362201,-.41897216,-.28867794] },
  { id:'uranus', name:'Uran', radiusKm:25362, color:0x8ce8ef, base:[19.18916464,.04725744,.77263783,313.23810451,170.9542763,74.01692503], rate:[-.00196176,-.00004397,-.00242939,428.48202785,.40805281,.04240589] },
  { id:'neptune', name:'Neptun', radiusKm:24622, color:0x628dff, base:[30.06992276,.00859048,1.77004347,-55.12002969,44.96476227,131.78422574], rate:[.00026291,.00005105,.00035372,218.45945325,-.32241464,-.00508664] },
];

export const FIXED_STARS: FixedStar[] = [
  { id: 'polaris', name: 'Polaris', raDeg: 37.9546, declinationDeg: 89.2641, distanceLy: 447.6, radiusSolar: 37.5 },
  { id: 'sirius', name: 'Syriusz', raDeg: 101.2872, declinationDeg: -16.7161, distanceLy: 8.60, radiusSolar: 1.711 },
  { id: 'vega', name: 'Wega', raDeg: 279.2347, declinationDeg: 38.7837, distanceLy: 25.04, radiusSolar: 2.362 },
  { id: 'betelgeuse', name: 'Betelgeza', raDeg: 88.7930, declinationDeg: 7.4071, distanceLy: 548, radiusSolar: 764 },
  { id: 'alpha-centauri', name: 'Alfa Centauri A', raDeg: 219.9021, declinationDeg: -60.8339, distanceLy: 4.367, radiusSolar: 1.2234 },
];

function directionFromEquatorial(raDeg: number, declinationDeg: number, date: Date) {
  const earthFixedLongitudeDeg = normalizeDegrees(raDeg - gmstDegrees(date));
  const declination = toRadians(declinationDeg);
  const longitude = toRadians(earthFixedLongitudeDeg);
  return {
    earthFixedLongitudeDeg,
    earthFixedDirection: {
      x: Math.cos(declination) * Math.cos(longitude),
      y: Math.cos(declination) * Math.sin(longitude),
      z: Math.sin(declination),
    },
  };
}

function moonState(date: Date): CelestialObjectState {
  const days = julianDay(date) - 2_451_545;
  const meanLongitude = normalizeAzimuth(218.316 + 13.176396 * days);
  const meanAnomaly = normalizeAzimuth(134.963 + 13.064993 * days);
  const argumentLatitude = normalizeAzimuth(93.272 + 13.229350 * days);
  const longitude = toRadians(meanLongitude + 6.289 * Math.sin(toRadians(meanAnomaly)));
  const latitude = toRadians(5.128 * Math.sin(toRadians(argumentLatitude)));
  const distanceKm = 385_001 - 20_905 * Math.cos(toRadians(meanAnomaly));
  const obliquity = toRadians(23.4393 - 3.563e-7 * days);
  const x = Math.cos(longitude) * Math.cos(latitude);
  const y = Math.sin(longitude) * Math.cos(latitude) * Math.cos(obliquity) - Math.sin(latitude) * Math.sin(obliquity);
  const z = Math.sin(longitude) * Math.cos(latitude) * Math.sin(obliquity) + Math.sin(latitude) * Math.cos(obliquity);
  const raDeg = normalizeAzimuth(toDegrees(Math.atan2(y, x)));
  const declinationDeg = toDegrees(Math.asin(z));
  const direction = directionFromEquatorial(raDeg, declinationDeg, date);
  return {
    id: 'moon', name: 'Księżyc', kind: 'moon',
    provenance: 'Efemeryda niskiej precyzji (orbita geocentryczna)',
    raDeg, declinationDeg, distanceKm, radiusKm: MOON_RADIUS_KM,
    angularRadiusDeg: toDegrees(Math.asin(MOON_RADIUS_KM / distanceKm)),
    ...direction,
  };
}

function heliocentricEcliptic(elements: OrbitalElements, centuries: number): Vec3 {
  const [a,e,i,l,peri,node] = elements.base.map((v,index) => v + elements.rate[index]! * centuries) as [number,number,number,number,number,number];
  const meanAnomaly = normalizeDegrees(l - peri);
  let eccentricAnomaly = toRadians(meanAnomaly);
  const meanAnomalyRad = toRadians(meanAnomaly);
  for (let iteration=0; iteration<12; iteration += 1) {
    eccentricAnomaly -= (eccentricAnomaly - e * Math.sin(eccentricAnomaly) - meanAnomalyRad) / (1 - e * Math.cos(eccentricAnomaly));
  }
  const xp = a * (Math.cos(eccentricAnomaly) - e);
  const yp = a * Math.sqrt(1 - e * e) * Math.sin(eccentricAnomaly);
  const omega = toRadians(peri - node);
  const inclination = toRadians(i);
  const ascending = toRadians(node);
  return {
    x:(Math.cos(omega)*Math.cos(ascending)-Math.sin(omega)*Math.sin(ascending)*Math.cos(inclination))*xp+(-Math.sin(omega)*Math.cos(ascending)-Math.cos(omega)*Math.sin(ascending)*Math.cos(inclination))*yp,
    y:(Math.cos(omega)*Math.sin(ascending)+Math.sin(omega)*Math.cos(ascending)*Math.cos(inclination))*xp+(-Math.sin(omega)*Math.sin(ascending)+Math.cos(omega)*Math.cos(ascending)*Math.cos(inclination))*yp,
    z:Math.sin(omega)*Math.sin(inclination)*xp+Math.cos(omega)*Math.sin(inclination)*yp,
  };
}

export const PLANET_IDS: PlanetId[] = ['mercury','venus','mars','jupiter','saturn','uranus','neptune'];
export const SYNODIC_DAYS: Record<PlanetId, number> = {
  mercury: 115.88, venus: 583.92, mars: 779.94, jupiter: 398.88,
  saturn: 378.09, uranus: 369.66, neptune: 367.49,
};

export interface PlanetTrajectoryFrame {
  id: PlanetId;
  name: string;
  heliocentricAu: Vec3;
  geocentricAu: Vec3;
  invertedOffsetKm: Vec3;
}

export function planetTrajectoryFrame(id: PlanetId, date: Date): PlanetTrajectoryFrame {
  const centuries = (julianDay(date) - 2_451_545) / 36_525;
  const planet = PLANETS.find((item) => item.id === id)!;
  const earth = PLANETS.find((item) => item.id === 'earth')!;
  const heliocentricAu = heliocentricEcliptic(planet, centuries);
  const earthAu = heliocentricEcliptic(earth, centuries);
  const geocentricAu = {
    x: heliocentricAu.x - earthAu.x,
    y: heliocentricAu.y - earthAu.y,
    z: heliocentricAu.z - earthAu.z,
  };
  const distanceAu = Math.hypot(geocentricAu.x, geocentricAu.y, geocentricAu.z);
  const centre = {
    x: geocentricAu.x / distanceAu * distanceAu * AU_KM,
    y: geocentricAu.y / distanceAu * distanceAu * AU_KM,
    z: geocentricAu.z / distanceAu * distanceAu * AU_KM,
  };
  const image = transformSphereConformal(centre, planet.radiusKm);
  return {
    id, name: planet.name, heliocentricAu, geocentricAu,
    invertedOffsetKm: {
      x: image.centre.x,
      y: image.centre.y,
      z: image.centre.z - 2 * EARTH_RADIUS_KM,
    },
  };
}

function planetState(id: PlanetId, date: Date): CelestialObjectState {
  const centuries = (julianDay(date) - 2_451_545) / 36_525;
  const planet = PLANETS.find((item) => item.id === id)!;
  const earth = PLANETS.find((item) => item.id === 'earth')!;
  const p = heliocentricEcliptic(planet, centuries);
  const e = heliocentricEcliptic(earth, centuries);
  const geocentricAu = { x:p.x-e.x, y:p.y-e.y, z:p.z-e.z };
  const obliquity = toRadians(23.43928);
  const equatorial = {
    x:geocentricAu.x,
    y:Math.cos(obliquity)*geocentricAu.y-Math.sin(obliquity)*geocentricAu.z,
    z:Math.sin(obliquity)*geocentricAu.y+Math.cos(obliquity)*geocentricAu.z,
  };
  const distanceAu = Math.hypot(equatorial.x,equatorial.y,equatorial.z);
  const raDeg = normalizeAzimuth(toDegrees(Math.atan2(equatorial.y,equatorial.x)));
  const declinationDeg = toDegrees(Math.asin(equatorial.z/distanceAu));
  return {
    id, name:planet.name, kind:'planet',
    provenance:'JPL SSD — przybliżone elementy Keplera 1800–2050',
    raDeg, declinationDeg, distanceKm:distanceAu*AU_KM, radiusKm:planet.radiusKm,
    angularRadiusDeg:toDegrees(Math.asin(planet.radiusKm/(distanceAu*AU_KM))),
    ...directionFromEquatorial(raDeg,declinationDeg,date),
  };
}

export function celestialObjectState(id: ObjectId, date: Date): CelestialObjectState {
  if (id === 'sun') {
    const sun = solarEphemeris(date);
    return {
      id, name: 'Słońce', kind: 'sun', provenance: 'Efemeryda słoneczna Meeusa',
      raDeg: sun.raDeg, declinationDeg: sun.declinationDeg,
      distanceKm: sun.distanceAu * AU_KM, radiusKm: SUN_RADIUS_KM,
      angularRadiusDeg: sun.angularRadiusDeg,
      earthFixedLongitudeDeg: sun.earthFixedLongitudeDeg,
      earthFixedDirection: sun.earthFixedDirection,
    };
  }
  if (id === 'moon') return moonState(date);
  if (['mercury','venus','mars','jupiter','saturn','uranus','neptune'].includes(id)) {
    return planetState(id as PlanetId, date);
  }
  const star = FIXED_STARS.find((candidate) => candidate.id === id);
  if (!star) throw new Error(`Nieznany obiekt katalogowy: ${id}`);
  const distanceKm = star.distanceLy * LIGHT_YEAR_KM;
  const radiusKm = star.radiusSolar * SUN_RADIUS_KM;
  const direction = directionFromEquatorial(star.raDeg, star.declinationDeg, date);
  return {
    id: star.id, name: star.name, kind: 'star',
    provenance: 'Pozycja J2000; odległość katalogowa z paralaksy',
    raDeg: star.raDeg, declinationDeg: star.declinationDeg,
    distanceKm, radiusKm,
    angularRadiusDeg: toDegrees(Math.asin(Math.min(1, radiusKm / distanceKm))),
    ...direction,
  };
}

export const OBJECT_OPTIONS: Array<{ id: ObjectId; label: string }> = [
  { id: 'sun', label: 'Słońce' },
  { id: 'moon', label: 'Księżyc' },
  { id: 'mercury', label: 'Merkury' },
  { id: 'venus', label: 'Wenus' },
  { id: 'mars', label: 'Mars' },
  { id: 'jupiter', label: 'Jowisz' },
  { id: 'saturn', label: 'Saturn' },
  { id: 'uranus', label: 'Uran' },
  { id: 'neptune', label: 'Neptun' },
  ...FIXED_STARS.map(({ id, name }) => ({ id, label: name })),
];
