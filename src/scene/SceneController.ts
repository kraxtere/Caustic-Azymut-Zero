import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mesh } from 'topojson-client';
import worldAtlas from 'world-atlas/countries-110m.json';
import { projectAzimuthal } from '../model/azimuthal';
import { pointOnDome } from '../model/dome';
import { add, scale } from '../model/math';
import type { ComputedModel, ModelState, Vec3 } from '../model/types';

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
} as const;

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
    if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
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
  private readonly camera = new THREE.PerspectiveCamera(38, 1, 50, 180_000);
  private readonly renderer: THREE.WebGLRenderer;
  private readonly controls: OrbitControls;
  private readonly modelGroup = new THREE.Group();
  private readonly resizeObserver: ResizeObserver;
  private animationFrame = 0;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
    });
    this.renderer.setClearColor(COLORS.background, 1);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    this.scene.fog = new THREE.FogExp2(COLORS.background, 0.000012);
    this.scene.add(this.modelGroup);

    this.camera.position.set(34_000, 25_000, 34_000);
    this.camera.up.set(0, 1, 0);
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.target.set(0, 3_000, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.07;
    this.controls.minDistance = 8_000;
    this.controls.maxDistance = 120_000;
    this.controls.maxPolarAngle = Math.PI * 0.495;
    this.controls.update();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.canvas.parentElement ?? this.canvas);
    this.resize();
    this.animate();
  }

  update(state: ModelState, computed: ComputedModel): void {
    disposeGroup(this.modelGroup);
    this.addMap(state);
    this.addDome(state);
    this.addMarkers(state, computed);
    this.addRay(state, computed);
  }

  setTopView(): void {
    this.camera.up.set(0, 0, -1);
    this.camera.position.set(0, 61_000, 0.01);
    this.controls.target.set(0, 0, 0);
    this.controls.update();
  }

  setPerspectiveView(): void {
    this.camera.up.set(0, 1, 0);
    this.camera.position.set(34_000, 25_000, 34_000);
    this.controls.target.set(0, 3_000, 0);
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
