#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -x .venv/Scripts/python.exe ]]; then
  python_bin=.venv/Scripts/python.exe
elif [[ -x .venv/bin/python ]]; then
  python_bin=.venv/bin/python
else
  echo "Brak .venv. Utwórz je i zainstaluj solver/requirements.txt." >&2
  exit 1
fi

"$python_bin" -m solver.visualize_scalar_trajectory --open
echo "Gotowe: solver/results/v2-scalar-trajectory.html"
