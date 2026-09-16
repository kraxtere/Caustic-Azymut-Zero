"""Derive a branch diagram and continuity/RMS Pareto frontier without ray tracing."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from .validate_maxwell_c2 import SELECTED_RADIUS_KM


DEFAULT_INPUT = Path("solver/results/v2-scalar-branch-boundary.json")
DEFAULT_OUTPUT = Path("solver/results/v2-scalar-branch-pareto.json")
DEFAULT_HTML = Path("solver/results/v2-scalar-branch-diagram.html")
LAMBDA_GRID = (0.0, 1e-8, 3e-8, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 1.0, 10.0, 100.0)
REFERENCE_SPEED_KM_PER_DEGREE = 200.0


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _states(record: dict[str, object], cluster_km: float) -> list[dict[str, object]]:
    states: list[dict[str, object]] = []
    for run in sorted(record["runs"], key=lambda item: item["rms_km"]):
        source = np.asarray(run["source_km"], dtype=float)
        signature = run["signature"]["hash"]
        existing = next(
            (
                state for state in states
                if state["signature_hash"] == signature
                and float(np.linalg.norm(source - state["source_km"])) <= cluster_km
            ),
            None,
        )
        if existing is None:
            states.append({
                "state_id": f"d{record['declination_deg']:+.3f}:s{len(states)}",
                "signature_hash": signature,
                "reflected_observer_count": int(run["signature"]["reflected_observer_count"]),
                "source_km": source,
                "alphas_rad": np.asarray(run["alphas_rad"], dtype=float),
                "rms_km": float(run["rms_km"]),
                "start": run["start"],
            })
    return states


def _path_metrics(
    indices: list[int],
    state_rows: list[list[dict[str, object]]],
    deltas: np.ndarray,
) -> dict[str, object]:
    chosen = [state_rows[index][state] for index, state in enumerate(indices)]
    local_best = [min(item["rms_km"] for item in row) for row in state_rows]
    speeds = [
        float(np.linalg.norm(chosen[index + 1]["source_km"] - chosen[index]["source_km"]) / (deltas[index + 1] - deltas[index]))
        for index in range(len(chosen) - 1)
    ]
    relative = [chosen[index]["rms_km"] / local_best[index] - 1.0 for index in range(len(chosen))]
    return {
        "state_ids": [item["state_id"] for item in chosen],
        "reflection_counts": [item["reflected_observer_count"] for item in chosen],
        "signature_hashes": [item["signature_hash"] for item in chosen],
        "rms_km": [item["rms_km"] for item in chosen],
        "step_speed_km_per_degree": speeds,
        "average_rms_penalty_percent": 100.0 * float(np.mean(relative)),
        "total_squared_rms_penalty_percent": 100.0 * (
            float(np.sum(np.square([item["rms_km"] for item in chosen])))
            / float(np.sum(np.square(local_best))) - 1.0
        ),
        "maximum_step_speed_km_per_degree": max(speeds),
        "median_step_speed_km_per_degree": float(np.median(speeds)),
    }


def _weighted_path(
    weight: float,
    state_rows: list[list[dict[str, object]]],
    deltas: np.ndarray,
) -> list[int]:
    first_best = min(item["rms_km"] for item in state_rows[0])
    costs = np.asarray([(item["rms_km"] / first_best) ** 2 - 1.0 for item in state_rows[0]])
    back_rows: list[list[int]] = []
    for index in range(1, len(state_rows)):
        local_best = min(item["rms_km"] for item in state_rows[index])
        scale = REFERENCE_SPEED_KM_PER_DEGREE * (deltas[index] - deltas[index - 1])
        next_costs = []
        back = []
        for current in state_rows[index]:
            alternatives = [
                float(costs[previous])
                + weight * (float(np.linalg.norm(current["source_km"] - prior["source_km"])) / scale) ** 2
                for previous, prior in enumerate(state_rows[index - 1])
            ]
            selected = int(np.argmin(alternatives))
            next_costs.append(
                alternatives[selected] + (current["rms_km"] / local_best) ** 2 - 1.0
            )
            back.append(selected)
        costs = np.asarray(next_costs)
        back_rows.append(back)
    selected = int(np.argmin(costs))
    path = [selected]
    for back in reversed(back_rows):
        selected = back[selected]
        path.append(selected)
    return list(reversed(path))


def _minimax_path(
    state_rows: list[list[dict[str, object]]],
    deltas: np.ndarray,
) -> list[int]:
    costs = [(0.0, 0.0) for _ in state_rows[0]]
    back_rows: list[list[int]] = []
    for index in range(1, len(state_rows)):
        local_best = min(item["rms_km"] for item in state_rows[index])
        step = deltas[index] - deltas[index - 1]
        next_costs = []
        back = []
        for current in state_rows[index]:
            alternatives = []
            for previous, prior in enumerate(state_rows[index - 1]):
                speed = float(np.linalg.norm(current["source_km"] - prior["source_km"])) / step
                alternatives.append((
                    max(costs[previous][0], speed),
                    costs[previous][1] + (current["rms_km"] / local_best) ** 2 - 1.0,
                    previous,
                ))
            selected = min(alternatives, key=lambda item: (item[0], item[1]))
            next_costs.append(selected[:2])
            back.append(selected[2])
        costs = next_costs
        back_rows.append(back)
    selected = min(range(len(costs)), key=lambda index: costs[index])
    path = [selected]
    for back in reversed(back_rows):
        selected = back[selected]
        path.append(selected)
    return list(reversed(path))


def analyze(payload: dict[str, object]) -> dict[str, object]:
    deltas = np.asarray([record["declination_deg"] for record in payload["records"]], dtype=float)
    cluster_km = float(payload["design"]["cluster_fraction_of_radius"]) * SELECTED_RADIUS_KM
    state_rows = [_states(record, cluster_km) for record in payload["records"]]
    candidates = []
    seen = set()
    for weight in LAMBDA_GRID:
        indices = _weighted_path(weight, state_rows, deltas)
        key = tuple(state_rows[index][state]["state_id"] for index, state in enumerate(indices))
        if key in seen:
            continue
        seen.add(key)
        item = _path_metrics(indices, state_rows, deltas)
        item["selection"] = "weighted"
        item["continuity_weight"] = weight
        candidates.append(item)
    minimax_indices = _minimax_path(state_rows, deltas)
    minimax = _path_metrics(minimax_indices, state_rows, deltas)
    minimax["selection"] = "minimax"
    minimax["continuity_weight"] = None
    independent = candidates[0]
    stable_reference = independent["median_step_speed_km_per_degree"]
    return {
        "schema_version": 1,
        "status": "completed",
        "source": "solver/results/v2-scalar-branch-boundary.json",
        "cluster_threshold_km": cluster_km,
        "reference_speed_km_per_degree": REFERENCE_SPEED_KM_PER_DEGREE,
        "declinations_deg": deltas.tolist(),
        "states": [
            [
                {
                    **{key: value for key, value in state.items() if key not in {"source_km", "alphas_rad"}},
                    "source_km": state["source_km"].tolist(),
                    "alphas_rad": state["alphas_rad"].tolist(),
                }
                for state in row
            ]
            for row in state_rows
        ],
        "pareto_paths": candidates,
        "minimax_path": minimax,
        "summary": {
            "independent_maximum_speed_km_per_degree": independent["maximum_step_speed_km_per_degree"],
            "independent_median_speed_km_per_degree": stable_reference,
            "minimax_maximum_speed_km_per_degree": minimax["maximum_step_speed_km_per_degree"],
            "minimax_to_independent_median_ratio": minimax["maximum_step_speed_km_per_degree"] / stable_reference,
            "minimax_average_rms_penalty_percent": minimax["average_rms_penalty_percent"],
            "minimax_reflection_counts": minimax["reflection_counts"],
            "continuous_path_found_in_sampled_states": bool(
                minimax["maximum_step_speed_km_per_degree"] <= 2.0 * stable_reference
            ),
        },
        "scope": "post-processing of previously computed restart states; no new ray tracing",
    }


def _html(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Diagram gałęzi skalarnego kandydata</title><style>
:root{{color-scheme:light dark;--bg:#f7f7f8;--fg:#18181b;--muted:#666;--panel:#fff;--line:#d4d4d8;--c0:#2563eb;--c2:#059669;--c4:#d97706;--c6:#dc2626;--c8:#7c3aed}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111216;--fg:#f4f4f5;--muted:#aaa;--panel:#1b1c21;--line:#3f3f46;--c0:#60a5fa;--c2:#34d399;--c4:#fbbf24;--c6:#fb7185;--c8:#c4b5fd}}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:20px}}h1{{font-size:21px;margin:0 0 5px}}p{{color:var(--muted);margin:0 0 18px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}section{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}}h2{{font-size:15px;margin:0 0 8px}}canvas{{display:block;width:100%;height:390px}}.legend{{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted)}}.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}canvas{{height:330px}}}}
</style></head><body><main><h1>Diagram gałęzi i kompromisu ciągłości</h1><p>Analiza 104 zapisanych restartów; bez nowego ray tracingu.</p><div class="grid"><section><h2>RMS basenów względem deklinacji</h2><canvas id="branches"></canvas><div class="legend" id="legend"></div></section><section><h2>Koszt ciągłości</h2><canvas id="pareto"></canvas></section></div><script id="data" type="application/json">{encoded}</script><script>
const D=JSON.parse(document.getElementById('data').textContent);const css=getComputedStyle(document.documentElement);const color=n=>css.getPropertyValue('--c'+n)||css.getPropertyValue('--fg');const setup=id=>{{const c=document.getElementById(id),d=devicePixelRatio||1,r=c.getBoundingClientRect();c.width=Math.round(r.width*d);c.height=Math.round(r.height*d);const x=c.getContext('2d');x.setTransform(d,0,0,d,0,0);return[x,r.width,r.height]}};function axes(x,w,h,pad,xs,ys){{x.strokeStyle=css.getPropertyValue('--line');x.beginPath();x.moveTo(pad.l,pad.t);x.lineTo(pad.l,h-pad.b);x.lineTo(w-pad.r,h-pad.b);x.stroke();return[v=>pad.l+(v-Math.min(...xs))/(Math.max(...xs)-Math.min(...xs)||1)*(w-pad.l-pad.r),v=>h-pad.b-(v-Math.min(...ys))/(Math.max(...ys)-Math.min(...ys)||1)*(h-pad.t-pad.b)]}}function branches(){{const[x,w,h]=setup('branches'),p={{l:55,r:18,t:18,b:34}},rows=[];D.states.forEach((ss,i)=>ss.forEach(s=>rows.push({{d:D.declinations_deg[i],r:s.rms_km,n:s.reflected_observer_count}})));const[X,Y]=axes(x,w,h,p,rows.map(q=>q.d),rows.map(q=>q.r));[0,2,4,6,8].forEach(n=>{{const q=rows.filter(v=>v.n===n).sort((a,b)=>a.d-b.d);if(!q.length)return;x.strokeStyle=color(n);x.lineWidth=2;x.beginPath();q.forEach((v,i)=>i?x.lineTo(X(v.d),Y(v.r)):x.moveTo(X(v.d),Y(v.r)));x.stroke();q.forEach(v=>{{x.fillStyle=color(n);x.beginPath();x.arc(X(v.d),Y(v.r),4,0,7);x.fill()}})}});x.fillStyle=css.getPropertyValue('--muted');D.declinations_deg.forEach(v=>x.fillText(v.toFixed(1)+'°',X(v)-14,h-10));x.fillText('RMS [km]',6,15)}}function pareto(){{const[x,w,h]=setup('pareto'),p={{l:58,r:18,t:18,b:38}},rows=D.pareto_paths.concat([D.minimax_path]).map((q,i)=>({{x:q.average_rms_penalty_percent,y:q.maximum_step_speed_km_per_degree,name:q.selection==='minimax'?'minimax':'λ='+q.continuity_weight}}));const[X,Y]=axes(x,w,h,p,rows.map(q=>q.x),rows.map(q=>q.y));rows.forEach((v,i)=>{{x.fillStyle=i===rows.length-1?color(8):color(0);x.beginPath();x.arc(X(v.x),Y(v.y),i===rows.length-1?7:5,0,7);x.fill();x.fillStyle=css.getPropertyValue('--muted');x.fillText(v.name,X(v.x)+7,Y(v.y)-6)}});x.fillStyle=css.getPropertyValue('--muted');x.fillText('średnia kara RMS [%]',w/2-58,h-10);x.fillText('max km/°',6,15)}}document.getElementById('legend').innerHTML=[0,2,4,6,8].map(n=>`<span><i class="dot" style="background:var(--c${{n}})"></i>${{n}} odbić</span>`).join('');new ResizeObserver(()=>{{branches();pareto()}}).observe(document.querySelector('main'));branches();pareto();
</script></main></body></html>"""


def run(input_path: Path, output: Path, html: Path) -> dict[str, object]:
    result = analyze(_read_json(input_path))
    _write_json(output, result)
    html.write_text(_html(result), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    args = parser.parse_args()
    result = run(args.input, args.output, args.html)
    print(json.dumps(result["summary"], indent=2))
    print(f"Dane: {args.output}")
    print(f"Diagram: {args.html}")


if __name__ == "__main__":
    main()
