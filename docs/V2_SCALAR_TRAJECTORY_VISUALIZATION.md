# Animacja trajektorii z checkpointów SVD

Generator nie wykonuje ponownie ray tracingu. Odczytuje zachowane wyniki
najlepszego kandydata `epsilon=0,40 / degree_3` z katalogu:

`solver/results/v2-scalar-nx-svd-checkpoints/candidates/`

Obecny eksperyment zawiera cztery rzeczywiście policzone deklinacje:
`-23,44`, `-11,72`, `+11,72`, `+23,44 deg`. Ruch pomiędzy nimi w animacji
jest wyłącznie interpolacją wizualną i jest tak oznaczony na ekranie.

## Uruchomienie

PowerShell z katalogu głównego repozytorium:

```powershell
.\solver\run_scalar_trajectory.ps1
```

Git Bash:

```bash
bash solver/run_scalar_trajectory.sh
```

Skrypt tworzy i otwiera:

- `solver/results/v2-scalar-trajectory.html` — samodzielną animację,
- `solver/results/v2-scalar-trajectory.json` — wyciągnięte dane diagnostyczne.

Wizualizacja pokazuje ślad środka źródła, powiększony kształt rekonstruowanej
tarczy, RMS, średnicę i axis ratio. Widok trajektorii można obracać myszą.

## Zakres wniosku

To diagnostyka czterech checkpointów deklinacji przy jednym momencie
referencyjnym, nie pełna trajektoria dobowa. Jeżeli cztery punkty tworzą
rozsądną geometrię, następnym etapem będzie wąski przebieg czasowy samego
środka Słońca dla najlepszego pola. Nie należy interpretować interpolowanych
klatek jako nowych wyników solvera.
