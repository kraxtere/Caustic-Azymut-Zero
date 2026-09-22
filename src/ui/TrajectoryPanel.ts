import { PLANET_IDS, SYNODIC_DAYS, planetTrajectoryFrame } from '../model/celestial';
import type { PlanetId, PlanetTrajectoryFrame } from '../model/celestial';
import type { ModelState, Vec3 } from '../model/types';

const COLOURS: Record<PlanetId, string> = {
  mercury:'#b9b1a6', venus:'#ffbd73', mars:'#ff684f', jupiter:'#e8b98d',
  saturn:'#f4dc91', uranus:'#76dce8', neptune:'#5d85ff',
};

type RangeMode = 'year' | 'years' | 'synodic';
type DrawMode = 'full' | 'progressive';

interface Track { id: PlanetId; name: string; frames: PlanetTrajectoryFrame[]; }

export class TrajectoryPanel {
  private state: ModelState;
  private rangeMode: RangeMode = 'years';
  private drawMode: DrawMode = 'full';
  private phase = 0;
  private playing = false;
  private speed = 1;
  private tracks: Track[] = [];
  private cacheKey = '';
  private lastFrame = performance.now();
  private animationFrame = 0;

  constructor(private readonly root: HTMLElement, initialState: ModelState) {
    this.state = structuredClone(initialState);
    this.root.innerHTML = this.template();
    this.bind();
    this.rebuild();
    this.animationFrame = requestAnimationFrame(this.animate);
  }

  updateState(state: ModelState): void {
    this.state = structuredClone(state);
    this.rebuild();
  }

  dispose(): void { cancelAnimationFrame(this.animationFrame); }

  private template(): string {
    return `<details class="trajectory-lab" open>
      <summary><span><small>Ruch w czasie</small>Trajektorie planet w trzech geometriach</span><b>rozwiń / zwiń</b></summary>
      <div class="trajectory-body">
        <div class="trajectory-toolbar">
          <label>Zakres czasu<select id="trajectory-range"><option value="year">1 rok</option><option value="years" selected>5 lat</option><option value="synodic">cykl synodyczny</option></select></label>
          <label>Prędkość<select id="trajectory-speed"><option value="0.25">0,25×</option><option value="1" selected>1×</option><option value="4">4×</option><option value="12">12×</option></select></label>
          <label>Rysowanie<select id="trajectory-mode"><option value="full">cała ścieżka</option><option value="progressive">narastająco</option></select></label>
          <button type="button" id="trajectory-play">▶ Odtwórz</button>
        </div>
        <div class="trajectory-timeline"><input id="trajectory-phase" type="range" min="0" max="1000" value="0" step="1"><output id="trajectory-date">—</output></div>
        <p class="trajectory-note" id="trajectory-note"></p>
        <div class="trajectory-grid">
          ${this.canvasCard('geo', 'Geocentryczny', 'Ziemia w środku · pętle ruchu wstecznego')}
          ${this.canvasCard('helio', 'Heliocentryczny', 'Słońce w środku · orbity Keplera')}
          ${this.canvasCard('inverse', 'Po inwersji półsferycznej', 'P∞ w środku · promień logarytmiczny')}
        </div>
      </div>
    </details>`;
  }

  private canvasCard(id: string, title: string, subtitle: string): string {
    return `<details class="trajectory-card" open><summary><span>${title}<small>${subtitle}</small></span></summary><canvas id="trajectory-${id}" width="720" height="460"></canvas></details>`;
  }

  private bind(): void {
    this.root.querySelector<HTMLSelectElement>('#trajectory-range')!.addEventListener('change', (event) => {
      this.rangeMode = (event.target as HTMLSelectElement).value as RangeMode; this.phase = 0; this.rebuild(true);
    });
    this.root.querySelector<HTMLSelectElement>('#trajectory-speed')!.addEventListener('change', (event) => {
      this.speed = Number((event.target as HTMLSelectElement).value);
    });
    this.root.querySelector<HTMLSelectElement>('#trajectory-mode')!.addEventListener('change', (event) => {
      this.drawMode = (event.target as HTMLSelectElement).value as DrawMode; this.draw();
    });
    this.root.querySelector<HTMLButtonElement>('#trajectory-play')!.addEventListener('click', (event) => {
      this.playing = !this.playing;
      (event.currentTarget as HTMLButtonElement).textContent = this.playing ? '❚❚ Pauza' : '▶ Odtwórz';
      this.lastFrame = performance.now();
    });
    this.root.querySelector<HTMLInputElement>('#trajectory-phase')!.addEventListener('input', (event) => {
      this.phase = Number((event.target as HTMLInputElement).value) / 1000; this.draw();
    });
  }

  private selectedPlanets(): PlanetId[] {
    return PLANET_IDS.filter((id) => this.state.visibleObjectIds.includes(id));
  }

  private rangeDays(ids: PlanetId[]): number {
    if (this.rangeMode === 'year') return 365.25;
    if (this.rangeMode === 'years') return 5 * 365.25;
    return Math.max(...ids.map((id) => SYNODIC_DAYS[id]), 365.25);
  }

  private rebuild(force = false): void {
    const ids = this.selectedPlanets();
    const start = new Date(`${this.state.sunUtc}:00Z`);
    const days = this.rangeDays(ids);
    const key = `${start.toISOString().slice(0,10)}|${this.rangeMode}|${ids.join(',')}`;
    if (!force && key === this.cacheKey) { this.draw(); return; }
    this.cacheKey = key;
    const samples = Math.min(900, Math.max(240, Math.ceil(days / 2)));
    this.tracks = ids.map((id) => ({
      id,
      name: planetTrajectoryFrame(id, start).name,
      frames: Array.from({ length:samples }, (_, index) => {
        const date = new Date(start.getTime() + days * (index / (samples - 1)) * 86_400_000);
        return planetTrajectoryFrame(id, date);
      }),
    }));
    const note = this.root.querySelector<HTMLElement>('#trajectory-note')!;
    note.textContent = ids.length
      ? `${ids.length} ${ids.length === 1 ? 'planeta' : 'planet'} · ${Math.round(days)} dni · wspólna oś czasu od ${start.toLocaleDateString('pl-PL')}`
      : 'Zaznacz co najmniej jedną planetę w katalogu obiektów.';
    this.draw();
  }

  private animate = (now: number): void => {
    if (this.playing) {
      const elapsed = Math.min((now - this.lastFrame) / 1000, 0.25);
      this.phase = (this.phase + elapsed * 0.035 * this.speed) % 1;
      this.root.querySelector<HTMLInputElement>('#trajectory-phase')!.value = String(Math.round(this.phase * 1000));
      this.draw();
    }
    this.lastFrame = now;
    this.animationFrame = requestAnimationFrame(this.animate);
  };

  private draw(): void {
    const ids = this.selectedPlanets();
    const start = new Date(`${this.state.sunUtc}:00Z`);
    const days = this.rangeDays(ids);
    const date = new Date(start.getTime() + days * this.phase * 86_400_000);
    this.root.querySelector<HTMLOutputElement>('#trajectory-date')!.value = date.toLocaleDateString('pl-PL', { year:'numeric', month:'short', day:'numeric' });
    this.drawPanel('geo', (frame) => frame.geocentricAu, 'Ziemia');
    this.drawPanel('helio', (frame) => frame.heliocentricAu, 'Słońce');
    this.drawInverse();
  }

  private drawPanel(id: string, point: (frame: PlanetTrajectoryFrame) => Vec3, centreLabel: string): void {
    const canvas = this.root.querySelector<HTMLCanvasElement>(`#trajectory-${id}`)!;
    const context = canvas.getContext('2d')!;
    this.background(context, canvas, centreLabel);
    const all = this.tracks.flatMap((track) => track.frames.map(point));
    const limit = Math.max(0.1, ...all.map((p) => Math.hypot(p.x, p.y))) * 1.08;
    this.tracks.forEach((track) => this.strokeTrack(context, canvas, track, (frame) => {
      const p = point(frame); return { x:p.x/limit, y:p.y/limit };
    }));
  }

  private drawInverse(): void {
    const canvas = this.root.querySelector<HTMLCanvasElement>('#trajectory-inverse')!;
    const context = canvas.getContext('2d')!;
    this.background(context, canvas, 'P∞');
    const radii = this.tracks.flatMap((track) => track.frames.map(({ invertedOffsetKm:p }) => Math.max(1e-12, Math.hypot(p.x,p.y,p.z))));
    const logs = radii.map(Math.log10);
    const min = Math.min(...logs, -9); const max = Math.max(...logs, min + 1); const span = max - min;
    this.tracks.forEach((track) => this.strokeTrack(context, canvas, track, ({ invertedOffsetKm:p }) => {
      const radius = Math.max(1e-12, Math.hypot(p.x,p.y,p.z));
      const angle = Math.atan2(p.y,p.x);
      const mapped = 0.12 + 0.82 * ((Math.log10(radius)-min)/span);
      return { x:Math.cos(angle)*mapped, y:Math.sin(angle)*mapped };
    }));
  }

  private background(context: CanvasRenderingContext2D, canvas: HTMLCanvasElement, label: string): void {
    context.clearRect(0,0,canvas.width,canvas.height);
    context.fillStyle='#061722'; context.fillRect(0,0,canvas.width,canvas.height);
    const cx=canvas.width/2, cy=canvas.height/2;
    context.strokeStyle='rgba(101,210,203,.16)'; context.lineWidth=1;
    for (const scale of [.25,.5,.75,1]) { context.beginPath(); context.arc(cx,cy,scale*canvas.height*.42,0,Math.PI*2); context.stroke(); }
    context.beginPath(); context.moveTo(24,cy); context.lineTo(canvas.width-24,cy); context.moveTo(cx,24); context.lineTo(cx,canvas.height-24); context.stroke();
    context.fillStyle='#ff4fa3'; context.beginPath(); context.arc(cx,cy,5,0,Math.PI*2); context.fill();
    context.fillStyle='#d6eaee'; context.font='600 14px Inter, sans-serif'; context.fillText(label,cx+11,cy-10);
  }

  private strokeTrack(context: CanvasRenderingContext2D, canvas: HTMLCanvasElement, track: Track, map: (frame: PlanetTrajectoryFrame) => {x:number;y:number}): void {
    const count = this.drawMode === 'progressive' ? Math.max(2, Math.floor(this.phase*(track.frames.length-1))+1) : track.frames.length;
    const cx=canvas.width/2, cy=canvas.height/2, scale=canvas.height*.42;
    context.beginPath();
    for (let index=0; index<count; index += 1) {
      const p=map(track.frames[index]!); const x=cx+p.x*scale, y=cy-p.y*scale;
      if (index===0) context.moveTo(x,y); else context.lineTo(x,y);
    }
    context.strokeStyle=COLOURS[track.id]; context.globalAlpha=.82; context.lineWidth=2; context.stroke(); context.globalAlpha=1;
    const marker=map(track.frames[Math.min(track.frames.length-1,Math.floor(this.phase*(track.frames.length-1)))]!);
    const x=cx+marker.x*scale,y=cy-marker.y*scale;
    context.fillStyle=COLOURS[track.id]; context.beginPath(); context.arc(x,y,5,0,Math.PI*2); context.fill();
    context.fillStyle=COLOURS[track.id]; context.font='600 12px Inter, sans-serif'; context.fillText(track.name,x+8,y-7);
  }
}
