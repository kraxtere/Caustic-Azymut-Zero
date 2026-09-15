# Rdzeń solvera

Ta warstwa odpowiada wyłącznie za eksperyment odwrotnej optyki. Nie zależy od
Three.js ani od konstrukcji kopuły używanej w wizualizacji.

## Status rodzin modeli

`field.py` i `fit_field.py` mają status **v1-falsified**. Pozostają w repo
wyłącznie jako odtwarzalny punkt odniesienia i nie powinny być dalej strojone.
`field_lens.py` zachowuje oba analitycznie sprawdzone profile. Hybryda
Luneburga ma status **v2-falsified-hybrid** po skanach `z0` i `(R,z0)`.
Główną hipotezą jest teraz dokładny Maxwell. Analityczny adapter pierwszego
interwału i lustra jest gotowy; następna bramka to rekonstrukcja wspólnego
punktu ze złożonych krzywych wielu obserwatorów.

## Historyczna hipoteza v1

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

Odrzucona rodzina pola ma pięć parametrów:

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

Historyczne odtworzenie dopasowania v1 metodą ewolucji różnicowej (nie jest to
nowy kierunek badań):

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
  --output solver/results/v1-closure-validation-v2.json
```

Walidator używa 64 kandydatów, pięciu punktów tarczy Słońca w trzech dziennych
torach oraz obu biegunów niebieskich. Grupa obserwatorów jest stała w obrębie
każdego toru, a kadencja nie pokrywa się z krokiem długości geograficznej.
Raport zawiera też kontrolę `n=1` i jawnie oznacza punkty leżące za choć jednym
promieniem. Domyślna polityka `vacuum-geometric` wymusza `k=0`, ponieważ cele
Meeusa nie zawierają refrakcji pozornej. Pełny przebieg wykonujemy na komputerze
lokalnym; testy jednostkowe nie całkują tego dużego zbioru.

## Historyczna walidacja hybrydy Luneburga v2

Po zaliczeniu natywnych testów analitycznych pierwszy adapter hybrydowy używa
górnej półsfery Luneburga nad mapą. Nie dopasowuje parametrów i nie zmienia
integratora, triangulacji ani metryk C-2/C-3:

```bash
./.venv/Scripts/python.exe -m solver.validate_lens \
  --family luneburg \
  --radius-km 20015.086796 \
  --centre-z-km 0 \
  --workers 6 \
  --output solver/results/v2-luneburg-default-validation.json
```

Historyczny walidator nadal odmawia uruchomienia Maxwella przez ścieżkę RK45,
zamiast po cichu obcinać profil. Jawny warunek odbicia jest już dostępny jako
analityczna ścieżka `maxwell_mirror.py`; nie jest jeszcze podłączony do C-2/C-3.

### Zamknięty etapowy skan położenia Luneburga

Pełne C-2 uruchamiamy dopiero po tańszej bramce obejmującej 15 środków Słońca
i oba bieguny C-3. Pierwszy etap utrzymuje `R` bez zmian i zaczyna od sześciu
wyraźnie niezerowych wartości `z0`; przypadek `z0=0` jest liczony na końcu jako
skorygowana kontrola:

```bash
./.venv/Scripts/python.exe -m solver.scan_luneburg \
  --stage z0 \
  --workers 6 \
  --output solver/results/v2-luneburg-z0-scan.json
```

Każdy z siedmiu kandydatów wymaga 344 promieni. JSON jest zapisywany po każdym
punkcie. Kandydat przechodzi tylko wtedy, gdy kompletny średni RMS środka
Słońca oraz RMS każdego bieguna są ściśle niższe od odpowiednich kontroli
`n=1`, a każde `minimum_forward_distance_km` jest nieujemne.

Drugi, wykonany etap użył następującego polecenia:

```bash
./.venv/Scripts/python.exe -m solver.scan_luneburg \
  --stage grid \
  --radius-fractions 1.2,1.35,1.5 \
  --z0-fractions=-0.9,-0.75,-0.6 \
  --workers 6 \
  --output solver/results/v2-luneburg-negative-local-grid.json
```

Zadeklarowana siatka drugiego etapu użyła `R/Rbase = 1,2; 1,35; 1,5` oraz
`z0/Rbase = -0,9; -0,75; -0,6`. Wynik obu etapów to odpowiednio `0/7` i
`0/9 PASS`. Nie uruchamiamy pełnego C-2 i nie rozszerzamy siatki. Szczegółowe
zamknięcie znajduje się w `../docs/V2_LUNEBURG_CLOSURE.md`.

## Pliki

| Plik | Odpowiedzialność |
|---|---|
| `ephemeris.py` | wymienny interfejs efemeryd i implementacja Meeusa |
| `geometry_flat.py` | projekcja AE, lokalna baza E/N/U, alt-az |
| `field.py` | archiwalne pole `v1-falsified` i jego gradient analityczny |
| `field_lens.py` | Maxwell v2 oraz archiwalny Luneburg, gradienty i analityka |
| `maxwell_mirror.py` | dokładny pierwszy interwał Maxwella na `S^3` i złożenie lustra |
| `raytrace.py` | integracja eikonalna 3D i triangulacja prostych |
| `demo_baseline.py` | kontrolny wynik bez pola |
| `fit_field.py` | historyczne odtworzenie optymalizacji v1 |
| `validate_v1.py` | gęsta siatka oraz walidacja C-2 i C-3 bez refitu |
| `validate_lens.py` | odtwarzalny adapter zamkniętej hybrydy Luneburga |
| `scan_luneburg.py` | odtwarzalny, zakończony skan `z0` i `(R,z0)` |
| `lenses.py` | zgodnościowy re-eksport API soczewek |
| `tests/` | testy regresyjne matematyki i wyniku bazowego |
