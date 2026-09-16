# Wynik skanu granicy gałęzi skalarnego kandydata

## Werdykt

Skan rozstrzyga wcześniejszą alternatywę: obserwowana nierównomierność nie
jest jedną silnie zakrzywioną, ale ciągłą trajektorią. Najlepsze rozwiązanie
przełącza się między kilkoma odrębnymi basenami o różnych sygnaturach odbić.

Na 13 deklinacji tylko 6 spełnia pełny konsensus źródło–odbicia–`alpha`.
Jedenaście punktów ma przynajmniej jedną diagnostykę granicy basenu, a
maksymalna odległość między rozwiązaniami otrzymanymi ze startów z obu stron
wynosi `6819,10 km`.

## Najmocniejszy punkt dowodowy

Przy `delta=-18,5567 deg` dwa rozwiązania są jednocześnie konkurencyjne:

- najlepszy basen: 6 promieni po odbiciu, RMS `4341,49 km`,
- drugi basen: 2 promienie po odbiciu, RMS `4349,14 km`,
- rozdział źródeł: `3906,75 km`,
- maksymalna różnica składowej `alpha`: `0,81699 rad`,
- dwie różne sygnatury odbić i dwa klastry źródeł.

Różnica RMS wynosi tylko około `0,18%`, podczas gdy geometrie źródła są
oddalone o tysiące kilometrów. Jest to bezpośredni dowód wielowartościowości
odwrotnego rozwiązania w badanym sąsiedztwie, nie szum optymalizatora.

## Diagram basenów

Minimalne RMS znalezione dla każdej sygnatury pokazują następującą sekwencję
obwiedni najlepszego kosztu:

- przy `-23,44 deg`: najlepsza sygnatura z 8 odbitymi promieniami,
- od około `-22,46` do `-18,56 deg`: 6 odbitych promieni,
- przy `-17,58 deg`: 2 odbite promienie,
- od około `-16,60 deg`: 0 odbitych promieni.

W szerokim zakresie baseny współistnieją, ale ich koszty przecinają się:

| delta [deg] | 6 odbić RMS [km] | 2 odbicia RMS [km] | 0 odbić RMS [km] |
|---:|---:|---:|---:|
| -20,51 | 4175,33 | 4467,08 | — |
| -19,53 | 4251,19 | — | 4605,54 |
| -18,56 | 4341,49 | 4349,14 | 4471,88 |
| -17,58 | 4445,05 | 4306,72 | 4342,21 |
| -16,60 | 4560,65 | 4275,33 | 4216,51 |
| -15,63 | 4687,03 | 4254,83 | 4094,74 |
| -14,65 | 4822,91 | 4244,98 | 3976,88 |

Wybór niezależnego minimum w każdej deklinacji tworzy więc poszarpaną
obwiednię kilku gładniejszych gałęzi. Nie jest to jedna trajektoria źródła.

## Kinematyka obwiedni minimum

- maksymalna prędkość parametryczna: `3993,22 km/deg`,
- drugi skok: `2988,55 km/deg`,
- gładkie fragmenty po obu stronach: około `143-189 km/deg`,
- maksymalny zwrot między odcinkami: `138,48 deg`,
- kolejne duże zwroty w rejonie przełączeń: `119,08`, `55,92` i `21,11 deg`.

To potwierdza, że wcześniejsze załamanie `44,33 deg` było skutkiem zbyt
rzadkiego próbkowania kilku przełączeń, a nie pojedynczą łagodną krzywizną.

## Drugi mechanizm: płaska dolina

Po stronie bez odbić, szczególnie od około `-15,63` do `-11,72 deg`, część
restartów ma tę samą sygnaturę odbić i niemal identyczny RMS, lecz różne
`alpha` lub źródła. Przykładowo przy `-13,6733 deg` występują trzy klastry
źródeł tej samej sygnatury, rozdzielone maksymalnie o `43,38 km`.

Skan rozdziela zatem dwa zjawiska:

1. dyskretne przełączenia topologii odbić w rejonie południowym,
2. ciągłą, płaską dolinę rozwiązań tej samej topologii bliżej `-11,72 deg`.

Oba łamią ścisły konsensus, ale nie wolno ich interpretować jako tego samego
mechanizmu.

## Konsekwencja

Pełna animacja dobowa oparta na niezależnym minimum każdej chwili pozostaje
zablokowana: interpolowałaby między różnymi rozwiązaniami topologicznymi.
Skan nie zamyka jeszcze całej klasy skalarnego `n(x)`, ale odrzuca obecną
obwiednię minimum jako pojedynczą fizyczną trajektorię źródła.

Następny tani test nie wymaga nowego ray tracingu. Z już zapisanych restartów
należy zbudować diagram gałęzi i rozwiązać dyskretną kontynuację z karą za
skok źródła oraz `alpha`. Wynikiem ma być krzywa Pareto: ile pogorszenia RMS
trzeba zaakceptować, aby wymusić ciągłą trajektorię. Jeżeli nawet duża kara
nie daje ciągłego toru bez znacznego wzrostu RMS, obecny kandydat powinien
zostać zamknięty.

Surowy wynik: `solver/results/v2-scalar-branch-boundary.json`.
