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

workers="$($python_bin -c 'import os; print(max(1, (os.cpu_count() or 2) - 1))')"
"$python_bin" -m solver.scan_scalar_branch_boundary --workers "$workers"
echo "Gotowe: solver/results/v2-scalar-branch-boundary.json"
