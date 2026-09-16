# Uruchomienie pełnego testu osiągalności skalarnego `n(x)`

## Zakres obliczeń

Runner wykonuje:

- trzy punkty bazowe `epsilon=0,00`, `0,20`, `0,40`,
- kotwice prowadzone kontynuacją co `0,05`,
- centralne różnice dla 10 kolumn największej bazy,
- zagnieżdżone SVD baz 3, 6 i 10 funkcji,
- fit na `delta=+-23,44 deg`,
- held-out na `delta=+-11,72 deg`,
- nieliniową walidację dziewięciu kandydatów w czterech krokach kontynuacji,
- C-3 oraz pięć elementów każdej tarczy.

Każdy zakończony cel jest zapisywany w katalogu checkpointów. Ponowne
uruchomienie tej samej komendy wznawia pracę i nie liczy gotowych elementów.

## Windows PowerShell

Z katalogu głównego repozytorium:

```powershell
.\solver\run_full_scalar_svd.ps1
```

Skrypt wykorzystuje `liczba logicznych procesorów - 1` procesów.

## Git Bash

Z katalogu głównego repozytorium:

```bash
bash solver/run_full_scalar_svd.sh
```

Można jawnie ograniczyć liczbę procesów, uruchamiając bezpośrednio:

```bash
./.venv/Scripts/python.exe -m solver.run_scalar_nx_svd \
  --workers 8 \
  --checkpoint-dir solver/results/v2-scalar-nx-svd-checkpoints \
  --output solver/results/v2-scalar-nx-svd.json
```

## Pliki wynikowe

- wynik końcowy: `solver/results/v2-scalar-nx-svd.json`,
- stan wznowienia: `solver/results/v2-scalar-nx-svd-checkpoints/`.

Po ukończeniu należy przekazać plik JSON. Katalog checkpointów jest duży i
nie trzeba go wysyłać ani dodawać do Git.

## Przerwanie i wznowienie

Proces można bezpiecznie przerwać `Ctrl+C`. Ukończone checkpointy pozostają.
Ta sama komenda podejmie pracę. Nie należy zmieniać kodu, parametrów ani
katalogu checkpointów w połowie jednego eksperymentu.

Tryb smoke, używany wyłącznie do kontroli instalacji:

```bash
./.venv/Scripts/python.exe -m solver.run_scalar_nx_svd \
  --smoke --workers 4 \
  --checkpoint-dir solver/results/smoke-scalar-nx-svd-checkpoints \
  --output solver/results/smoke-scalar-nx-svd.json
```

Smoke używa czterech obserwatorów, jednego punktu bazowego i jednej kolumny.
Nie wolno interpretować go jako wyniku fizycznego.

