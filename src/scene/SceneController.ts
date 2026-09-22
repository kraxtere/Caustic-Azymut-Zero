import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mesh } from 'topojson-client';
import worldAtlas from 'world-atlas/countries-110m.json';
import { projectAzimuthal } from '../model/azimuthal';
import {
  EARTH_RADIUS_KM,
  conformalToScene,
  projectStereographicSurface,
  stereographicRadiusForLatitude,
} from '../model/conformal';
import { pointOnDome } from '../model/dome';
import { sampleBaselineInversionPath } from '../model/compute';
import { equatorialToHorizontal, horizontalDirectionOnMap } from '../model/horizontal';
import { add, scale } from '../model/math';
import type { ComputedModel, GeoCoordinate, ModelState, Vec3 } from '../model/types';

interface CoastlineMesh {
  coordinates: number[][][];
}

const COLORS = {
  background: 0x061012,
  map: 0x0b2427,
  mapEdge: 0x4c8e8c,
  mapGrid: 0x28585a,
  coastline: 0x7ab9a4,
  dome: 0x54c7ce,
  domeGrid: 0x39898f,
  observer: 0xff6f61,
  source: 0xffc857,
  ray: 0xff4fa3,
  straight: 0xa2b3b7,
  tangent: 0x61d6ff,
  terminator: 0xffe39a,
  direction: 0x61d6ff,
  opticalPath: 0xff4fa3,
} as const;

const CONFORMAL_CUTOFF_LATITUDE_DEG = -60;
const OBJECT_COLOURS: Record<string, number> = {
  sun: 0xffd15c, moon: 0xdde8ed, mercury: 0xb9b1a6, venus: 0xffbd73,
  mars: 0xff684f, jupiter: 0xe8b98d, saturn: 0xf4dc91, uranus: 0x76dce8,
  neptune: 0x5d85ff, polaris: 0xe8f3ff, sirius: 0xaed8ff, vega: 0xcbdfff,
  betelgeuse: 0xff9a62, 'alpha-centauri': 0xffe0a6,
};
const OBSERVER_COLOURS = [0xff756a, 0x65d2cb, 0xb78cff] as const;

function vector3(point: Vec3): THREE.Vector3 {
  return new THREE.Vector3(point.x, point.y, point.z);
}

function lineMaterial(
  color: number,
  opacity = 1,
  dashed = false,
): THREE.LineBasicMaterial | THREE.LineDashedMaterial {
  const options = { color, transparent: opacity < 1, opacity };
  return dashed
    ? new THREE.LineDashedMaterial({ ...options, dashSize: 650, gapSize: 420 })
    : new THREE.LineBasicMaterial(options);
}

function createLine(
  points: Vec3[],
  color: number,
  opacity = 1,
  dashed = false,
  loop = false,
): THREE.Line {
  const geometry = new THREE.BufferGeometry().setFromPoints(points.map(vector3));
  const material = lineMaterial(color, opacity, dashed);
  const line = loop
    ? new THREE.LineLoop(geometry, material)
    : new THREE.Line(geometry, material);
  if (dashed) line.computeLineDistances();
  return line;
}

function disposeGroup(group: THREE.Group): void {
  group.traverse((object) => {
    if (object instanceof THREE.Sprite) {
      object.material.map?.dispose();
      object.material.dispose();
    } else if (
      object instanceof THREE.Mesh
      || object instanceof THREE.Line
      || object instanceof THREE.Points
    ) {
      object.geometry.dispose();
      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];
      for (const material of materials) material.dispose();
    }
  });
  group.clear();
}

export class SceneController {
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(38, 1, 50, 300_000);
  private readonly renderer: THREE.WebGLRenderer;
  private readonly controls: OrbitControls;
  private readonly modelGroup = new THREE.Group();
  private readonly resizeObserver: ResizeObserver;
  private animationFrame = 0;
  private lastComputed?: ComputedModel;
  private lastState?: ModelState;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
    });
    this.renderer.setClearColor(0x071827, 1);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    this.scene.fog = new THREE.FogExp2(0x071827, 0.000009);
    this.addStarField();
    this.scene.add(this.modelGroup);

    this.camera.position.set(70_000, 52_000, 70_000);
    this.camera.up.set(0, 1, 0);
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.target.set(0, 3_000, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.07;
    this.controls.minDistance = 8_000;
    this.controls.maxDistance = 220_000;
    this.controls.maxPolarAngle = Math.PI * 0.495;
    this.controls.update();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.canvas.parentElement ?? this.canvas);
    this.resize();
    this.animate();
  }

  private addStarField(): void {
    const points: THREE.Vector3[] = [];
    for (let index = 0; index < 900; index += 1) {
      const longitude = ((index * 137.508) % 360) * Math.PI / 180;
      const latitude = Math.asin((((index * 73) % 899) / 899) * 1.6 - 0.35);
      const radius = 180_000 + (index % 7) * 2500;
      points.push(new THREE.Vector3(
        radius * Math.cos(latitude) * Math.cos(longitude),
        Math.abs(radius * Math.sin(latitude)) + 8000,
        radius * Math.cos(latitude) * Math.sin(longitude),
      ));
    }
    const field = new THREE.Points(
      new THREE.BufferGeometry().setFromPoints(points),
      new THREE.PointsMaterial({ color:0xcdeaff, size:1.35, sizeAttenuation:false, transparent:true, opacity:.68, depthWrite:false }),
    );
    this.scene.add(field);
  }

  update(state: ModelState, computed: ComputedModel): void {
    this.lastComputed = computed;
    this.lastState = state;
    disposeGroup(this.modelGroup);
    if (state.geometryMode === 'conformal' && computed.conformalObject) {
      this.addConformalMap(state, computed);
      this.addConformalMarkers(state, computed);
      return;
    }
    this.addMap(state);
    this.addDome(state);
    this.addMarkers(state, computed);
    this.addRay(state, computed);
  }

  private addConformalMap(state: ModelState, computed: ComputedModel): void {
    const cutoffRadius = stereographicRadiusForLatitude(
      CONFORMAL_CUTOFF_LATITUDE_DEG,
    );
    const source = computed.conformalObject;
    if (!source) return;

    const disk = new THREE.Mesh(
      new THREE.CircleGeometry(cutoffRadius, 192),
      new THREE.ShaderMaterial({
        transparent: false,
        side: THREE.DoubleSide,
        uniforms: {
          earthRadius: { value: EARTH_RADIUS_KM },
          sunDirection: {
            value: new THREE.Vector3(
              source.solarIlluminationDirection.x,
              source.solarIlluminationDirection.y,
              source.solarIlluminationDirection.z,
            ),
          },
          dayColor: { value: new THREE.Color(0x317f84) },
          nightColor: { value: new THREE.Color(0x07182b) },
        },
        vertexShader: `
          varying vec2 planePosition;
          void main() {
            planePosition = position.xy;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          varying vec2 planePosition;
          uniform float earthRadius;
          uniform vec3 sunDirection;
          uniform vec3 dayColor;
          uniform vec3 nightColor;
          void main() {
            float rho = length(planePosition);
            float theta = 2.0 * atan(rho / (2.0 * earthRadius));
            vec2 radial = rho > 0.0001 ? planePosition / rho : vec2(1.0, 0.0);
            vec3 normal = vec3(
              sin(theta) * radial.y,
              sin(theta) * radial.x,
              cos(theta)
            );
            float incidence = dot(normal, normalize(sunDirection));
            float daylight = smoothstep(-0.025, 0.025, incidence);
            float glow = 0.15 + 0.85 * max(incidence, 0.0);
            vec3 colour = mix(nightColor, dayColor * (0.72 + 0.28 * glow), daylight);
            gl_FragColor = vec4(colour, 1.0);
          }
        `,
      }),
    );
    disk.rotation.x = -Math.PI / 2;
    disk.position.y = -30;
    disk.renderOrder = -3;
    this.modelGroup.add(disk);
    this.modelGroup.add(this.createCircle(cutoffRadius, 6, COLORS.mapEdge, 0.95));

    if (state.view.showMapGrid) this.addConformalGrid(cutoffRadius);
    if (state.view.showCoastline) this.addConformalCoastline();
    if (state.view.showTerminator) {
      this.addConformalTerminator(source.solarIlluminationDirection);
    }
  }

  private addConformalGrid(cutoffRadius: number): void {
    for (let latitude = CONFORMAL_CUTOFF_LATITUDE_DEG; latitude <= 60; latitude += 30) {
      const radius = stereographicRadiusForLatitude(latitude);
      if (radius <= cutoffRadius + 1e-6) {
        this.modelGroup.add(this.createCircle(radius, 5, COLORS.mapGrid, 0.72));
      }
    }
    for (let longitude = -180; longitude < 180; longitude += 15) {
      const points: Vec3[] = [];
      for (let latitude = CONFORMAL_CUTOFF_LATITUDE_DEG; latitude <= 90; latitude += 2) {
        points.push(
          conformalToScene(
            projectStereographicSurface({ latitudeDeg: latitude, longitudeDeg: longitude }),
          ),
        );
      }
      for (const point of points) point.y = 5;
      this.modelGroup.add(createLine(points, COLORS.mapGrid, 0.56));
    }
  }

  private addConformalCoastline(): void {
    const topology = worldAtlas as unknown as { objects: { land: unknown } };
    const coastline = mesh(
      worldAtlas as never,
      topology.objects.land as never,
    ) as unknown as CoastlineMesh;

    for (const coordinates of coastline.coordinates) {
      let segment: Vec3[] = [];
      const flush = () => {
        if (segment.length > 1) this.modelGroup.add(createLine(segment, COLORS.coastline, 0.92));
        segment = [];
      };
      for (const coordinate of coordinates) {
        const longitudeDeg = coordinate[0] ?? 0;
        const latitudeDeg = coordinate[1] ?? 0;
        if (latitudeDeg < CONFORMAL_CUTOFF_LATITUDE_DEG) {
          flush();
          continue;
        }
        const point = conformalToScene(
          projectStereographicSurface({ latitudeDeg, longitudeDeg }),
        );
        point.y = 18;
        segment.push(point);
      }
      flush();
    }
  }

  private addConformalTerminator(direction: Vec3): void {
    const reference = Math.abs(direction.z) < 0.9
      ? { x: 0, y: 0, z: 1 }
      : { x: 1, y: 0, z: 0 };
    const cross = (a: Vec3, b: Vec3): Vec3 => ({
      x: a.y * b.z - a.z * b.y,
      y: a.z * b.x - a.x * b.z,
      z: a.x * b.y - a.y * b.x,
    });
    const normalise = (v: Vec3): Vec3 => {
      const length = Math.hypot(v.x, v.y, v.z);
      return { x: v.x / length, y: v.y / length, z: v.z / length };
    };
    const first = normalise(cross(direction, reference));
    const second = normalise(cross(direction, first));
    let segment: Vec3[] = [];
    const flush = () => {
      if (segment.length > 1) {
        this.modelGroup.add(createLine(segment, COLORS.terminator, 1));
        for (const offset of [-20, 20]) {
          this.modelGroup.add(createLine(
            segment.map((point) => ({ ...point, y: point.y + offset })),
            COLORS.terminator,
            0.22,
          ));
        }
      }
      segment = [];
    };
    for (let index = 0; index <= 360; index += 1) {
      const angle = (index * Math.PI) / 180;
      const unit = {
        x: first.x * Math.cos(angle) + second.x * Math.sin(angle),
        y: first.y * Math.cos(angle) + second.y * Math.sin(angle),
        z: first.z * Math.cos(angle) + second.z * Math.sin(angle),
      };
      const latitudeDeg = (Math.asin(unit.z) * 180) / Math.PI;
      if (latitudeDeg < CONFORMAL_CUTOFF_LATITUDE_DEG) {
        flush();
        continue;
      }
      const longitudeDeg = (Math.atan2(unit.y, unit.x) * 180) / Math.PI;
      const point = conformalToScene(
        projectStereographicSurface({ latitudeDeg, longitudeDeg }),
      );
      point.y = 28;
      segment.push(point);
    }
    flush();
  }

  private addConformalMarkers(state: ModelState, computed: ComputedModel): void {
    const source = computed.conformalObject;
    if (!source) return;

    if (state.view.showPhysicalSun) for (const object of computed.conformalObjects ?? [source]) {
      const position = conformalToScene(object.imageCentreMath);
      const colour = OBJECT_COLOURS[object.id] ?? COLORS.source;
      const actual = new THREE.Mesh(
        new THREE.SphereGeometry(Math.max(object.imageRadiusKm * state.objectVisualScale, 0.001), 18, 12),
        new THREE.MeshBasicMaterial({ color: colour }),
      );
      actual.position.copy(vector3(position));
      this.modelGroup.add(actual);
      const marker = new THREE.Points(
        new THREE.BufferGeometry().setFromPoints([vector3(position)]),
        new THREE.PointsMaterial({ color: colour, size: object.kind === 'sun' ? 15 : object.kind === 'moon' ? 12 : 9, sizeAttenuation: false }),
      );
      this.modelGroup.add(marker);
      if (object.id === source.id) this.modelGroup.add(this.createLabel(object.name, position, colour, true));
    }

    if (state.view.showDirectionDome) {
      const observers = [
        { name: 'Główny obserwator', coordinate: state.observer, point: computed.observerPoint },
        ...state.auxiliaryObservers.filter(({ enabled }) => enabled).map((observer) => ({
          name: observer.name,
          coordinate: observer.coordinate,
          point: conformalToScene(projectStereographicSurface(observer.coordinate)),
        })),
      ];
      observers.forEach((observer, index) => {
        const observerColour = OBSERVER_COLOURS[index] ?? COLORS.observer;
        this.addObserverDome(observer.point, observer.coordinate, state.observerDomeRadiusKm, state.straightRayBoundaryKm, observer.name, observerColour);
        for (const object of computed.conformalObjects ?? [source]) {
          this.addObjectDirectionOnDome(state, object, source.id, observer.coordinate, observer.point, observerColour, index);
        }
      });
    }

    if (state.view.showTransformedPath && source.transformedPath.length > 1) {
      this.modelGroup.add(createLine(source.transformedPath, COLORS.opticalPath, 0.92));
    }
  }

  private addObjectDirectionOnDome(
    state: ModelState,
    object: NonNullable<ComputedModel['conformalObject']>,
    selectedId: string,
    observer: GeoCoordinate,
    observerPoint: Vec3,
    observerColour: number,
    observerIndex: number,
  ): void {
    const hourAngleDeg = observer.longitudeDeg - object.earthFixedLongitudeDeg;
    const horizontal = equatorialToHorizontal(observer.latitudeDeg, object.declinationDeg, hourAngleDeg);
    if (horizontal.elevationDeg < 0) return;
    const direction = horizontalDirectionOnMap(observer.longitudeDeg, horizontal);
    const radius = state.observerDomeRadiusKm;
    const transitionRadius = state.straightRayBoundaryKm;
    const nominalDomePosition = {
      x: observerPoint.x + direction.x * radius,
      y: observerPoint.y + 120 + direction.y * radius,
      z: observerPoint.z + direction.z * radius,
    };
    const path = sampleBaselineInversionPath(object, observer);
    const eyePoint = { ...observerPoint, y: observerPoint.y + 190 };
    const hit = this.findDomeIntersection(path, eyePoint, transitionRadius);
    const domePosition = hit?.point ?? nominalDomePosition;
    const arrivalDirection = hit?.direction ?? direction;
    const colour = OBJECT_COLOURS[object.id] ?? COLORS.direction;
    const directionMarker = new THREE.Mesh(
      new THREE.RingGeometry(object.id === selectedId ? 190 : 105, object.id === selectedId ? 285 : 160, 32),
      new THREE.MeshBasicMaterial({ color: colour, transparent: true, opacity: 0.95, side: THREE.DoubleSide }),
    );
    directionMarker.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 0, 1),
      vector3(arrivalDirection).normalize(),
    );
    directionMarker.position.copy(vector3(domePosition));
    this.modelGroup.add(directionMarker);

    if (state.view.showConnectionLines) {
      if (path.length > 1) {
        const curvedPath = hit ? [...path.slice(0, hit.index + 1), hit.point] : path;
        this.modelGroup.add(createLine(curvedPath, colour, observerIndex === 0 ? 0.68 : 0.42));
        if (hit) {
          this.modelGroup.add(createLine([hit.point, eyePoint], colour, observerIndex === 0 ? 1 : 0.72));
          this.addArrivalTangent(
          { x: hit.point.x - hit.direction.x, y: hit.point.y - hit.direction.y, z: hit.point.z - hit.direction.z },
          hit.point,
          colour,
          );
        }
      }
    }
    if (horizontal.elevationDeg >= -2 && (object.id === selectedId || observerIndex > 0)) {
      this.modelGroup.add(this.createLabel(
        observerIndex === 0 ? object.name : `${object.name} · ${observerIndex + 1}`,
        domePosition,
        colour,
        object.id === selectedId,
      ));
    }
    const spokeEnd = {
      x: observerPoint.x + direction.x * 620,
      y: observerPoint.y + 120 + direction.y * 620,
      z: observerPoint.z + direction.z * 620,
    };
    this.modelGroup.add(createLine([observerPoint, spokeEnd], observerColour, 0.45));
  }

  private findDomeIntersection(path: Vec3[], centre: Vec3, radius: number): { point: Vec3; direction: Vec3; index: number } | undefined {
    const distance = (point: Vec3) => Math.hypot(point.x - centre.x, point.y - centre.y, point.z - centre.z);
    for (let index = path.length - 2; index >= 0; index -= 1) {
      const outside = path[index]!;
      const inside = path[index + 1]!;
      const outsideDistance = distance(outside);
      const insideDistance = distance(inside);
      if (outsideDistance >= radius && insideDistance <= radius) {
        const denominator = outsideDistance - insideDistance;
        const t = denominator > 1e-9 ? (outsideDistance - radius) / denominator : 0;
        const point = {
          x: outside.x + (inside.x - outside.x) * t,
          y: outside.y + (inside.y - outside.y) * t,
          z: outside.z + (inside.z - outside.z) * t,
        };
        const directionVector = vector3(inside).sub(vector3(outside)).normalize();
        return { point, direction: { x: directionVector.x, y: directionVector.y, z: directionVector.z }, index };
      }
    }
    return undefined;
  }

  private addArrivalTangent(before: Vec3, end: Vec3, colour: number): void {
    const direction = vector3(end).sub(vector3(before)).normalize();
    const centre = vector3(end);
    const half = 520;
    this.modelGroup.add(createLine([
      { x: centre.x - direction.x * half, y: centre.y - direction.y * half, z: centre.z - direction.z * half },
      { x: centre.x + direction.x * half, y: centre.y + direction.y * half, z: centre.z + direction.z * half },
    ], colour, 1));
  }

  private createLabel(text: string, position: Vec3, colour: number, selected: boolean): THREE.Sprite {
    const canvas = document.createElement('canvas');
    canvas.width = 420; canvas.height = 90;
    const context = canvas.getContext('2d')!;
    context.font = `${selected ? '700' : '600'} ${selected ? 34 : 29}px Inter, sans-serif`;
    context.textAlign = 'center'; context.textBaseline = 'middle';
    context.fillStyle = 'rgba(3,12,20,.82)';
    context.roundRect(8, 8, 404, 74, 20); context.fill();
    context.strokeStyle = `#${colour.toString(16).padStart(6,'0')}`;
    context.lineWidth = selected ? 3 : 1.5; context.stroke();
    context.fillStyle = '#f4fbff'; context.fillText(text, 210, 46);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map:new THREE.CanvasTexture(canvas), transparent:true, depthTest:false }));
    sprite.position.copy(vector3({x:position.x,y:position.y+(selected ? 700 : 480),z:position.z}));
    sprite.scale.set(selected ? 3300 : 2600, selected ? 710 : 560, 1);
    sprite.renderOrder = 20;
    return sprite;
  }

  private addObserverDome(point: Vec3, coordinate: GeoCoordinate, radius: number, transitionRadius: number, name: string, colour: number): void {
    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 48, 18, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshBasicMaterial({
        color: colour, transparent: true, opacity: 0.11,
        side: THREE.DoubleSide, depthWrite: false,
      }),
    );
    dome.position.copy(vector3(point));
    dome.position.y += 120;
    this.modelGroup.add(dome);

    const transition = new THREE.Mesh(
      new THREE.SphereGeometry(transitionRadius, 36, 12, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshBasicMaterial({
        color: COLORS.opticalPath, wireframe: true, transparent: true, opacity: 0.14,
        side: THREE.DoubleSide, depthWrite: false,
      }),
    );
    transition.position.copy(vector3(point));
    transition.position.y += 190;
    this.modelGroup.add(transition);

    for (let elevation = 0; elevation <= 60; elevation += 30) {
      const horizontalRadius = radius * Math.cos(elevation * Math.PI / 180);
      const height = 120 + radius * Math.sin(elevation * Math.PI / 180);
      const ring = this.createCircle(horizontalRadius, height, colour, 0.5);
      ring.position.x = point.x;
      ring.position.z = point.z;
      this.modelGroup.add(ring);
    }
    const observer = new THREE.Mesh(
      new THREE.SphereGeometry(280, 20, 14),
      new THREE.MeshBasicMaterial({ color: colour }),
    );
    observer.position.copy(vector3(point)); observer.position.y += 190;
    this.modelGroup.add(observer);
    this.modelGroup.add(this.createLabel(`${name} · ${coordinate.latitudeDeg.toFixed(0)}°`, { ...point, y: point.y + 350 }, colour, false));
  }

  setTopView(): void {
    this.camera.up.set(0, 0, -1);
    this.camera.position.set(0, 150_000, 0.01);
    this.controls.target.set(0, 0, 0);
    this.controls.update();
  }

  setPerspectiveView(): void {
    this.camera.up.set(0, 1, 0);
    this.camera.position.set(70_000, 52_000, 70_000);
    this.controls.target.set(0, 3_000, 0);
    this.controls.update();
  }

  setObserverView(): void {
    if (!this.lastComputed || !this.lastState) return;
    const point = this.lastComputed.observerPoint;
    const look = horizontalDirectionOnMap(this.lastState.observer.longitudeDeg, { azimuthDeg: 0, elevationDeg: 12 });
    this.camera.up.set(0, 1, 0);
    this.camera.position.set(point.x, point.y + 240, point.z);
    this.controls.target.set(
      point.x + look.x * 12_000,
      point.y + 240 + look.y * 12_000,
      point.z + look.z * 12_000,
    );
    this.controls.update();
  }

  dispose(): void {
    cancelAnimationFrame(this.animationFrame);
    this.resizeObserver.disconnect();
    this.controls.dispose();
    disposeGroup(this.modelGroup);
    this.renderer.dispose();
  }

  private addMap(state: ModelState): void {
    const disk = new THREE.Mesh(
      new THREE.CircleGeometry(state.mapRadiusKm, 128),
      new THREE.MeshBasicMaterial({
        color: COLORS.map,
        transparent: true,
        opacity: 0.88,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    disk.rotation.x = -Math.PI / 2;
    disk.position.y = -30;
    disk.renderOrder = -2;
    this.modelGroup.add(disk);

    const border = this.createCircle(state.mapRadiusKm, 8, COLORS.mapEdge, 0.95);
    this.modelGroup.add(border);

    if (state.view.showMapGrid) {
      for (let latitude = -60; latitude <= 60; latitude += 30) {
        const radius = ((90 - latitude) / 180) * state.mapRadiusKm;
        this.modelGroup.add(this.createCircle(radius, 5, COLORS.mapGrid, 0.7));
      }
      for (let longitude = 0; longitude < 180; longitude += 15) {
        const start = projectAzimuthal(
          { latitudeDeg: -90, longitudeDeg: longitude },
          state.mapRadiusKm,
        );
        const end = projectAzimuthal(
          { latitudeDeg: -90, longitudeDeg: longitude + 180 },
          state.mapRadiusKm,
        );
        start.y = 5;
        end.y = 5;
        this.modelGroup.add(createLine([start, end], COLORS.mapGrid, 0.58));
      }
    }

    if (state.view.showCoastline) this.addCoastline(state.mapRadiusKm);
  }

  private addCoastline(mapRadiusKm: number): void {
    const topology = worldAtlas as unknown as {
      objects: { land: unknown };
    };
    const coastline = mesh(
      worldAtlas as never,
      topology.objects.land as never,
    ) as unknown as CoastlineMesh;

    for (const coordinates of coastline.coordinates) {
      const points = coordinates
        .filter((coordinate) => coordinate.length >= 2)
        .map((coordinate) => {
          const longitudeDeg = coordinate[0] ?? 0;
          const latitudeDeg = coordinate[1] ?? 0;
          const point = projectAzimuthal(
            { latitudeDeg, longitudeDeg },
            mapRadiusKm,
          );
          point.y = 18;
          return point;
        });
      if (points.length > 1) {
        this.modelGroup.add(createLine(points, COLORS.coastline, 0.92));
      }
    }
  }

  private addDome(state: ModelState): void {
    const domeRadius = state.mapRadiusKm * state.domeRadiusScale;
    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(
        domeRadius,
        64,
        28,
        0,
        Math.PI * 2,
        0,
        Math.PI / 2,
      ),
      new THREE.MeshBasicMaterial({
        color: COLORS.dome,
        transparent: true,
        opacity: 0.055,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    dome.scale.y = state.domeHeightKm / domeRadius;
    dome.renderOrder = -1;
    this.modelGroup.add(dome);

    if (!state.view.showDomeGrid) return;

    const domeParameters = {
      mapRadiusKm: state.mapRadiusKm,
      domeHeightKm: state.domeHeightKm,
      domeRadiusScale: state.domeRadiusScale,
    };

    for (let latitude = -60; latitude <= 90; latitude += 30) {
      const points: Vec3[] = [];
      for (let longitude = -180; longitude < 180; longitude += 4) {
        points.push(pointOnDome(latitude, longitude, domeParameters));
      }
      this.modelGroup.add(createLine(points, COLORS.domeGrid, 0.48, false, true));
    }

    for (let longitude = -180; longitude < 180; longitude += 30) {
      const points: Vec3[] = [];
      for (let latitude = -90; latitude <= 90; latitude += 3) {
        points.push(pointOnDome(latitude, longitude, domeParameters));
      }
      this.modelGroup.add(createLine(points, COLORS.domeGrid, 0.42));
    }
  }

  private addMarkers(state: ModelState, computed: ComputedModel): void {
    const observer = new THREE.Mesh(
      new THREE.SphereGeometry(320, 24, 16),
      new THREE.MeshBasicMaterial({ color: COLORS.observer }),
    );
    observer.position.copy(vector3(computed.observerPoint));
    observer.position.y += 220;
    this.modelGroup.add(observer);

    const observerHalo = new THREE.Mesh(
      new THREE.RingGeometry(520, 650, 48),
      new THREE.MeshBasicMaterial({
        color: COLORS.observer,
        transparent: true,
        opacity: 0.5,
        side: THREE.DoubleSide,
      }),
    );
    observerHalo.rotation.x = -Math.PI / 2;
    observerHalo.position.copy(vector3(computed.observerPoint));
    observerHalo.position.y += 35;
    this.modelGroup.add(observerHalo);

    const source = new THREE.Mesh(
      new THREE.SphereGeometry(420, 28, 18),
      new THREE.MeshBasicMaterial({ color: COLORS.source }),
    );
    source.position.copy(vector3(computed.sourcePoint));
    this.modelGroup.add(source);

    const sourceGlow = new THREE.PointLight(COLORS.source, 1.2, state.mapRadiusKm * 0.7);
    sourceGlow.position.copy(vector3(computed.sourcePoint));
    this.modelGroup.add(sourceGlow);
  }

  private addRay(state: ModelState, computed: ComputedModel): void {
    this.modelGroup.add(createLine(computed.baselineRay.points, COLORS.ray, 1));

    if (state.view.showStraightComparison) {
      this.modelGroup.add(
        createLine(
          [computed.observerPoint, computed.sourcePoint],
          COLORS.straight,
          0.58,
          true,
        ),
      );
    }

    if (state.view.showRayTangent) {
      const tangentLength = state.mapRadiusKm * 0.24;
      const tangentEnd = add(
        computed.observerPoint,
        scale(computed.initialDirection, tangentLength),
      );
      this.modelGroup.add(
        createLine([computed.observerPoint, tangentEnd], COLORS.tangent, 0.9),
      );
    }
  }

  private createCircle(
    radius: number,
    height: number,
    color: number,
    opacity: number,
  ): THREE.Line {
    const points: Vec3[] = Array.from({ length: 128 }, (_, index) => {
      const angle = (index / 128) * Math.PI * 2;
      return {
        x: Math.sin(angle) * radius,
        y: height,
        z: -Math.cos(angle) * radius,
      };
    });
    return createLine(points, color, opacity, false, true);
  }

  private resize(): void {
    const parent = this.canvas.parentElement;
    const width = Math.max(1, parent?.clientWidth ?? this.canvas.clientWidth);
    const height = Math.max(1, parent?.clientHeight ?? this.canvas.clientHeight);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  private animate = (): void => {
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.animationFrame = requestAnimationFrame(this.animate);
  };
}
