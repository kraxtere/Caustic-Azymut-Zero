import { DEFAULT_MODEL_STATE } from '../model/types';
import type { ComputedModel, ModelState, ViewOptions } from '../model/types';

type StateChangeHandler = (state: ModelState) => void;

interface CameraActions {
  top: () => void;
  perspective: () => void;
}

interface RangeBinding {
  input: HTMLInputElement;
  output: HTMLOutputElement;
  read: () => number;
  write: (value: number) => void;
  format: (value: number) => string;
}

function requiredElement<T extends HTMLElement>(
  root: ParentNode,
  selector: string,
): T {
  const element = root.querySelector<T>(selector);
  if (!element) throw new Error(`Brak elementu interfejsu: ${selector}`);
  return element;
}

function formatAngle(value: number): string {
  return `${value.toFixed(1)}°`;
}

export class ControlPanel {
  private state: ModelState;
  private readonly rangeBindings: RangeBinding[] = [];
  private readonly optionInputs = new Map<keyof ViewOptions, HTMLInputElement>();
  private readonly azimuthOutput: HTMLElement;
  private readonly elevationOutput: HTMLElement;
  private readonly sourceLongitudeOutput: HTMLElement;
  private readonly visibilityBadge: HTMLElement;

  constructor(
    private readonly root: HTMLElement,
    initialState: ModelState,
    private readonly onStateChange: StateChangeHandler,
    camera: CameraActions,
  ) {
    this.state = structuredClone(initialState);
    this.root.innerHTML = this.template();

    this.bindRange(
      '#observer-latitude',
      () => this.state.observer.latitudeDeg,
      (value) => (this.state.observer.latitudeDeg = value),
      formatAngle,
    );
    this.bindRange(
      '#observer-longitude',
      () => this.state.observer.longitudeDeg,
      (value) => (this.state.observer.longitudeDeg = value),
      formatAngle,
    );
    this.bindRange(
      '#source-declination',
      () => this.state.source.declinationDeg,
      (value) => (this.state.source.declinationDeg = value),
      formatAngle,
    );
    this.bindRange(
      '#source-hour-angle',
      () => this.state.source.hourAngleDeg,
      (value) => (this.state.source.hourAngleDeg = value),
      formatAngle,
    );
    this.bindRange(
      '#dome-height',
      () => this.state.domeHeightKm,
      (value) => (this.state.domeHeightKm = value),
      (value) => `${Math.round(value).toLocaleString('pl-PL')} km`,
    );
    this.bindRange(
      '#dome-scale',
      () => this.state.domeRadiusScale,
      (value) => (this.state.domeRadiusScale = value),
      (value) => `${value.toFixed(2)}×`,
    );
    this.bindRange(
      '#ray-parameter',
      () => this.state.rayParameter,
      (value) => (this.state.rayParameter = value),
      (value) => value.toFixed(2),
    );

    this.bindOption('showMapGrid');
    this.bindOption('showCoastline');
    this.bindOption('showDomeGrid');
    this.bindOption('showStraightComparison');
    this.bindOption('showRayTangent');

    this.azimuthOutput = requiredElement(this.root, '#result-azimuth');
    this.elevationOutput = requiredElement(this.root, '#result-elevation');
    this.sourceLongitudeOutput = requiredElement(this.root, '#result-longitude');
    this.visibilityBadge = requiredElement(this.root, '#visibility-badge');

    requiredElement<HTMLButtonElement>(this.root, '#view-top').addEventListener(
      'click',
      camera.top,
    );
    requiredElement<HTMLButtonElement>(this.root, '#view-perspective').addEventListener(
      'click',
      camera.perspective,
    );
    requiredElement<HTMLButtonElement>(this.root, '#reset-model').addEventListener(
      'click',
      () => {
        this.state = structuredClone(DEFAULT_MODEL_STATE);
        this.refreshInputs();
        this.emitChange();
      },
    );

    this.refreshInputs();
  }

  updateComputed(computed: ComputedModel): void {
    this.azimuthOutput.textContent = formatAngle(computed.horizontal.azimuthDeg);
    this.elevationOutput.textContent = formatAngle(computed.horizontal.elevationDeg);
    this.sourceLongitudeOutput.textContent = formatAngle(
      computed.sourceEarthFixedLongitudeDeg,
    );
    const isVisible = computed.horizontal.elevationDeg >= 0;
    this.visibilityBadge.textContent = isVisible
      ? 'źródło nad horyzontem'
      : 'źródło pod horyzontem';
    this.visibilityBadge.dataset.visible = String(isVisible);
  }

  private bindRange(
    selector: string,
    read: () => number,
    write: (value: number) => void,
    format: (value: number) => string,
  ): void {
    const input = requiredElement<HTMLInputElement>(this.root, selector);
    const output = requiredElement<HTMLOutputElement>(
      this.root,
      `output[for="${input.id}"]`,
    );
    const binding = { input, output, read, write, format };
    this.rangeBindings.push(binding);
    input.addEventListener('input', () => {
      const value = Number(input.value);
      write(value);
      output.value = format(value);
      this.emitChange();
    });
  }

  private bindOption(key: keyof ViewOptions): void {
    const input = requiredElement<HTMLInputElement>(
      this.root,
      `input[data-option="${key}"]`,
    );
    this.optionInputs.set(key, input);
    input.addEventListener('change', () => {
      this.state.view[key] = input.checked;
      this.emitChange();
    });
  }

  private refreshInputs(): void {
    for (const binding of this.rangeBindings) {
      const value = binding.read();
      binding.input.value = String(value);
      binding.output.value = binding.format(value);
    }
    for (const [key, input] of this.optionInputs) {
      input.checked = this.state.view[key];
    }
  }

  private emitChange(): void {
    this.onStateChange(structuredClone(this.state));
  }

  private template(): string {
    return `
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Parametry modelu</p>
          <h2>Stan obserwacji</h2>
        </div>
        <button class="icon-button" id="reset-model" type="button" title="Przywróć wartości początkowe" aria-label="Przywróć wartości początkowe">↺</button>
      </div>

      <section class="result-card" aria-live="polite">
        <div class="result-card__topline">
          <span>Wynik geometryczny</span>
          <span class="visibility-badge" id="visibility-badge"></span>
        </div>
        <dl class="result-grid">
          <div><dt>Azymut</dt><dd id="result-azimuth">—</dd></div>
          <div><dt>Elewacja</dt><dd id="result-elevation">—</dd></div>
          <div><dt>Długość źródła</dt><dd id="result-longitude">—</dd></div>
        </dl>
      </section>

      <fieldset>
        <legend>Obserwator</legend>
        ${this.rangeTemplate('observer-latitude', 'Szerokość geograficzna', -90, 90, 0.1)}
        ${this.rangeTemplate('observer-longitude', 'Długość geograficzna', -180, 180, 0.1)}
      </fieldset>

      <fieldset>
        <legend>Źródło na niebie</legend>
        ${this.rangeTemplate('source-declination', 'Deklinacja', -90, 90, 0.5)}
        ${this.rangeTemplate('source-hour-angle', 'Kąt godzinny', -180, 180, 0.5)}
        <p class="field-note">Ujemny kąt godzinny: źródło na wschód od południka. Dodatni: na zachód.</p>
      </fieldset>

      <fieldset>
        <legend>Konstrukcja bazowa</legend>
        ${this.rangeTemplate('dome-height', 'Wysokość kopuły', 2000, 20015, 100)}
        ${this.rangeTemplate('dome-scale', 'Promień kopuły', 1, 2.2, 0.01)}
        ${this.rangeTemplate('ray-parameter', 'Parametr krzywej', 0.5, 2, 0.01)}
      </fieldset>

      <fieldset>
        <legend>Warstwy</legend>
        <div class="toggle-grid">
          ${this.optionTemplate('showMapGrid', 'Siatka mapy')}
          ${this.optionTemplate('showCoastline', 'Linie lądów')}
          ${this.optionTemplate('showDomeGrid', 'Siatka kopuły')}
          ${this.optionTemplate('showStraightComparison', 'Tor prosty')}
          ${this.optionTemplate('showRayTangent', 'Kierunek pomiaru')}
        </div>
      </fieldset>

      <section class="camera-controls" aria-label="Widok kamery">
        <button id="view-perspective" type="button">Widok 3D</button>
        <button id="view-top" type="button">Widok z góry</button>
      </section>

      <p class="model-note">
        Różowy tor to konstrukcja Béziera Bislina — punkt zerowy do porównań, jeszcze bez pola toroidalnego.
      </p>
    `;
  }

  private rangeTemplate(
    id: string,
    label: string,
    min: number,
    max: number,
    step: number,
  ): string {
    return `
      <label class="range-control" for="${id}">
        <span>${label}</span>
        <output for="${id}">—</output>
        <input id="${id}" type="range" min="${min}" max="${max}" step="${step}" />
      </label>
    `;
  }

  private optionTemplate(key: keyof ViewOptions, label: string): string {
    return `
      <label class="toggle">
        <input type="checkbox" data-option="${key}" />
        <span aria-hidden="true"></span>
        ${label}
      </label>
    `;
  }
}
