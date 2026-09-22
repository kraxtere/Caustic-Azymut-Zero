import './styles.css';
import { mesh } from 'topojson-client';
import worldAtlas from 'world-atlas/countries-110m.json';
import { computeModel } from './model/compute';
import { stereographicRadiusForLatitude } from './model/conformal';
import { DEFAULT_MODEL_STATE } from './model/types';
import type { ModelState } from './model/types';
import { SceneController } from './scene/SceneController';
import { AtmospherePanel } from './ui/AtmospherePanel';
import { ControlPanel } from './ui/ControlPanel';
import { TrajectoryPanel } from './ui/TrajectoryPanel';

const app = document.querySelector<HTMLDivElement>('#app');
if (!app) throw new Error('Nie znaleziono kontenera aplikacji.');

app.innerHTML = `
  <main class="app-shell">
    <header class="app-header">
      <div class="brand-mark" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
      <div class="brand-copy">
        <p class="eyebrow">Laboratorium odwzorowania obserwacji</p>
        <h1>Caustic <span>Azymut Zero</span></h1>
      </div>
      <div class="baseline-pill" id="geometry-status"><i></i> geometria: inwersja 3D</div>
    </header>

    <nav class="mode-tabs" aria-label="Część laboratorium">
      <button type="button" class="mode-tab is-active" data-tab="global" aria-selected="true">Inwersja sferyczna</button>
      <button type="button" class="mode-tab" data-tab="atmosphere" aria-selected="false">Laboratorium refrakcji</button>
    </nav>

    <section class="workspace" id="global-panel">
      <div class="viewport-card">
        <canvas id="model-canvas" aria-label="Trójwymiarowa wizualizacja mapy, kopuły i toru promienia"></canvas>
        <div class="viewport-legend" aria-hidden="true">
          <span><i class="legend-observer"></i>obserwator</span>
          <span><i class="legend-source"></i>obiekt po inwersji</span>
          <span><i class="legend-direction"></i>lokalny kierunek</span>
          <span><i class="legend-connection"></i>powiązanie z kopułą</span>
          <span><i class="legend-ray"></i>tor transformacji</span>
          <span><i class="legend-terminator"></i>terminator</span>
        </div>
        <div class="viewport-hint">przeciągnij, aby obrócić · kółko/pinch, aby zbliżyć</div>
        <div class="time-console" aria-label="Sterowanie czasem">
          <button type="button" id="time-back" title="Cofnij o dobę">−1d</button>
          <button type="button" id="time-play" class="time-play" aria-pressed="false">▶ Odtwórz</button>
          <button type="button" id="time-forward" title="Przesuń o dobę">+1d</button>
          <select id="time-speed" aria-label="Prędkość animacji">
            <option value="1">1 h/s</option><option value="6">6 h/s</option>
            <option value="24" selected>1 dzień/s</option><option value="168">1 tydzień/s</option>
          </select>
        </div>
      </div>
      <aside class="control-panel" id="control-panel"></aside>
    </section>

    <section class="catalogue-table-card" id="catalogue-table-card">
      <div class="catalogue-table-heading">
        <div><p class="eyebrow">Wspólna transformacja</p><h2>Położenie i skala obiektów</h2></div>
        <p>Wartości źródłowe i wynik po inwersji, liczone względem centrum mapy.</p>
      </div>
      <div class="table-scroll">
        <table class="object-table">
          <thead><tr><th>Obiekt</th><th>Rodzaj</th><th>Odległość źródłowa</th><th>Średnica rzeczywista</th><th>Δ∞</th><th>Od centrum mapy</th><th>Średnica po inwersji</th></tr></thead>
          <tbody id="object-table-body"></tbody>
        </table>
      </div>
    </section>

    <section class="diagnostic-grid" id="diagnostic-grid">
      <article class="diagnostic-card">
        <div class="diagnostic-heading"><div><p class="eyebrow">Powiększenie osobliwości</p><h2>Otoczenie P∞</h2></div><span>promień logarytmiczny</span></div>
        <svg id="compactification-svg" viewBox="0 0 900 300" role="img" aria-label="Logarytmiczne powiększenie położeń obiektów wokół punktu nieskończoności"></svg>
        <p>Środek to <strong>P∞=(0,0,2R)</strong>. Kierunek jest zachowany, lecz promień został rozciągnięty logarytmicznie wyłącznie dla czytelności.</p>
      </article>
      <article class="diagnostic-card">
        <div class="diagnostic-heading"><div><p class="eyebrow">Dwie różne geometrie</p><h2>Stereograficzna a AE</h2></div><span>bez mieszania torów</span></div>
        <canvas id="projection-comparison" width="900" height="300" aria-label="Porównanie rzutu stereograficznego i azymutalnego równodystansowego"></canvas>
        <p>Po lewej powierzchnia ścisłej inwersji. Po prawej klasyczna mapa azymutalna równodystansowa — pokazana wyłącznie kartograficznie.</p>
      </article>
    </section>

    <section id="trajectory-panel"></section>

    <section class="atmosphere-lab" id="atmosphere-lab" hidden></section>

    <footer class="app-footer">
      <span>V10 · tory dwuczęściowe i zsynchronizowane trajektorie planet</span>
      <a href="https://walter.bislins.ch/bloge/index.asp?page=Source+Code%3A+FE%2DDome+App" target="_blank" rel="noreferrer">oryginalny kod ↗</a>
    </footer>
  </main>
`;

const canvas = document.querySelector<HTMLCanvasElement>('#model-canvas');
const panelRoot = document.querySelector<HTMLElement>('#control-panel');
const atmosphereRoot = document.querySelector<HTMLElement>('#atmosphere-lab');
const geometryStatus = document.querySelector<HTMLElement>('#geometry-status');
if (!canvas || !panelRoot || !atmosphereRoot || !geometryStatus) {
  throw new Error('Nie udało się zbudować interfejsu.');
}
const geometryStatusElement = geometryStatus;
const objectTableBody = document.querySelector<HTMLTableSectionElement>('#object-table-body')!;
const catalogueTableCard = document.querySelector<HTMLElement>('#catalogue-table-card')!;
const diagnosticGrid = document.querySelector<HTMLElement>('#diagnostic-grid')!;
const compactificationSvg = document.querySelector<SVGSVGElement>('#compactification-svg')!;
const projectionCanvas = document.querySelector<HTMLCanvasElement>('#projection-comparison')!;
const trajectoryRoot = document.querySelector<HTMLElement>('#trajectory-panel')!;

const scene = new SceneController(canvas);
let state: ModelState = structuredClone(DEFAULT_MODEL_STATE);
let panel: ControlPanel;
let trajectoryPanel: TrajectoryPanel;
let playing = false;
let lastAnimationTime = performance.now();

function update(nextState: ModelState): void {
  state = nextState;
  geometryStatusElement.innerHTML = state.geometryMode === 'conformal'
    ? '<i></i> geometria: inwersja 3D'
    : '<i></i> porównanie: FE-Dome';
  const computed = computeModel(state);
  scene.update(state, computed);
  panel?.updateComputed(computed);
  updateObjectTable(computed);
  updateCompactification(computed);
  trajectoryPanel?.updateState(state);
}

panel = new ControlPanel(panelRoot, state, update, {
  top: () => scene.setTopView(),
  perspective: () => scene.setPerspectiveView(),
  observer: () => scene.setObserverView(),
});
new AtmospherePanel(atmosphereRoot);
trajectoryPanel = new TrajectoryPanel(trajectoryRoot, state);

for (const button of document.querySelectorAll<HTMLButtonElement>('.mode-tab')) {
  button.addEventListener('click', () => {
    const global = button.dataset.tab === 'global';
    document.querySelector<HTMLElement>('#global-panel')!.hidden = !global;
    catalogueTableCard.hidden = !global || state.geometryMode !== 'conformal';
    diagnosticGrid.hidden = !global || state.geometryMode !== 'conformal';
    trajectoryRoot.hidden = !global || state.geometryMode !== 'conformal';
    atmosphereRoot.hidden = global;
    for (const candidate of document.querySelectorAll<HTMLButtonElement>('.mode-tab')) {
      const active = candidate === button;
      candidate.classList.toggle('is-active', active);
      candidate.setAttribute('aria-selected', String(active));
    }
  });
}

const playButton = document.querySelector<HTMLButtonElement>('#time-play')!;
const speedSelect = document.querySelector<HTMLSelectElement>('#time-speed')!;
function shiftTime(hours: number): void {
  const date = new Date(`${state.sunUtc}:00Z`);
  date.setTime(date.getTime() + hours * 3_600_000);
  state.sunUtc = date.toISOString().slice(0, 16);
  panel.syncState(state);
  update(state);
}
document.querySelector<HTMLButtonElement>('#time-back')!.addEventListener('click', () => shiftTime(-24));
document.querySelector<HTMLButtonElement>('#time-forward')!.addEventListener('click', () => shiftTime(24));
playButton.addEventListener('click', () => {
  playing = !playing;
  playButton.setAttribute('aria-pressed', String(playing));
  playButton.textContent = playing ? '❚❚ Pauza' : '▶ Odtwórz';
  lastAnimationTime = performance.now();
});
function animateTime(now: number): void {
  if (playing && now - lastAnimationTime >= 120) {
    const elapsedSeconds = (now - lastAnimationTime) / 1000;
    shiftTime(Number(speedSelect.value) * elapsedSeconds);
    lastAnimationTime = now;
  }
  requestAnimationFrame(animateTime);
}
requestAnimationFrame(animateTime);

function updateObjectTable(computed: ReturnType<typeof computeModel>): void {
  catalogueTableCard.hidden = state.geometryMode !== 'conformal';
  diagnosticGrid.hidden = state.geometryMode !== 'conformal';
  const kind: Record<string, string> = { sun: 'gwiazda', moon: 'księżyc', planet: 'planeta', star: 'gwiazda' };
  objectTableBody.innerHTML = (computed.conformalObjects ?? []).map((object) => {
    const transformedDistance = Math.hypot(object.imageCentreMath.x, object.imageCentreMath.y, object.imageCentreMath.z);
    const selected = object.id === state.selectedObject ? ' class="is-selected"' : '';
    return `<tr${selected} data-object-row="${object.id}">
      <th><button type="button" data-select-object="${object.id}">${object.name}</button></th>
      <td>${kind[object.kind] ?? object.kind}</td>
      <td>${formatDistance(object.distanceKm)}</td>
      <td>${formatDiameter(object.sourceRadiusKm * 2)}</td>
      <td class="delta-cell">${formatDiameter(object.distanceFromInfinityKm)}</td>
      <td>${formatDistance(transformedDistance)}</td>
      <td>${formatDiameter(object.imageRadiusKm * 2)}</td>
    </tr>`;
  }).join('');
  for (const button of objectTableBody.querySelectorAll<HTMLButtonElement>('[data-select-object]')) {
    button.addEventListener('click', () => {
      state.selectedObject = button.dataset.selectObject as ModelState['selectedObject'];
      panel.syncState(state); update(state);
    });
  }
}

const OBJECT_COLOURS: Record<string, string> = {
  sun:'#ffd15c', moon:'#dde8ed', mercury:'#b9b1a6', venus:'#ffbd73', mars:'#ff684f',
  jupiter:'#e8b98d', saturn:'#f4dc91', uranus:'#76dce8', neptune:'#5d85ff', polaris:'#e8f3ff',
  sirius:'#aed8ff', vega:'#cbdfff', betelgeuse:'#ff9a62', 'alpha-centauri':'#ffe0a6',
};

function updateCompactification(computed: ReturnType<typeof computeModel>): void {
  const objects = computed.conformalObjects ?? [];
  if (!objects.length) { compactificationSvg.innerHTML = ''; return; }
  const logs = objects.map((object) => Math.log10(Math.max(object.distanceFromInfinityKm, 1e-15)));
  const min = Math.min(...logs); const max = Math.max(...logs); const span = Math.max(max - min, 1);
  const cx = 450; const cy = 150;
  const circles = [32, 72, 112].map((r) => `<circle cx="${cx}" cy="${cy}" r="${r}" class="compact-ring"/>`).join('');
  const points = objects.map((object, index) => {
    const log = logs[index]!;
    const radius = 28 + 100 * ((log - min) / span);
    const angle = Math.atan2(object.imageCentreMath.y, object.imageCentreMath.x);
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    const selected = object.id === state.selectedObject;
    return `<g class="compact-object${selected ? ' is-selected' : ''}">
      <line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}"/>
      <circle cx="${x}" cy="${y}" r="${selected ? 8 : 5}" fill="${OBJECT_COLOURS[object.id] ?? '#fff'}"/>
      <text x="${x + 10}" y="${y - 8}">${object.name}</text>
    </g>`;
  }).join('');
  compactificationSvg.innerHTML = `${circles}<circle cx="${cx}" cy="${cy}" r="5" class="compact-centre"/><text x="${cx + 12}" y="${cy + 5}" class="compact-pinf">P∞</text>${points}`;
}

function drawProjectionComparison(): void {
  const context = projectionCanvas.getContext('2d')!;
  const width = projectionCanvas.width; const height = projectionCanvas.height;
  context.clearRect(0, 0, width, height);
  const topology = worldAtlas as unknown as { objects: { land: unknown } };
  const coast = mesh(worldAtlas as never, topology.objects.land as never) as unknown as { coordinates:number[][][] };
  const panels = [
    { cx:225, label:'STEREOGRAFICZNA · ścisła inwersja', project:(lat:number,lon:number) => ({ r:stereographicRadiusForLatitude(lat), a:(lon-90)*Math.PI/180 }), max:stereographicRadiusForLatitude(-60) },
    { cx:675, label:'AE · równodystansowa', project:(lat:number,lon:number) => ({ r:((90-lat)/180)*20_015, a:(lon-90)*Math.PI/180 }), max:20_015 },
  ];
  for (const panel of panels) {
    const scale = 126 / panel.max;
    context.strokeStyle='rgba(101,210,203,.28)'; context.lineWidth=1;
    context.beginPath(); context.arc(panel.cx,155,126,0,Math.PI*2); context.stroke();
    context.fillStyle='#b9d3d8'; context.font='600 13px Inter, sans-serif'; context.textAlign='center'; context.fillText(panel.label,panel.cx,20);
    context.strokeStyle='rgba(150,218,201,.82)'; context.lineWidth=1.15;
    for (const line of coast.coordinates) {
      context.beginPath(); let started=false; let previous:{x:number;y:number}|undefined;
      for (const [lon=0,lat=0] of line) {
        if (panel.cx===225 && lat < -60) { started=false; previous=undefined; continue; }
        const polar=panel.project(lat,lon); const point={x:panel.cx+Math.cos(polar.a)*polar.r*scale,y:155+Math.sin(polar.a)*polar.r*scale};
        if (!started || (previous && Math.hypot(point.x-previous.x,point.y-previous.y)>55)) context.moveTo(point.x,point.y); else context.lineTo(point.x,point.y);
        started=true; previous=point;
      }
      context.stroke();
    }
  }
}

drawProjectionComparison();
update(state);

function formatDistance(km: number): string {
  const ly = 9.4607304725808e12;
  if (km >= ly * 0.1) return `${(km / ly).toLocaleString('pl-PL', { maximumFractionDigits: 3 })} ly`;
  if (km >= 100_000_000) return `${(km / 149_597_870.7).toLocaleString('pl-PL', { maximumFractionDigits: 4 })} AU`;
  if (km < 1) return `${(km * 1000).toPrecision(4)} m`;
  return `${km.toLocaleString('pl-PL', { maximumFractionDigits: 1 })} km`;
}

function formatDiameter(km: number): string {
  if (km < 1e-6) return `${(km * 1e9).toPrecision(4)} mm`;
  if (km < 0.001) return `${(km * 1e6).toPrecision(4)} mm`;
  if (km < 1) return `${(km * 1000).toPrecision(4)} m`;
  return `${km.toLocaleString('pl-PL', { maximumFractionDigits: 2 })} km`;
}

window.addEventListener('beforeunload', () => { scene.dispose(); trajectoryPanel.dispose(); }, { once: true });
