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
- integrator eikonalny 3D, triangulację asymptotycznych promieni i globalne dopasowanie parametrów,
- walidator gęstej siatki, tarczy Słońca (C-2) i biegunów niebieskich (C-3),
- główną hipotezę v2: profil Maxwella z analitycznym adapterem lustra,
- zamkniętą jako `v2-falsified-hybrid` rodzinę Luneburga z pełnym audytem.

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
- Trzy pełne przebiegi DE z różnymi populacjami startowymi odtworzyły `2314,03 km`, czyli poprawę o około `6,7%`. Rozwiązanie na granicach `A=-0,1`, `s=100 km` jest stabilnym minimum tej rodziny, lecz nie jest dobrym modelem globalnym.

Zamknięcie odrzuconego modelu `v1-falsified` opisuje
[`docs/V1_CLOSURE.md`](docs/V1_CLOSURE.md), a główną hipotezę soczewkową v2 —
[`docs/LENS_MODELS.md`](docs/LENS_MODELS.md).

Maszynowy zapis wyniku wstępnego znajduje się w [`solver/results/preliminary-fit.json`](solver/results/preliminary-fit.json).
Pełne wyniki trzech ziaren są zapisane obok jako `full-fit-v1-seed-*.json`.

Natywne testy analityczne v2 są zaliczone. Kontrolny adapter górnej półsfery
Luneburga jest gotowy do lokalnego przebiegu przez niezmieniony walidator
C-2/C-3 (`python -m solver.validate_lens`). Dokładny pierwszy interwał
Maxwella i odbicie od lustra są zaimplementowane bez RK45 jako wielkie okręgi
na pomocniczej `S^3`. Kod celowo nie zastępuje profilu arbitralnym obcięciem.
Pojedyncza obserwacja wyznacza przy tym krzywą, nie ogólny jednoznaczny punkt
źródła. Dla spójnie rozwiniętych krzywych wspólny punkt jest liczony zamkniętą
dekompozycją własną `4×4`. Gałęzie przed/po odbiciu wybiera tani schemat
naprzemienny z kilkoma kontrolowanymi restartami, bez RK45 i bez optymalizacji
po `alpha`. Kontrakt opisuje
[`docs/MAXWELL_MIRROR_CONTRACT.md`](docs/MAXWELL_MIRROR_CONTRACT.md).

Pierwsza, wcześniej zamrożona tania bramka Maxwella dla
`R=20015,086796 km`, `z0=0` zakończyła się **FAIL**. Model poprawił kierunkowy
RMS centrów Słońca o `59,33%` i bieguna południowego o `83,06%`, ale pogorszył
biegun północny o `9,70%`. Wszystkie drogi były skierowane w przód, cztery
ziarna dały ten sam wynik, a bieguny nie zapadły się w jeden punkt. Pełne C-2
pozostaje zablokowane. Kryteria i wynik opisują
[`docs/V2_MAXWELL_CHEAP_GATE.md`](docs/V2_MAXWELL_CHEAP_GATE.md) oraz
[`docs/V2_MAXWELL_CHEAP_GATE_RESULT.md`](docs/V2_MAXWELL_CHEAP_GATE_RESULT.md).

Następny, wcześniej zamrożony skan samego `z0` przy stałym `R` dał
**0/7 PASS**. Nie potwierdził prostego kompromisu między biegunami:
`z0/R=+0,40` poprawia jednocześnie północ i południe, ale cztery grupy
słoneczne łamią warunek drogi w przód. Przy `+0,10` i `+0,25` wszystkie grupy
Słońca są ważne i mają jeszcze niższy RMS, lecz biegun północny staje się
niefizyczny. Pełne C-2 nadal jest zablokowane; wynik opisuje
[`docs/V2_MAXWELL_Z0_SCAN_RESULT.md`](docs/V2_MAXWELL_Z0_SCAN_RESULT.md).

Jednowymiarowy skan większego `R` przy stałym bezwzględnym
`z0=8006,034718 km` dał następnie **2/6 PASS**. Punkty `R/Rbase=1,20` i
`1,35` odzyskały wszystkie drogi słoneczne w przód oraz jednocześnie pobiły
`n=1` dla Słońca i obu biegunów. Do pełnego C-2 promowany jest `1,20`
(`R=24018,104155 km`): poprawa wynosi `60,11%` dla centrów Słońca, `15,76%`
dla bieguna N i `83,44%` dla bieguna S. Pełne C-2 jest odblokowane, ale nie
zostało jeszcze uruchomione. Kontrakt pełnego testu zamraża 75 celów, osobny
konsensus punktu i przypisań `P/JPJ`, bufor drogi w przód `10°` oraz liczbowe
progi stałości i kształtu tarczy. Szczegóły:
[`docs/V2_MAXWELL_RADIUS_SCAN_RESULT.md`](docs/V2_MAXWELL_RADIUS_SCAN_RESULT.md).
Kontrakt kolejnego przebiegu:
[`docs/V2_MAXWELL_FULL_C2.md`](docs/V2_MAXWELL_FULL_C2.md).

Pełny przebieg tego kontraktu zakończył się **FAIL**. Wszystkie 75 celów miało
zgodny punkt i identyczne przypisania `P/JPJ` między ziarnami, a C-3 pozostało
zaliczone. Jeden brzeg tarczy prowadził jednak wstecz (`forward_sine=-0,7787`),
a rozmiar tarczy nie był stały sezonowo (`CV=18,63%`, `max/min=1,617`).
Szczegółowy wynik:
[`docs/V2_MAXWELL_FULL_C2_RESULT.md`](docs/V2_MAXWELL_FULL_C2_RESULT.md).

Po kontrolowanej korekcie promienia kątowego Słońca oczekiwana zmiana
grudzień/czerwiec wynosi `3,30%`, natomiast model odtwarza `51,62%`. Po
usunięciu znanego efektu odległości pozostaje **46,77% niewyjaśnionej zmiany
skali**. Diagnostyczny skan deklinacji nie potwierdził jednej gładkiej funkcji
na całym zakresie z powodu granicy gałęzi przy `-17,58°`; na stabilnym
fragmencie `-11,72° ... +23,44°` skala jest jednak ściśle monotoniczna
(`R²=0,9775`). Szczegóły:
[`docs/V2_MAXWELL_FULL_C2_CORRECTED_RESULT.md`](docs/V2_MAXWELL_FULL_C2_CORRECTED_RESULT.md)
i [`docs/V2_MAXWELL_DECLINATION_SCAN_RESULT.md`](docs/V2_MAXWELL_DECLINATION_SCAN_RESULT.md).

Analiza rezydualnej korekty na stabilnej gałęzi wybiera najprostszą postać
`C(delta)=1+0,544753*sin(delta)` (`RMSE=0,72%`, błąd maksymalny `1,60%`).
Postać `sin(delta)` odpowiada wiodącemu członowi dipolowemu `l=1` radialnego
pola przesuniętego osiowo. Parzysty kwadrupol `P2` nie zmienia różnicy między
przeciwnymi przesileniami; ewentualnym następnym składnikiem sezonowym jest
nieparzysty oktupol `P3`, rozdzielany od `P1` przez deklinacje pośrednie.
Rzeczywisty grudzień leży na odbitej stronie granicy, natomiast czerwiec na
bezpośredniej, dlatego sezonowej rozbieżności nie można przypisać wyłącznie
gładkiemu efektowi `z0`. Następny stopień swobody powinien realizować
nieparzystą osiową korektę lokalnej skali, niezależną od stabilizacji gałęzi.
Szczegóły:
[`docs/V2_MAXWELL_SCALE_CORRECTION_RESULT.md`](docs/V2_MAXWELL_SCALE_CORRECTION_RESULT.md).
Przed jego implementacją obowiązuje kontrolowany test wymuszonej kontynuacji
na wspólnej kohorcie:
[`docs/V2_MAXWELL_FORCED_BRANCH_CONTINUATION.md`](docs/V2_MAXWELL_FORCED_BRANCH_CONTINUATION.md).
Test wykazał jednoznaczny gładki czynnik `1,203849`, ale pełna dekompozycja
nie przeszła kontroli konsensusu gałęzi dla sześciu grudniowych celów. Wynik
pozostaje **FAIL**; nie implementujemy jeszcze nowego parametru. Szczegóły:
[`docs/V2_MAXWELL_FORCED_BRANCH_CONTINUATION_RESULT.md`](docs/V2_MAXWELL_FORCED_BRANCH_CONTINUATION_RESULT.md).
Audyt wykazał też, że mnożnik `5,964089` nie jest indeksem nawinięcia — model
nie ma takiej zmiennej, a wynik jest zdominowany przez przełączenie jednego
brzegu tarczy o 16:00. Szczegóły:
[`docs/V2_MAXWELL_BRANCH_GEOMETRY_AUDIT.md`](docs/V2_MAXWELL_BRANCH_GEOMETRY_AUDIT.md).

Identyfikacja na wymuszonej gałęzi `P` i jednej kohorcie 20 obserwatorów
wybrała minimalną nieparzystą bazę `P1`: parametr ustalony na przesileniu
przewidział parę `±11,72°` z błędem `1,40%`, poniżej zamrożonego progu `2%`.
`P1+P3` nie jest obecnie uzasadnione dodatkowym parametrem. Szczegóły:
[`docs/V2_MAXWELL_RESPONSE_IDENTIFICATION_RESULT.md`](docs/V2_MAXWELL_RESPONSE_IDENTIFICATION_RESULT.md).
Jest to pierwszy zamrożony test out-of-sample w projekcie: parametr nie był
oceniany na danych użytych do jego wyznaczenia.

Trzy dotychczasowe przypadki nieciągłości `P/JPJ` zostały połączone w osobny
wątek badawczy:
[`docs/V2_MAXWELL_BRANCH_AMBIGUITY_RESEARCH.md`](docs/V2_MAXWELL_BRANCH_AMBIGUITY_RESEARCH.md).
Implementacja lokalnego dipola wymaga nowego propagatora, ponieważ traci się
dokładną geometrię wielkich okręgów:
[`docs/V2_LOCAL_DIPOLE_ARCHITECTURE.md`](docs/V2_LOCAL_DIPOLE_ARCHITECTURE.md).

Zatwierdzona obwiednia lokalnego dipola została zaimplementowana wraz z
numerycznym propagatorem i lustrem. Zamrożona bramka `epsilon=0` odtwarza
12/12 analitycznych torów `S3`, w tym odbicia, i kończy się **PASS**. Nie
uruchomiono jeszcze skanu `epsilon` ani C-3. Szczegóły:
[`docs/V2_LOCAL_DIPOLE_PROPAGATOR_RESULT.md`](docs/V2_LOCAL_DIPOLE_PROPAGATOR_RESULT.md).

Tani skan C-3 wyłonił trzy amplitudy lokalnego dipola, które jednocześnie
poprawiają oba bieguny: `epsilon=0,10`, `0,20`, `0,40`. Wszystkie ujemne
wartości oraz `0,05` odpadły. Nie wybrano jeszcze jednego zwycięzcy i nie
uruchomiono C-2. Szczegóły:
[`docs/V2_LOCAL_DIPOLE_C3_SCAN_RESULT.md`](docs/V2_LOCAL_DIPOLE_C3_SCAN_RESULT.md).

Następna zamrożona bramka skali odrzuciła wszystkie trzy amplitudy (`0/3
PASS`). Dodatni dipol poprawiający C-3 zwiększa CV średnicy oraz asymetrię
skali na parach pośredniej i przesileniowej; pełny C-2 pozostaje zablokowany.
Szczegóły:
[`docs/V2_LOCAL_DIPOLE_SCALE_GATE_RESULT.md`](docs/V2_LOCAL_DIPOLE_SCALE_GATE_RESULT.md).

Ekran czułości monopolu, kwadrupola i oktupola nie wyłonił drugiego parametru:
każdy składnik po orientacji znaku poprawia asymetrię i CV kosztem większej
eliptyczności, a różnice centralne częściowo przecinają granice konkurencyjnych
minimów. Skan 2D i pełny C-2 pozostają zablokowane. Szczegóły:
[`docs/V2_LOCAL_MULTIPOLE_SENSITIVITY_RESULT.md`](docs/V2_LOCAL_MULTIPOLE_SENSITIVITY_RESULT.md).

Diagnostyka przypadku `delta=-11,72 deg` wykazała niemal płaską dolinę
rozwiązań zamiast kilku izolowanych minimów. Nie jest ona jednak przyczyną
eliptyczności: wszystkie 1024 kombinacje klastrów dają `axis_ratio` w zakresie
`1,286–1,318`, powyżej limitu `1,10`. Szczegóły:
[`docs/V2_LOCAL_BASIN_DIAGNOSTIC_RESULT.md`](docs/V2_LOCAL_BASIN_DIAGNOSTIC_RESULT.md).

Pierwszy przebieg ustawienia `R=20015 km`, `z0=0` ujawnił błędne kryterium
wyjścia z kulistego pola; zostało ono zastąpione rzeczywistym przecięciem
sferycznej granicy bez zmiany równania RK45. Dalsza ścieżka używa etapowego
`python -m solver.scan_luneburg`: najpierw niezerowe `z0` przy stałym `R`,
potem lokalna siatka `(R,z0)`. Pełne C-2 jest uzasadnione wyłącznie dla
kandydatów, które biją `n=1` dla środka Słońca i obu biegunów oraz mają same
nieujemne odległości w przód.

Oba zadeklarowane etapy zakończyły się wynikiem `0 PASS`: siedem punktów skanu
`z0` oraz dziewięć punktów lokalnej siatki `(R,z0)`. Pełne C-2 nie zostało
uruchomione, a hybryda Luneburga jest zamknięta. Szczegóły i zamrożone kryteria
są w [`docs/V2_LUNEBURG_CLOSURE.md`](docs/V2_LUNEBURG_CLOSURE.md).

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
