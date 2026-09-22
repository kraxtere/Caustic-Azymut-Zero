import {
  createExponentialAtmosphere,
  findFlatRayConnections,
} from '../model/flatAtmosphere';

interface AtmospherePanelState {
  observerHeightM: number;
  surfaceRefractivityPpm: number;
  scaleHeightKm: number;
  extinctionPerKm: number;
  rangeKm: number;
}

const SVG_WIDTH = 900;
const SVG_HEIGHT = 280;
const PLOT_LEFT = 48;
const PLOT_RIGHT = 880;
const PLOT_TOP = 22;
const PLOT_BOTTOM = 238;
const MAX_DISPLAY_HEIGHT_KM = 0.25;
const OBJECT_HEIGHTS_KM = [0.01, 0.04, 0.08, 0.12, 0.16];
const RAY_COLORS = ['#ff756a', '#65d2cb', '#ff4fa3', '#ffc857', '#a9c8ff'];

export class AtmospherePanel {
  private state: AtmospherePanelState = {
    observerHeightM: 0.5,
    surfaceRefractivityPpm: 300,
    scaleHeightKm: 3,
    extinctionPerKm: 0.03,
    rangeKm: 10,
  };

  constructor(private readonly root: HTMLElement) {
    this.root.innerHTML = this.template();
    this.bind('atmosphere-observer', 'observerHeightM');
    this.bind('atmosphere-refractivity', 'surfaceRefractivityPpm');
    this.bind('atmosphere-scale-height', 'scaleHeightKm');
    this.bind('atmosphere-extinction', 'extinctionPerKm');
    this.bind('atmosphere-range', 'rangeKm');
    this.render();
  }

  private bind(id: string, key: keyof AtmospherePanelState): void {
    const input = this.root.querySelector<HTMLInputElement>(`#${id}`);
    if (!input) throw new Error(`Brak kontrolki atmosfery: ${id}`);
    input.addEventListener('input', () => {
      this.state[key] = Number(input.value);
      this.render();
    });
  }

  private render(): void {
    const atmosphere = createExponentialAtmosphere({
      surfaceRefractivity: this.state.surfaceRefractivityPpm * 1e-6,
      refractivityScaleHeightKm: this.state.scaleHeightKm,
      surfaceExtinctionPerKm: this.state.extinctionPerKm,
      extinctionScaleHeightKm: Math.max(0.05, this.state.scaleHeightKm / 8),
    });
    const observerHeightKm = this.state.observerHeightM / 1000;
    const targetHorizontalKm = this.state.rangeKm * 0.78;
    const connections = OBJECT_HEIGHTS_KM.map((targetHeightKm) =>
      findFlatRayConnections({
        observerHeightKm,
        targetHorizontalKm,
        targetHeightKm,
        atmosphere,
        stepKm: Math.max(0.001, this.state.rangeKm / 3000),
        minimumElevationDeg: -2,
        maximumElevationDeg: 6,
        scanStepDeg: 0.08,
        maximumSolutions: 3,
      }),
    );

    const plotX = (horizontalKm: number) =>
      PLOT_LEFT +
      (horizontalKm / this.state.rangeKm) * (PLOT_RIGHT - PLOT_LEFT);
    const plotY = (heightKm: number) =>
      PLOT_BOTTOM -
      (heightKm / MAX_DISPLAY_HEIGHT_KM) * (PLOT_BOTTOM - PLOT_TOP);
    const pathMarkup = connections
      .flatMap((solutions, heightIndex) =>
        solutions.map((connection, solutionIndex) => {
          const coordinates = [...connection.ray.points]
            .reverse()
            .filter(
              (_, pointIndex, points) =>
                pointIndex % 3 === 0 || pointIndex === points.length - 1,
            )
            .map(
              (point) =>
                `${plotX(point.horizontalKm).toFixed(2)},${plotY(point.heightKm).toFixed(2)}`,
            )
            .join(' ');
          const transmission = Math.exp(-connection.ray.opticalDepth);
          const opacity = Math.max(0.16, Math.min(1, transmission));
          const dash = solutionIndex === 0 ? '' : 'stroke-dasharray="5 5"';
          return `<polyline points="${coordinates}" fill="none" stroke="${RAY_COLORS[heightIndex]}" stroke-width="2.4" opacity="${opacity}" ${dash} marker-end="url(#information-arrow)" />`;
        }),
      )
      .join('');
    const objectPointMarkup = OBJECT_HEIGHTS_KM.map((heightKm, index) => {
      const visible = connections[index]!.length > 0;
      return visible
        ? `<circle cx="${plotX(targetHorizontalKm)}" cy="${plotY(heightKm)}" r="5" fill="${RAY_COLORS[index]}" />`
        : `<g stroke="#ff756a" stroke-width="2"><line x1="${plotX(targetHorizontalKm) - 5}" y1="${plotY(heightKm) - 5}" x2="${plotX(targetHorizontalKm) + 5}" y2="${plotY(heightKm) + 5}" /><line x1="${plotX(targetHorizontalKm) - 5}" y1="${plotY(heightKm) + 5}" x2="${plotX(targetHorizontalKm) + 5}" y2="${plotY(heightKm) - 5}" /></g>`;
    }).join('');
    const visiblePointCount = connections.filter((solutions) => solutions.length > 0).length;
    const multiplePathCount = connections.filter((solutions) => solutions.length > 1).length;
    const status = `${visiblePointCount}/${OBJECT_HEIGHTS_KM.length} punktów obiektu dociera do obserwatora${multiplePathCount > 0 ? ` · ${multiplePathCount} ma wiele torów` : ''}.`;
    const observerY = plotY(observerHeightKm);

    const svg = this.root.querySelector<SVGSVGElement>('#atmosphere-svg');
    const statusElement = this.root.querySelector<HTMLElement>('#atmosphere-status');
    const outputs = {
      'atmosphere-observer-output': `${this.state.observerHeightM.toFixed(1)} m`,
      'atmosphere-refractivity-output': `${this.state.surfaceRefractivityPpm.toFixed(0)} ppm`,
      'atmosphere-scale-height-output': `${this.state.scaleHeightKm.toFixed(2)} km`,
      'atmosphere-extinction-output': `${this.state.extinctionPerKm.toFixed(2)} km⁻¹`,
      'atmosphere-range-output': `${this.state.rangeKm.toFixed(1)} km`,
    };
    for (const [id, value] of Object.entries(outputs)) {
      const output = this.root.querySelector<HTMLOutputElement>(`#${id}`);
      if (output) output.value = value;
    }
    if (statusElement) statusElement.textContent = status;
    if (!svg) return;
    svg.innerHTML = `
      <defs>
        <clipPath id="atmosphere-clip"><rect x="${PLOT_LEFT}" y="${PLOT_TOP}" width="${PLOT_RIGHT - PLOT_LEFT}" height="${PLOT_BOTTOM - PLOT_TOP}" /></clipPath>
        <marker id="information-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#edf7f4" /></marker>
      </defs>
      <rect x="${PLOT_LEFT}" y="${PLOT_TOP}" width="${PLOT_RIGHT - PLOT_LEFT}" height="${PLOT_BOTTOM - PLOT_TOP}" rx="8" fill="#061012" stroke="rgba(137,205,196,.18)" />
      <g opacity=".35" stroke="#28585a" stroke-width="1">
        <line x1="${PLOT_LEFT}" y1="${plotY(0.05)}" x2="${PLOT_RIGHT}" y2="${plotY(0.05)}" />
        <line x1="${PLOT_LEFT}" y1="${plotY(0.1)}" x2="${PLOT_RIGHT}" y2="${plotY(0.1)}" />
        <line x1="${PLOT_LEFT}" y1="${plotY(0.2)}" x2="${PLOT_RIGHT}" y2="${plotY(0.2)}" />
      </g>
      <rect x="${PLOT_LEFT}" y="${PLOT_BOTTOM}" width="${PLOT_RIGHT - PLOT_LEFT}" height="18" fill="#17383a" />
      <line x1="${PLOT_LEFT}" y1="${observerY}" x2="${PLOT_RIGHT}" y2="${observerY}" stroke="#65d2cb" stroke-width="1" stroke-dasharray="7 7" opacity=".28" />
      <g clip-path="url(#atmosphere-clip)">${pathMarkup}</g>
      <circle cx="${PLOT_LEFT}" cy="${observerY}" r="5" fill="#ff756a" />
      <g>${objectPointMarkup}<line x1="${plotX(targetHorizontalKm)}" y1="${PLOT_BOTTOM}" x2="${plotX(targetHorizontalKm)}" y2="${plotY(0.16)}" stroke="#ffc857" stroke-width="3" opacity=".38" /></g>
      <text x="${plotX(targetHorizontalKm)}" y="${plotY(0.178)}" fill="#ffc857" text-anchor="middle" font-size="12">obiekt ${targetHorizontalKm.toFixed(1)} km</text>
      <text x="${PLOT_LEFT + 7}" y="${Math.max(PLOT_TOP + 16, observerY - 10)}" fill="#ff756a" font-size="12">obserwator</text>
      <text x="${PLOT_LEFT}" y="270" fill="#86a29f" font-size="12">0 km</text>
      <text x="${PLOT_RIGHT}" y="270" fill="#86a29f" text-anchor="end" font-size="12">${this.state.rangeKm.toFixed(1)} km</text>
      <text x="${PLOT_LEFT + 8}" y="${PLOT_TOP + 17}" fill="#86a29f" font-size="12">250 m</text>
    `;
  }

  private template(): string {
    return `
      <div class="atmosphere-heading">
        <div>
          <p class="eyebrow">Wariant eksperymentalny</p>
          <h2>Płaska powierzchnia + atmosfera warstwowa</h2>
        </div>
        <p id="atmosphere-status" class="atmosphere-status"></p>
      </div>
      <div class="atmosphere-layout">
        <svg id="atmosphere-svg" viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}" role="img" aria-label="Przekrój pionowy promieni w atmosferze warstwowej"></svg>
        <div class="atmosphere-controls">
          ${this.range('atmosphere-observer', 'Wysokość obserwatora', 0.5, 100, 0.5, this.state.observerHeightM)}
          ${this.range('atmosphere-refractivity', 'Refraktywność przy powierzchni', 0, 600, 5, this.state.surfaceRefractivityPpm)}
          ${this.range('atmosphere-scale-height', 'Skala pionowa', 0.05, 8, 0.05, this.state.scaleHeightKm)}
          ${this.range('atmosphere-extinction', 'Ekstynkcja przy powierzchni', 0, 0.5, 0.01, this.state.extinctionPerKm)}
          ${this.range('atmosphere-range', 'Zakres przekroju', 1, 30, 0.5, this.state.rangeKm)}
        </div>
      </div>
      <p class="model-note">Kolorowe punkty są fragmentami jednego pionowego obiektu. Strzałki pokazują informację optyczną biegnącą od obiektu do obserwatora; brak połączenia oznacza punkt niewidoczny w danym profilu. Tory przerywane oznaczają dodatkowe rozwiązania mirażowe. To model do przodu — bez dopasowania do konkretnego zdjęcia.</p>
    `;
  }

  private range(
    id: string,
    label: string,
    minimum: number,
    maximum: number,
    step: number,
    value: number,
  ): string {
    return `<label class="range-control" for="${id}"><span>${label}</span><output id="${id}-output" for="${id}">—</output><input id="${id}" type="range" min="${minimum}" max="${maximum}" step="${step}" value="${value}" /></label>`;
  }
}
