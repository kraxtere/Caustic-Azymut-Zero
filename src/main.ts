import './styles.css';
import { computeModel } from './model/compute';
import { DEFAULT_MODEL_STATE } from './model/types';
import type { ModelState } from './model/types';
import { SceneController } from './scene/SceneController';
import { ControlPanel } from './ui/ControlPanel';

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
      <div class="baseline-pill"><i></i> baza: FE-Dome</div>
    </header>

    <section class="workspace">
      <div class="viewport-card">
        <canvas id="model-canvas" aria-label="Trójwymiarowa wizualizacja mapy, kopuły i toru promienia"></canvas>
        <div class="viewport-legend" aria-hidden="true">
          <span><i class="legend-observer"></i>obserwator</span>
          <span><i class="legend-source"></i>źródło</span>
          <span><i class="legend-ray"></i>tor bazowy</span>
        </div>
        <div class="viewport-hint">przeciągnij, aby obrócić · kółko/pinch, aby zbliżyć</div>
      </div>
      <aside class="control-panel" id="control-panel"></aside>
    </section>

    <footer class="app-footer">
      <span>Etap 0 · fundament matematyczny i wizualny</span>
      <a href="https://walter.bislins.ch/bloge/index.asp?page=Source+Code%3A+FE%2DDome+App" target="_blank" rel="noreferrer">oryginalny kod ↗</a>
    </footer>
  </main>
`;

const canvas = document.querySelector<HTMLCanvasElement>('#model-canvas');
const panelRoot = document.querySelector<HTMLElement>('#control-panel');
if (!canvas || !panelRoot) throw new Error('Nie udało się zbudować interfejsu.');

const scene = new SceneController(canvas);
let state: ModelState = structuredClone(DEFAULT_MODEL_STATE);
let panel: ControlPanel;

function update(nextState: ModelState): void {
  state = nextState;
  const computed = computeModel(state);
  scene.update(state, computed);
  panel?.updateComputed(computed);
}

panel = new ControlPanel(panelRoot, state, update, {
  top: () => scene.setTopView(),
  perspective: () => scene.setPerspectiveView(),
});

update(state);

window.addEventListener('beforeunload', () => scene.dispose(), { once: true });
