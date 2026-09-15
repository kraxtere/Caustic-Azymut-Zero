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

## Pliki

| Plik | Odpowiedzialność |
|---|---|
| `ephemeris.py` | wymienny interfejs efemeryd i implementacja Meeusa |
| `geometry_flat.py` | projekcja AE, lokalna baza E/N/U, alt-az |
| `field.py` | pięcioparametrowe pole i jego gradient analityczny |
| `raytrace.py` | integracja eikonalna 3D i triangulacja prostych |
| `demo_baseline.py` | kontrolny wynik bez pola |
| `fit_field.py` | globalna oraz wielostartowa optymalizacja |
| `tests/` | testy regresyjne matematyki i wyniku bazowego |
