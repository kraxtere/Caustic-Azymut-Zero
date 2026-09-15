# Caustic Azymut Zero

Eksperymentalne laboratorium do odwzorowywania obserwacji na azymutalnej mapie równodystansowej i badania modeli propagacji promienia nad płaszczyzną.

## Aktualny stan

Repozytorium zawiera teraz:

- uruchamialną aplikację 3D w Vite + TypeScript + Three.js,
- azymutalną mapę z siatką i liniami lądów,
- położenie obserwatora i źródła na elipsoidalnej kopule,
- krzywą Béziera odtwarzającą geometryczny punkt wyjścia aplikacji FE-Dome,
- czyste moduły matematyczne i testy,
- zachowaną kopię oryginalnego kodu Waltera Bislina w `reference/walter-bislin/`,
- niezależny solver Python z pięcioparametrowym polem toroidalnym,
- integrator eikonalny 3D, triangulację asymptotycznych promieni i globalne dopasowanie parametrów.

Krzywa Béziera jest tutaj **modelem bazowym do porównań**, a nie fizycznym wyjaśnieniem ugięcia światła. Solver nie strzela do założonej kopuły: prowadzi promienie od obserwatorów do zaniku pola i mierzy zbieżność ich asymptotycznych półprostych. Szczegóły są w [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) i [`solver/README.md`](solver/README.md).

## Uruchomienie

Wymagany jest Node.js 22 lub nowszy.

```bash
npm install
npm run dev
```

Kontrola jakości:

```bash
npm run check
```

Solver wymaga Pythona 3.11+ oraz NumPy i SciPy:

```bash
python3 -m pip install -r solver/requirements.txt
npm run test:solver
python3 -m solver.demo_baseline
```

Pełne sprawdzenie obu warstw uruchamia `npm run check:all`.

## Wyniki kontrolne

- Pojedyncza chwila z `demo_baseline.py`: wysokość najlepszego przecięcia `5060 km`, RMS `1069 km` bez pola.
- Sześć chwil używanych do dopasowania: średni RMS półprostych `2479,98 km` bez pola.
- Wstępny, skrócony przebieg DE + lokalne dopasowanie: `2314,03 km`, czyli poprawa o około `6,7%`. Rozwiązanie doszło do granic `A=-0,1` i `s=100 km`, więc **nie jest rozstrzygnięciem** ani wiarygodnym minimum wewnętrznym. Pełny przebieg pozostaje do wykonania z większym budżetem.

Maszynowy zapis wyniku wstępnego znajduje się w [`solver/results/preliminary-fit.json`](solver/results/preliminary-fit.json).

## Układ projektu

```text
src/model/       obliczenia niezależne od interfejsu i renderera
src/scene/       scena Three.js
src/ui/          kontrolki i prezentacja wyników
tests/           testy matematyki modelu
solver/          niezależne obliczenia, dopasowanie i testy Python
docs/            konwencje oraz plan dalszej rozbudowy
reference/       niemodyfikowana baza źródłowa FE-Dome
```

## Pochodzenie bazy

Punktem odniesienia jest aplikacja **FE-Dome App** Waltera Bislina. Strona źródłowa oznacza materiał jako Public Domain. Pełne informacje i linki znajdują się w [`ATTRIBUTION.md`](ATTRIBUTION.md).

Projekt ma charakter obliczeniowy i porównawczy. Każdy przyszły wariant pola warto sprawdzać jednocześnie względem surowych obserwacji oraz standardowego modelu astronomicznego z refrakcją atmosferyczną.
