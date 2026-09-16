$ErrorActionPreference = "Stop"

$RepositoryRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Brak .venv. Uruchom najpierw: py -3.12 -m venv .venv"
}

Set-Location $RepositoryRoot
& $Python -m solver.visualize_scalar_trajectory --open

if ($LASTEXITCODE -ne 0) {
    throw "Generator animacji zakończył się błędem $LASTEXITCODE"
}

Write-Host "Gotowe: solver/results/v2-scalar-trajectory.html"
