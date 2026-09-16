"""Build an interactive trajectory diagnostic from completed scalar-SVD checkpoints."""

from __future__ import annotations

import argparse
import json
import math
import webbrowser
from pathlib import Path

import numpy as np

from .scan_local_dipole_scale import _disk_shape
from .validate_maxwell_c2 import SAMPLE_IDS


DEFAULT_CHECKPOINT_DIR = Path("solver/results/v2-scalar-nx-svd-checkpoints")
DEFAULT_OUTPUT = Path("solver/results/v2-scalar-trajectory.html")
DEFAULT_DATA_OUTPUT = Path("solver/results/v2-scalar-trajectory.json")
DECLINATIONS_DEG = (-23.44, -11.72, 11.72, 23.44)


def _slug(value: str) -> str:
    return value.replace(":", "__").replace("+", "p").replace("-", "m").replace(".", "_")


def _candidate_path(
    checkpoint_dir: Path,
    dipole: float,
    level: str,
    declination: float,
    sample_id: str,
) -> Path:
    key = f"base={dipole}:level={level}:group=disk:{declination:+.2f}:{sample_id}"
    return checkpoint_dir / "candidates" / f"{_slug(key)}.json"


def load_frames(
    checkpoint_dir: Path,
    dipole: float = 0.4,
    level: str = "degree_3",
) -> list[dict[str, object]]:
    frames = []
    missing = []
    for declination in DECLINATIONS_DEG:
        targets = {}
        for sample_id in SAMPLE_IDS:
            path = _candidate_path(checkpoint_dir, dipole, level, declination, sample_id)
            if not path.exists():
                missing.append(path)
                continue
            targets[sample_id] = json.loads(path.read_text(encoding="utf-8"))
        if len(targets) != len(SAMPLE_IDS):
            continue
        shape = _disk_shape(targets)
        frames.append({
            "declination_deg": declination,
            "samples": {
                sample_id: [float(value) for value in targets[sample_id]["source_km"]]
                for sample_id in SAMPLE_IDS
            },
            "rms_km": float(targets["centre"]["rms_km"]),
            "iterations": int(targets["centre"]["iterations"]),
            "converged": bool(targets["centre"]["converged"]),
            "shape": {name: float(value) for name, value in shape.items()},
        })
    if missing:
        preview = "\n".join(f"  - {path}" for path in missing[:5])
        suffix = f"\n  ... oraz {len(missing) - 5} dalszych" if len(missing) > 5 else ""
        raise FileNotFoundError(
            "Brakuje checkpointów najlepszego kandydata. Oczekiwane pliki m.in.:\n"
            f"{preview}{suffix}\n"
            "Uruchom skrypt z katalogu głównego repozytorium i wskaż właściwy --checkpoint-dir."
        )
    return frames


def build_payload(frames: list[dict[str, object]], dipole: float, level: str) -> dict[str, object]:
    centres = np.asarray([frame["samples"]["centre"] for frame in frames], dtype=float)
    steps = np.linalg.norm(np.diff(centres, axis=0), axis=1) if len(centres) > 1 else np.array([])
    return {
        "schema_version": 1,
        "kind": "checkpoint-trajectory-diagnostic",
        "candidate": {"dipole_epsilon": dipole, "basis_level": level},
        "frame_count": len(frames),
        "computed_declinations_deg": [frame["declination_deg"] for frame in frames],
        "centre_step_distances_km": steps.tolist(),
        "scope": (
            "Four computed declination checkpoints at one reference moment. "
            "Motion between checkpoints is visual interpolation, not ray tracing."
        ),
        "frames": frames,
    }


def _html(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trajektoria źródła — diagnostyka checkpointów</title>
<style>
:root {{ color-scheme: light dark; --bg:#f7f7f8; --fg:#171719; --muted:#65656d; --panel:#fff; --line:#d7d7dc; --a:#2563eb; --b:#d97706; --bad:#c0262d; }}
@media (prefers-color-scheme:dark) {{ :root {{ --bg:#111216; --fg:#f1f1f3; --muted:#aaaab3; --panel:#1a1b20; --line:#34363e; --a:#60a5fa; --b:#fbbf24; --bad:#fb7185; }} }}
* {{ box-sizing:border-box }} body {{ margin:0; font:14px/1.45 system-ui,sans-serif; background:var(--bg); color:var(--fg) }}
main {{ max-width:1180px; margin:auto; padding:20px }} h1 {{ font-size:21px; margin:0 0 4px }} p {{ margin:0; color:var(--muted) }}
.controls {{ display:flex; gap:12px; align-items:center; margin:18px 0; flex-wrap:wrap }} button {{ padding:8px 14px; font:inherit }} input[type=range] {{ flex:1; min-width:240px }}
.grid {{ display:grid; grid-template-columns:1.45fr 1fr; gap:14px }} .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px }}
h2 {{ font-size:15px; font-weight:600; margin:0 0 8px }} canvas {{ display:block; width:100%; height:420px }} #disk {{ height:245px }} #metrics {{ height:245px }}
.readout {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; margin-top:12px }} .metric {{ padding:8px 0; border-top:1px solid var(--line) }} .metric span {{ display:block; color:var(--muted); font-size:12px }} .metric strong {{ font-variant-numeric:tabular-nums }}
.status {{ color:var(--b); font-weight:600 }} .computed {{ color:var(--a) }}
@media(max-width:820px) {{ .grid {{ grid-template-columns:1fr }} canvas {{ height:330px }} .readout {{ grid-template-columns:repeat(2,1fr) }} }}
</style>
</head>
<body><main>
<h1>Rekonstruowana geometria źródła</h1>
<p>ε=0,40 · degree_3 · cztery rzeczywiście policzone deklinacje. Przejścia pomiędzy nimi są tylko interpolacją wizualną.</p>
<div class="controls"><button id="play" type="button">▶ Odtwórz</button><input id="time" type="range" min="0" max="3" step="0.001" value="0"><strong id="state" class="computed">punkt policzony</strong></div>
<div class="grid">
  <section class="panel"><h2>Ślad środka źródła w 3D — przeciągnij, aby obrócić</h2><canvas id="trajectory"></canvas><div class="readout">
    <div class="metric"><span>Deklinacja</span><strong id="declination"></strong></div><div class="metric"><span>RMS środka</span><strong id="rms"></strong></div>
    <div class="metric"><span>Średnica tarczy</span><strong id="diameter"></strong></div><div class="metric"><span>Axis ratio</span><strong id="axis"></strong></div>
  </div></section>
  <div><section class="panel"><h2>Tarcza względem własnego środka — skala powiększona</h2><canvas id="disk"></canvas></section><section class="panel" style="margin-top:14px"><h2>Metryki w policzonych punktach</h2><canvas id="metrics"></canvas></section></div>
</div>
<script id="payload" type="application/json">{encoded}</script>
<script>
const data=JSON.parse(document.getElementById('payload').textContent), frames=data.frames;
const slider=document.getElementById('time'), play=document.getElementById('play'); let running=false,last=0,yaw=-0.7,pitch=0.42,drag=null;
const lerp=(a,b,t)=>a+(b-a)*t, vec=(a,b,t)=>a.map((v,j)=>lerp(v,b[j],t));
function sample(){{const u=+slider.value,i=Math.min(frames.length-2,Math.floor(u)),t=u-i; const A=frames[i],B=frames[i+1]||A,out={{}}; for(const k of Object.keys(A.samples))out[k]=vec(A.samples[k],B.samples[k],t); return {{i,t,delta:lerp(A.declination_deg,B.declination_deg,t),rms:lerp(A.rms_km,B.rms_km,t),samples:out,shape:Object.fromEntries(Object.keys(A.shape).map(k=>[k,lerp(A.shape[k],B.shape[k],t)]))}}}}
function setup(c){{const d=devicePixelRatio||1,r=c.getBoundingClientRect(); if(c.width!==Math.round(r.width*d)||c.height!==Math.round(r.height*d)){{c.width=Math.round(r.width*d);c.height=Math.round(r.height*d)}} const x=c.getContext('2d');x.setTransform(d,0,0,d,0,0);return [x,r.width,r.height]}}
function project(p){{const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);const x=cy*p[0]-sy*p[2],z=sy*p[0]+cy*p[2];return [x,cp*p[1]-sp*z]}}
function colors(){{const s=getComputedStyle(document.documentElement);return {{fg:s.getPropertyValue('--fg'),muted:s.getPropertyValue('--muted'),line:s.getPropertyValue('--line'),a:s.getPropertyValue('--a'),b:s.getPropertyValue('--b'),bad:s.getPropertyValue('--bad')}}}}
function trajectory(cur){{const [x,w,h]=setup(document.getElementById('trajectory')),c=colors(),pts=frames.map(f=>project(f.samples.centre)),now=project(cur.samples.centre),all=pts.concat([now]);const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]),pad=42,minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys),scale=Math.min((w-2*pad)/(maxx-minx||1),(h-2*pad)/(maxy-miny||1)),P=p=>[w/2+(p[0]-(minx+maxx)/2)*scale,h/2-(p[1]-(miny+maxy)/2)*scale];x.clearRect(0,0,w,h);x.strokeStyle=c.line;x.lineWidth=1;x.beginPath();for(let j=0;j<pts.length;j++){{const q=P(pts[j]);j?x.lineTo(...q):x.moveTo(...q)}}x.stroke();for(let j=0;j<pts.length;j++){{const q=P(pts[j]);x.fillStyle=c.a;x.beginPath();x.arc(...q,5,0,Math.PI*2);x.fill();x.fillStyle=c.muted;x.fillText(frames[j].declination_deg.toFixed(2)+'°',q[0]+8,q[1]-7)}}const q=P(now);x.fillStyle=c.b;x.beginPath();x.arc(...q,8,0,Math.PI*2);x.fill()}}
function disk(cur){{const [x,w,h]=setup(document.getElementById('disk')),c=colors(),center=cur.samples.centre,ids=['north_limb','south_limb','east_limb','west_limb'],pts=ids.map(k=>project(cur.samples[k].map((v,j)=>v-center[j]))),extent=Math.max(1,...pts.flat().map(Math.abs)),s=0.38*Math.min(w,h)/extent,P=p=>[w/2+p[0]*s,h/2-p[1]*s];x.clearRect(0,0,w,h);x.strokeStyle=c.line;x.beginPath();x.moveTo(20,h/2);x.lineTo(w-20,h/2);x.moveTo(w/2,18);x.lineTo(w/2,h-18);x.stroke();x.strokeStyle=c.a;x.lineWidth=2;[['north_limb','south_limb'],['east_limb','west_limb']].forEach(pair=>{{const a=P(project(cur.samples[pair[0]].map((v,j)=>v-center[j]))),b=P(project(cur.samples[pair[1]].map((v,j)=>v-center[j])));x.beginPath();x.moveTo(...a);x.lineTo(...b);x.stroke()}});x.fillStyle=c.b;x.beginPath();x.arc(w/2,h/2,5,0,Math.PI*2);x.fill()}}
function metrics(cur){{const [x,w,h]=setup(document.getElementById('metrics')),c=colors(),pad={{l:46,r:40,t:18,b:30}},d=frames.map(f=>f.declination_deg),diam=frames.map(f=>f.shape.mean_diameter_km),axis=frames.map(f=>f.shape.axis_ratio),minD=Math.min(...diam),maxD=Math.max(...diam),minA=Math.min(1.1,...axis),maxA=Math.max(...axis),X=v=>pad.l+(v-d[0])/(d[d.length-1]-d[0])*(w-pad.l-pad.r),Y=(v,a,b)=>h-pad.b-(v-a)/(b-a||1)*(h-pad.t-pad.b);x.clearRect(0,0,w,h);x.strokeStyle=c.line;x.beginPath();x.moveTo(pad.l,pad.t);x.lineTo(pad.l,h-pad.b);x.lineTo(w-pad.r,h-pad.b);x.stroke();function line(vals,min,max,color){{x.strokeStyle=color;x.lineWidth=2;x.beginPath();vals.forEach((v,j)=>j?x.lineTo(X(d[j]),Y(v,min,max)):x.moveTo(X(d[j]),Y(v,min,max)));x.stroke();vals.forEach((v,j)=>{{x.fillStyle=color;x.beginPath();x.arc(X(d[j]),Y(v,min,max),4,0,Math.PI*2);x.fill()}})}}line(diam,minD,maxD,c.a);line(axis,minA,maxA,c.bad);x.strokeStyle=c.b;x.beginPath();x.moveTo(X(cur.delta),pad.t);x.lineTo(X(cur.delta),h-pad.b);x.stroke();x.fillStyle=c.a;x.fillText('średnica [km]',pad.l+4,14);x.fillStyle=c.bad;x.fillText('axis ratio',w-pad.r-62,14);x.fillStyle=c.muted;d.forEach(v=>x.fillText(v.toFixed(1)+'°',X(v)-16,h-8))}}
function draw(){{const cur=sample(),computed=cur.t<0.001||cur.t>0.999;document.getElementById('declination').textContent=cur.delta.toFixed(2)+'°';document.getElementById('rms').textContent=cur.rms.toFixed(2)+' km';document.getElementById('diameter').textContent=cur.shape.mean_diameter_km.toFixed(2)+' km';document.getElementById('axis').textContent=cur.shape.axis_ratio.toFixed(3);const st=document.getElementById('state');st.textContent=computed?'punkt policzony':'interpolacja wizualna';st.className=computed?'computed':'status';trajectory(cur);disk(cur);metrics(cur)}}
slider.addEventListener('input',draw);play.addEventListener('click',()=>{{running=!running;play.textContent=running?'❚❚ Pauza':'▶ Odtwórz';last=performance.now();requestAnimationFrame(tick)}});function tick(now){{if(!running)return;slider.value=(+slider.value+(now-last)/3500)%(frames.length-1);last=now;draw();requestAnimationFrame(tick)}}
const canvas=document.getElementById('trajectory');canvas.addEventListener('pointerdown',e=>{{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)}});canvas.addEventListener('pointermove',e=>{{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;pitch=Math.max(-1.3,Math.min(1.3,pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];draw()}});canvas.addEventListener('pointerup',()=>drag=null);new ResizeObserver(draw).observe(document.querySelector('main'));draw();
</script></main></body></html>"""


def run(
    checkpoint_dir: Path,
    output: Path,
    data_output: Path,
    dipole: float = 0.4,
    level: str = "degree_3",
) -> dict[str, object]:
    frames = load_frames(checkpoint_dir, dipole, level)
    payload = build_payload(frames, dipole, level)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_html(payload), encoding="utf-8")
    data_output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-output", type=Path, default=DEFAULT_DATA_OUTPUT)
    parser.add_argument("--dipole", type=float, default=0.4)
    parser.add_argument("--level", default="degree_3")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()
    payload = run(args.checkpoint_dir, args.output, args.data_output, args.dipole, args.level)
    print(f"Wczytano {payload['frame_count']} policzone klatki.")
    print(f"Animacja: {args.output}")
    print(f"Dane: {args.data_output}")
    if args.open_browser:
        webbrowser.open(args.output.resolve().as_uri())


if __name__ == "__main__":
    main()
