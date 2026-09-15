# Raport dla prowadzącego — stan integracji solvera

Data: 2026-09-15  
Repozytorium: `kraxtere/Caustic-Azymut-Zero`  
Status: **implementacja etapu bazowego zakończona; pełny eksperyment optymalizacyjny jeszcze nieuruchomiony**

## 1. Co zostało dowiezione

Repozytorium ma obecnie dwie rozdzielone warstwy:

- aplikację Vite/TypeScript/Three.js odtwarzającą bazową geometrię FE-Dome i służącą jako wizualizator,
- niezależny solver Python do odwrotnego śledzenia promieni w osiowosymetrycznym polu `n(rho,z)`.

Solver zawiera:

- efemerydę Słońca i konwersję czasu,
- azymutalną projekcję równodystansową oraz lokalne bazy E/N/U,
- pięcioparametrowe pole atmosferyczno-toroidalne,
- całkowanie równania eikonalnego w pełnym 3D metodą RK45,
- śledzenie wstecz od obserwatora do faktycznego zaniku pola,
- dopasowanie wspólnego punktu do asymptotycznych półprostych,
- znormalizowaną przestrzeń parametrów `[0,1]^5`,
- globalną optymalizację `differential_evolution`,
- opcjonalne, wielostartowe dopracowanie Neldera–Meada,
- zapis wyników do JSON oraz testy regresyjne.

Krzywa Béziera FE-Dome jest wyłącznie bazą wizualną. Nie jest celem dopasowania i solver nie zakłada powierzchni kopuły ani z góry zadanej wysokości źródła.

## 2. Korekty odkryte podczas integracji

Pakiet wejściowy wymagał dwóch istotnych poprawek, bez których optymalizator mógł zwracać sztucznie dobre wyniki:

1. Zdarzenie oznaczające zanik pola nie kończyło integracji, a limit drogi `3000 km` często pozostawiał promień nadal wewnątrz pola. Integracja kończy się teraz dopiero po spełnieniu kryterium zaniku całego pola; promienie nieuciekające, wracające do mapy albo uszkodzone numerycznie są karane jako nieważne.
2. Dopasowanie nieskończonych prostych dopuszczało przecięcia za obserwatorami lub pod mapą. Domyślną metryką są teraz fizyczne półproste. Tryb dawnych prostych pozostał jedynie do diagnostyki.

Dodano również diagnostykę rangi i uwarunkowania triangulacji, ograniczenie `rho0 >= 2s`, skalowanie logarytmiczne `H` i `s` oraz adaptacyjny pułap wyjścia z pola.

## 3. Kontrola jakości

Lokalnie zakończyło się powodzeniem:

- `9/9` testów TypeScript,
- sprawdzenie typów TypeScript,
- produkcyjny build Vite,
- `13/13` testów Python,
- kontrola białych znaków `git diff --check`.

Odtworzono punkt kontrolny pakietu wejściowego dla 2026-06-21 15:00 UTC: około `5060 km` wysokości wspólnego punktu i `1069 km` RMS bez pola.

Nie potwierdzono statusu zewnętrznego CI: integracja GitHub zwróciła `403` dla endpointu statusów commita. Sam commit i pliki na gałęzi `main` zostały natomiast odczytane ponownie i potwierdzone. Powyższe wyniki odnoszą się do pełnej kontroli lokalnej.

## 4. Wynik wstępnego dopasowania

Skrócony przebieg globalny (`24` generacje, mnożnik populacji `5`) z lokalnym dopracowaniem dał:

| Metryka | Bez pola | Wstępne pole |
|---|---:|---:|
| Średni RMS dla sześciu grup | `2479,98 km` | `2314,03 km` |
| Zmiana względna | — | `-6,69%` |
| Nieważne promienie | — | `0` |

Parametry rozwiązania wstępnego:

| Parametr | Wartość | Interpretacja |
|---|---:|---|
| `k` | `7,70e-10 1/km` | praktycznie zero |
| `H` | `30,0 km` | górna granica, nieistotna przy `k≈0` |
| `A` | `-0,1` | dolna granica |
| `rho0` | `11271,31 km` | promień pierścienia |
| `s` | `100,0 km` | dolna granica |

To **nie jest dodatni ani ujemny wynik hipotezy**. Minimum leży na granicach amplitudy i szerokości, a poprawa jest mała. Wynik mówi jedynie, że w skróconym biegu optymalizator preferuje wąski, silniejszy pierścień. Najsłabsze pozostają przypadki grudniowe (`3447,67 km` i `4422,50 km` RMS).

Pełny zapis maszynowy znajduje się w `solver/results/preliminary-fit.json`.

## 5. Otwarte ryzyka modelu

- Obecna efemeryda Meeusa jest dobrym testem technicznym, lecz docelowy zbiór powinien używać JPL/Skyfield oraz jawnych niepewności obserwacyjnych.
- Używane dane treningowe są syntetyczne. Nie ma jeszcze osobnego zbioru walidacyjnego ani tabeli rzeczywistych obserwacji.
- Pierścień Gaussa oparty na `rho=sqrt(x^2+y^2)` nie jest ściśle różniczkowalny na osi. Warunek `rho0 >= 2s` odsuwa istotną część pola od osi, ale nie usuwa tego problemu matematycznie. Warto dodać drugi, wszędzie gładki wariant pola i porównać go z wersją bazową.
- Wizualizator nie importuje jeszcze wyników JSON ani przebiegów promieni z solvera. Interfejs między warstwami jest opisany, ale eksport ścieżek i ich renderowanie należą do następnego etapu.
- Zrównoleglenie `--workers` ma bezpieczny fallback sekwencyjny. W bieżącym środowisku uruchomieniowym tworzenie procesów było blokowane; na zwykłej maszynie należy ponownie sprawdzić pracę równoległą.

## 6. Rekomendowany następny eksperyment

Najpierw należy zamknąć bazowy test modelu v1 bez zmiany rodziny pola:

```bash
python3 -m pip install -r solver/requirements.txt
npm run check:all
python3 -m solver.fit_field \
  --method de \
  --maxiter 120 \
  --popsize 12 \
  --polish \
  --output solver/results/full-fit-v1.json
```

Na maszynie dopuszczającej multiprocessing można dodać `--workers 6`. Dla wiarygodności należy wykonać kilka niezależnych ziaren losowych, ponownie przeliczyć najlepsze rozwiązanie z ostrzejszą tolerancją integratora i dopiero wtedy zdecydować o rozszerzeniu granic parametrów.

Po tym przebiegu proponowana kolejność jest następująca:

1. porównać minima z wielu ziaren i sprawdzić, czy nadal trafiają w granice,
2. dodać wszędzie gładką rodzinę pola toroidalnego jako model v2,
3. wprowadzić podział trening/walidacja oraz obserwacje oparte na JPL,
4. eksportować ścieżki promieni do JSON i wyświetlić je w aplikacji Three.js.

## 7. Decyzja potrzebna od prowadzącego

Rekomendacja: **uruchomić pełny, ograniczony test v1 przed rozbudową pola**. Pozwoli to rozdzielić pytanie „czy optymalizator dokończył przeszukiwanie?” od pytania „czy rodzina pola jest zbyt uboga?”. Dopiero wynik pełnego biegu powinien uruchomić wariant v2 albo świadome rozszerzenie granic.

