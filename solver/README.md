# Rdzeń solvera

Ta warstwa odpowiada wyłącznie za eksperyment odwrotnej optyki. Nie zależy od
Three.js ani od konstrukcji kopuły używanej w wizualizacji.

## Hipoteza testowana w pierwszym etapie

Dla jednego obiektu i jednej chwili prowadzimy promienie wstecz od kilku
obserwatorów, zgodnie z ich azymutem i elewacją. Po opuszczeniu obszaru, w
którym gradient współczynnika załamania jest istotny, każdy promień wyznacza
prostą asymptotyczną. W obliczeniach traktujemy ją jako półprostą skierowaną
od obserwatora. Funkcja kosztu to średnia z RMS najmniejszych odległości od
tych półprostych, liczona dla wielu chwil i pór roku. Zapobiega to uznaniu za
źródło punktu leżącego za obserwatorem. Tryb zgodności z pierwotnym handoffem
(`--intersection lines`) zachowuje metrykę nieskończonych prostych.

Nie zakładamy położenia Słońca na kopule i nie dopasowujemy torów do krzywych
Béziera z FE-Dome.

Pierwsza rodzina pola ma pięć parametrów:

```text
n(rho,z) = 1 + k exp(-z/H)
             + A exp(-((rho-rho0)^2 + z^2)/(2 s^2))
```

Współrzędne solvera: `x, y` leżą w płaszczyźnie mapy, `z` jest wysokością, a
jednostką długości jest kilometr. Viewer ma konwencję Y-up; przy imporcie
wyników wymaga to jawnej zamiany osi.

## Uruchomienie

Z katalogu głównego repozytorium:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r solver/requirements.txt
python -m unittest discover -s solver/tests -v
python -m solver.demo_baseline
```

Pełne dopasowanie metodą ewolucji różnicowej:

```bash
python -m solver.fit_field \
  --method de \
  --maxiter 120 \
  --popsize 12 \
  --polish \
  --output solver/results/latest-fit.json
```

Parametry fizyczne są kodowane w znormalizowanej kostce `[0,1]^5`, a skale
`H` i `s` są mapowane logarytmicznie. Zapobiega to dominacji parametrów
liczonych w tysiącach kilometrów nad amplitudami rzędu `1e-4`.

Alternatywny test wielostartowy Neldera-Meada:

```bash
python -m solver.fit_field --method multistart --starts 12 --maxiter 800
```

Pola, dla których promień wraca do płaszczyzny albo nie opuszcza pola przed
limitem drogi, są odrzucane. Nie trafiają już po cichu do triangulacji.

Wynikowy JSON zapisuje ziarno, budżet i faktyczną liczbę użytych workerów.
Dla każdego poprawnego promienia zawiera także diagnostykę w stopniach:

- `net_direction_change_deg` — kąt między kierunkiem początkowym i końcowym,
- `background_path_bending_deg` — całka z krzywizny wniesionej przez tło,
- `ring_path_bending_deg` — analogiczna całka dla pierścienia,
- `combined_path_bending_deg` — całka z modułu łącznej krzywizny.

Całki składowych są liczone po gotowym torze, już po zakończeniu RK45. Nie
wpływają więc na dobór kroków, wynik śledzenia ani funkcję kosztu. Składowe
nie muszą sumować się do zmiany kierunku, ponieważ ugięcia o różnych
kierunkach mogą się częściowo znosić.

## Zamknięcie v1 i walidacja C-2/C-3

Trzy pełne przebiegi z różnymi populacjami startowymi odtworzyły to samo
minimum brzegowe. Szczegółowa decyzja i kontrola ziaren są opisane w
`../docs/V1_CLOSURE.md`.

Zamrożony wynik można sprawdzić poza siatką treningową bez ponownego
dopasowania:

```bash
./.venv/Scripts/python.exe -m solver.validate_v1 \
  --fit-json solver/results/full-fit-v1-seed-20260917.json \
  --workers 6 \
  --output solver/results/v1-closure-validation.json
```

Walidator używa 64 kandydatów, pięciu punktów tarczy Słońca i obu biegunów
niebieskich. Domyślna polityka `vacuum-geometric` wymusza `k=0`, ponieważ
cele Meeusa nie zawierają refrakcji pozornej. Pełny przebieg wykonujemy na
komputerze lokalnym; testy jednostkowe nie całkują tego dużego zbioru.

## Pliki

| Plik | Odpowiedzialność |
|---|---|
| `ephemeris.py` | wymienny interfejs efemeryd i implementacja Meeusa |
| `geometry_flat.py` | projekcja AE, lokalna baza E/N/U, alt-az |
| `field.py` | pięcioparametrowe pole i jego gradient analityczny |
| `raytrace.py` | integracja eikonalna 3D i triangulacja prostych |
| `demo_baseline.py` | kontrolny wynik bez pola |
| `fit_field.py` | globalna oraz wielostartowa optymalizacja |
| `validate_v1.py` | gęsta siatka oraz walidacja C-2 i C-3 bez refitu |
| `lenses.py` | analityczne modele odniesienia Maxwella i Luneburga |
| `tests/` | testy regresyjne matematyki i wyniku bazowego |
