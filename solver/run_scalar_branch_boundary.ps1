$ErrorActionPreference = "Stop"

$RepositoryRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Brak .venv. Uruchom najpierw: py -3.12 -m venv .venv"
}

$Workers = [Math]::Max(1, [Environment]::ProcessorCount - 1)
Set-Location $RepositoryRoot
& $Python -m solver.scan_scalar_branch_boundary --workers $Workers

if ($LASTEXITCODE -ne 0) {
    throw "Skan granicy gałęzi zakończył się błędem $LASTEXITCODE"
}

Write-Host "Gotowe: solver/results/v2-scalar-branch-boundary.json"
