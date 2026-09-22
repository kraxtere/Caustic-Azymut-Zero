import { DEFAULT_MODEL_STATE } from '../model/types';
import { OBJECT_OPTIONS } from '../model/celestial';
import type { ComputedModel, ModelState, ObjectId, ViewOptions } from '../model/types';

type StateChangeHandler = (state: ModelState) => void;

interface CameraActions {
  top: () => void;
  perspective: () => void;
  observer: () => void;
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
  private readonly sunDistanceOutput: HTMLElement;
  private readonly sunImageHeightOutput: HTMLElement;
  private readonly sunImageDiameterOutput: HTMLElement;
  private readonly sunIndexOutput: HTMLElement;
  private readonly objectNameOutput: HTMLElement;
  private readonly sourceDistanceOutput: HTMLElement;
  private readonly mappedDistanceOutput: HTMLElement;
  private readonly angularSizeOutput: HTMLElement;
  private readonly provenanceOutput: HTMLElement;
  private readonly logDistanceMarker: HTMLElement;

  constructor(
    private readonly root: HTMLElement,
    initialState: ModelState,
    private readonly onStateChange: StateChangeHandler,
    camera: CameraActions,
  ) {
    this.state = structuredClone(initialState);
    this.root.innerHTML = this.template();

    const geometryMode = requiredElement<HTMLSelectElement>(this.root, '#geometry-mode');
    geometryMode.addEventListener('change', () => {
      this.state.geometryMode = geometryMode.value as ModelState['geometryMode'];
      this.refreshInputs();
      this.emitChange();
    });
    const sunUtc = requiredElement<HTMLInputElement>(this.root, '#sun-utc');
    sunUtc.addEventListener('input', () => {
      this.state.sunUtc = sunUtc.value;
      this.emitChange();
    });
    const objectSelect = requiredElement<HTMLSelectElement>(this.root, '#object-select');
    objectSelect.addEventListener('change', () => {
      this.state.selectedObject = objectSelect.value as ObjectId;
      if (!this.state.visibleObjectIds.includes(this.state.selectedObject)) {
        this.state.visibleObjectIds.push(this.state.selectedObject);
      }
      this.refreshObjectVisibility();
      this.emitChange();
    });
    for (const input of this.root.querySelectorAll<HTMLInputElement>('[data-object-visible]')) {
      input.addEventListener('change', () => {
        const id = input.dataset.objectVisible as ObjectId;
        this.state.visibleObjectIds = input.checked
          ? [...new Set([...this.state.visibleObjectIds, id])]
          : this.state.visibleObjectIds.filter((candidate) => candidate !== id);
        if (this.state.visibleObjectIds.length === 0) {
          this.state.visibleObjectIds = [this.state.selectedObject];
        }
        this.refreshObjectVisibility();
        this.emitChange();
      });
    }

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
      '#observer-dome-radius',
      () => this.state.observerDomeRadiusKm,
      (value) => (this.state.observerDomeRadiusKm = value),
      (value) => `${Math.round(value).toLocaleString('pl-PL')} km`,
    );
    this.bindRange(
      '#straight-ray-boundary',
      () => this.state.straightRayBoundaryKm,
      (value) => (this.state.straightRayBoundaryKm = value),
      (value) => `${Math.round(value).toLocaleString('pl-PL')} km`,
    );
    this.bindRange(
      '#object-visual-scale',
      () => this.state.objectVisualScale,
      (value) => (this.state.objectVisualScale = value),
      (value) => `${value.toFixed(1)}×`,
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
    this.bindOption('showTerminator');
    this.bindOption('showDirectionDome');
    this.bindOption('showPhysicalSun');
    this.bindOption('showTransformedPath');
    this.bindOption('showConnectionLines');

    for (const input of this.root.querySelectorAll<HTMLInputElement>('[data-observer-enabled]')) {
      input.addEventListener('change', () => {
        const observer = this.state.auxiliaryObservers.find(({ id }) => id === input.dataset.observerEnabled);
        if (observer) observer.enabled = input.checked;
        this.emitChange();
      });
    }
    for (const input of this.root.querySelectorAll<HTMLInputElement>('[data-observer-coordinate]')) {
      input.addEventListener('change', () => {
        const observer = this.state.auxiliaryObservers.find(({ id }) => id === input.dataset.observerId);
        if (!observer) return;
        const key = input.dataset.observerCoordinate as keyof typeof observer.coordinate;
        observer.coordinate[key] = Number(input.value);
        this.emitChange();
      });
    }

    this.azimuthOutput = requiredElement(this.root, '#result-azimuth');
    this.elevationOutput = requiredElement(this.root, '#result-elevation');
    this.sourceLongitudeOutput = requiredElement(this.root, '#result-longitude');
    this.visibilityBadge = requiredElement(this.root, '#visibility-badge');
    this.sunDistanceOutput = requiredElement(this.root, '#sun-distance');
    this.sunImageHeightOutput = requiredElement(this.root, '#sun-image-height');
    this.sunImageDiameterOutput = requiredElement(this.root, '#sun-image-diameter');
    this.sunIndexOutput = requiredElement(this.root, '#sun-index');
    this.objectNameOutput = requiredElement(this.root, '#object-name');
    this.sourceDistanceOutput = requiredElement(this.root, '#source-distance');
    this.mappedDistanceOutput = requiredElement(this.root, '#mapped-distance');
    this.angularSizeOutput = requiredElement(this.root, '#angular-size');
    this.provenanceOutput = requiredElement(this.root, '#object-provenance');
    this.logDistanceMarker = requiredElement(this.root, '#log-distance-marker');

    requiredElement<HTMLButtonElement>(this.root, '#view-top').addEventListener(
      'click',
      camera.top,
    );
    requiredElement<HTMLButtonElement>(this.root, '#view-perspective').addEventListener(
      'click',
      camera.perspective,
    );
    requiredElement<HTMLButtonElement>(this.root, '#view-observer').addEventListener(
      'click',
      camera.observer,
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
    const sun = computed.conformalSun;
    const object = computed.conformalObject;
    requiredElement<HTMLElement>(this.root, '#result-longitude-label').textContent = sun
      ? 'Długość podsłoneczna'
      : 'Długość źródła';
    this.sunDistanceOutput.textContent = object ? formatDistance(object.distanceKm) : '—';
    this.sunImageHeightOutput.textContent = object
      ? `${object.imageCentreMath.z.toLocaleString('pl-PL', { maximumFractionDigits: 3 })} km`
      : '—';
    this.sunImageDiameterOutput.textContent = object
      ? formatMappedSize(object.imageRadiusKm * 2)
      : '—';
    this.sunIndexOutput.textContent = sun
      ? sun.scalarIndex.toExponential(3)
      : object ? object.scalarIndex.toExponential(3) : '—';
    this.objectNameOutput.textContent = object?.name ?? '—';
    this.sourceDistanceOutput.textContent = object
      ? formatDistance(object.distanceKm)
      : '—';
    this.mappedDistanceOutput.textContent = object
      ? formatMappedDistance(object.distanceFromInfinityKm)
      : '—';
    this.angularSizeOutput.textContent = object
      ? `${(object.angularRadiusDeg * 2).toPrecision(4)}°`
      : '—';
    this.provenanceOutput.textContent = object?.provenance ?? '—';
    this.logDistanceMarker.style.left = `${(object?.logDistanceFraction ?? 0) * 100}%`;
  }

  syncState(nextState: ModelState): void {
    this.state = structuredClone(nextState);
    this.refreshInputs();
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
    requiredElement<HTMLSelectElement>(this.root, '#geometry-mode').value =
      this.state.geometryMode;
    requiredElement<HTMLInputElement>(this.root, '#sun-utc').value = this.state.sunUtc;
    requiredElement<HTMLSelectElement>(this.root, '#object-select').value =
      this.state.selectedObject;
    for (const element of this.root.querySelectorAll<HTMLElement>('[data-mode-section]')) {
      const mode = element.dataset.modeSection;
      element.hidden = mode !== this.state.geometryMode;
    }
    for (const binding of this.rangeBindings) {
      const value = binding.read();
      binding.input.value = String(value);
      binding.output.value = binding.format(value);
    }
    for (const [key, input] of this.optionInputs) {
      input.checked = this.state.view[key];
    }
    for (const input of this.root.querySelectorAll<HTMLInputElement>('[data-observer-enabled]')) {
      input.checked = this.state.auxiliaryObservers.find(({ id }) => id === input.dataset.observerEnabled)?.enabled ?? false;
    }
    for (const input of this.root.querySelectorAll<HTMLInputElement>('[data-observer-coordinate]')) {
      const observer = this.state.auxiliaryObservers.find(({ id }) => id === input.dataset.observerId);
      if (observer) input.value = String(observer.coordinate[input.dataset.observerCoordinate as keyof typeof observer.coordinate]);
    }
    this.refreshObjectVisibility();
  }

  private refreshObjectVisibility(): void {
    for (const input of this.root.querySelectorAll<HTMLInputElement>('[data-object-visible]')) {
      input.checked = this.state.visibleObjectIds.includes(input.dataset.objectVisible as ObjectId);
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
          <div><dt id="result-longitude-label">Długość źródła</dt><dd id="result-longitude">—</dd></div>
        </dl>
      </section>

      <fieldset>
        <legend>Geometria</legend>
        <label class="select-control" for="geometry-mode">
          <span>Tryb odwzorowania</span>
          <select id="geometry-mode">
            <option value="conformal">Dokładna inwersja 3D</option>
            <option value="fe-dome">FE-Dome — porównanie</option>
          </select>
        </label>
      </fieldset>

      <section data-mode-section="conformal">
        <fieldset>
          <legend>Katalog nieba i czas</legend>
          <label class="select-control" for="object-select">
            <span>Obiekt źródłowy</span>
            <select id="object-select">
              ${OBJECT_OPTIONS.map(({ id, label }) => `<option value="${id}">${label}</option>`).join('')}
            </select>
          </label>
          <details class="catalogue-picker" open>
            <summary>Obiekty wyświetlane jednocześnie</summary>
            <div class="catalogue-grid">
              ${OBJECT_OPTIONS.map(({ id, label }) => `<label><input type="checkbox" data-object-visible="${id}" /><span></span>${label}</label>`).join('')}
            </div>
          </details>
          <label class="date-control" for="sun-utc">
            <span>Data i czas UTC</span>
            <input id="sun-utc" type="datetime-local" step="60" />
          </label>
          <section class="object-card">
            <div class="object-card__title"><span id="object-name">—</span><small id="object-provenance">—</small></div>
            <dl class="object-results">
              <div><dt>Odległość źródłowa</dt><dd id="source-distance">—</dd></div>
              <div><dt>Od obrazu nieskończoności</dt><dd id="mapped-distance">—</dd></div>
              <div><dt>Średnica kątowa</dt><dd id="angular-size">—</dd></div>
            </dl>
            <div class="distance-ruler" aria-label="Logarytmiczna pozycja od Księżyca do odległych gwiazd">
              <span>Księżyc</span><i><b id="log-distance-marker"></b></i><span>gwiazdy</span>
            </div>
          </section>
          <dl class="inversion-results">
            <div><dt>Odległość źródłowa</dt><dd id="sun-distance">—</dd></div>
            <div><dt>Wysokość obrazu</dt><dd id="sun-image-height">—</dd></div>
            <div><dt>Średnica po inwersji</dt><dd id="sun-image-diameter">—</dd></div>
            <div><dt>Wymagane n</dt><dd id="sun-index">—</dd></div>
          </dl>
          <p class="field-note">Żółty punkt jest znacznikiem ekranowym. Położenie i rozmiar fizycznej kuli wynikają wyłącznie z jednej transformacji.</p>
        </fieldset>

        <fieldset>
          <legend>Kopuły obserwacji</legend>
          ${this.rangeTemplate('observer-dome-radius', 'Promień kopuły widzenia', 3000, 9000, 100)}
          ${this.rangeTemplate('straight-ray-boundary', 'Granica prostego odcinka', 500, 9000, 100)}
          <div class="observer-list">
            ${this.observerTemplate('north', 'Obserwator północny')}
            ${this.observerTemplate('south', 'Obserwator południowy')}
          </div>
          <p class="field-note">Granica prostego odcinka jest na razie parametrem prezentacyjnym. Tor jest krzywy do tej granicy, a dalej biegnie prosto do oka.</p>
        </fieldset>

        <fieldset>
          <legend>Skala prezentacji</legend>
          ${this.rangeTemplate('object-visual-scale', 'Powiększenie brył obiektów', 0.5, 8, 0.5)}
          <p class="field-note">Zmienia wyłącznie wielkość rysowanych brył. Wartości w tabeli pozostają fizyczne.</p>
        </fieldset>
      </section>

      <fieldset>
        <legend>Obserwator</legend>
        ${this.rangeTemplate('observer-latitude', 'Szerokość geograficzna', -90, 90, 0.1)}
        ${this.rangeTemplate('observer-longitude', 'Długość geograficzna', -180, 180, 0.1)}
      </fieldset>

      <fieldset data-mode-section="fe-dome">
        <legend>Źródło na niebie</legend>
        ${this.rangeTemplate('source-declination', 'Deklinacja', -90, 90, 0.5)}
        ${this.rangeTemplate('source-hour-angle', 'Kąt godzinny', -180, 180, 0.5)}
        <p class="field-note">Ujemny kąt godzinny: źródło na wschód od południka. Dodatni: na zachód.</p>
      </fieldset>

      <fieldset data-mode-section="fe-dome">
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
          ${this.optionTemplate('showStraightComparison', 'Tor prosty', 'fe-dome')}
          ${this.optionTemplate('showRayTangent', 'Kierunek pomiaru', 'fe-dome')}
          ${this.optionTemplate('showTerminator', 'Terminator i dzień', 'conformal')}
          ${this.optionTemplate('showDirectionDome', 'Kopuła kierunkowa', 'conformal')}
          ${this.optionTemplate('showPhysicalSun', 'Obiekt po inwersji', 'conformal')}
          ${this.optionTemplate('showTransformedPath', 'Dokładny tor transformacji', 'conformal')}
          ${this.optionTemplate('showConnectionLines', 'Krzywe bazowej inwersji', 'conformal')}
        </div>
      </fieldset>

      <section class="camera-controls" aria-label="Widok kamery">
        <button id="view-perspective" type="button">Widok 3D</button>
        <button id="view-top" type="button">Widok z góry</button>
        <button id="view-observer" type="button">Z wnętrza kopuły</button>
      </section>

      <p class="model-note" data-mode-section="conformal">
        Pozycja, rozmiar i tor każdego obiektu wynikają z jednej transformacji 3D. Kopuła pokazuje punkt przecięcia toru i jego styczną. Łuki analityczne obowiązują tylko w trybie bazowej inwersji bez dipola i bez propagatora numerycznego. Widok powierzchni kończy się na 60°S, ponieważ biegun południowy tej inwersji leży w nieskończoności.
      </p>
      <p class="model-note" data-mode-section="fe-dome">
        Różowy tor to konstrukcja Béziera Bislina — zachowana wyłącznie jako historyczny punkt odniesienia.
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

  private optionTemplate(
    key: keyof ViewOptions,
    label: string,
    mode?: ModelState['geometryMode'],
  ): string {
    return `
      <label class="toggle"${mode ? ` data-mode-section="${mode}"` : ''}>
        <input type="checkbox" data-option="${key}" />
        <span aria-hidden="true"></span>
        ${label}
      </label>
    `;
  }

  private observerTemplate(id: 'north' | 'south', label: string): string {
    return `
      <section class="observer-config">
        <label class="observer-toggle"><input type="checkbox" data-observer-enabled="${id}" /> ${label}</label>
        <label>φ <input type="number" min="-89" max="89" step="1" data-observer-id="${id}" data-observer-coordinate="latitudeDeg" /></label>
        <label>λ <input type="number" min="-180" max="180" step="1" data-observer-id="${id}" data-observer-coordinate="longitudeDeg" /></label>
      </section>`;
  }
}

function formatDistance(km: number): string {
  const lightYearKm = 9.4607304725808e12;
  if (km >= lightYearKm * 0.1) return `${(km / lightYearKm).toLocaleString('pl-PL', { maximumFractionDigits: 3 })} ly`;
  if (km >= 100_000_000) return `${(km / 149_597_870.7).toLocaleString('pl-PL', { maximumFractionDigits: 6 })} AU`;
  return `${Math.round(km).toLocaleString('pl-PL')} km`;
}

function formatMappedDistance(km: number): string {
  if (km < 0.001) return `${(km * 1_000_000).toPrecision(4)} mm`;
  if (km < 1) return `${(km * 1_000).toPrecision(4)} m`;
  return `${km.toLocaleString('pl-PL', { maximumFractionDigits: 3 })} km`;
}

function formatMappedSize(km: number): string {
  if (km < 1e-6) return `${(km * 1e9).toPrecision(4)} mm`;
  if (km < 0.001) return `${(km * 1e6).toPrecision(4)} mm`;
  if (km < 1) return `${(km * 1e3).toPrecision(4)} m`;
  return `${km.toLocaleString('pl-PL', { maximumFractionDigits: 4 })} km`;
}
