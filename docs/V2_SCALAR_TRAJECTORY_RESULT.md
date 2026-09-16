# Wynik diagnostyki trajektorii z checkpointów SVD

## Zakres

Analiza wykorzystuje bez ponownego ray tracingu cztery checkpointy najlepszego
kandydata `epsilon=0,40 / degree_3` dla deklinacji `-23,44`, `-11,72`,
`+11,72` i `+23,44 deg`. Wszystkie pozycje pośrednie pokazywane przez HTML są
wyłącznie interpolacją wizualną.

## Werdykt

Cztery punkty **nie uzasadniają jednej gładkiej trajektorii na całym
zakresie**. Odcinek od `-23,44` do `-11,72 deg` ma inną skalę i kierunek niż
dwa następne. Jest to zgodne z wcześniej rozpoznaną granicą rozwiązania około
`-17,58 deg`, leżącą wewnątrz tego odcinka.

Zakres od `-11,72` do `+23,44 deg` jest znacznie bardziej regularny, ale
rekonstrukcja źródła nadal ma RMS rzędu tysięcy kilometrów. Ślad średnich
punktów nie może być traktowany jako precyzyjnie wyznaczona fizyczna pozycja
Słońca.

## Geometria środka

| odcinek [deg] | długość [km] | km/deg |
|:---|---:|---:|
| -23,44 -> -11,72 | 6963,47 | 594,15 |
| -11,72 -> +11,72 | 4366,70 | 186,29 |
| +11,72 -> +23,44 | 1904,06 | 162,46 |

Pierwsza prędkość parametryczna jest `3,19x` większa od środkowej i `3,66x`
większa od ostatniej. Kąt między pierwszym a drugim wektorem odcinka wynosi
`44,33 deg`, natomiast między drugim a trzecim tylko `3,74 deg`.

Współrzędna poprzeczna `y` pozostaje numerycznie bliska zeru we wszystkich
czterech punktach. Ślad zachowuje więc oczekiwaną symetrię płaszczyzny
południkowej; problem dotyczy zmiany gałęzi lub basenu w tej płaszczyźnie,
nie przypadkowego skręcenia poza nią.

## Jakość rekonstrukcji

| deklinacja | RMS środka [km] | RMS/R | odległość od środka soczewki [km] |
|---:|---:|---:|---:|
| -23,44 | 4044,13 | 0,1684 | 16432,97 |
| -11,72 | 3646,14 | 0,1518 | 13289,00 |
| +11,72 | 2033,19 | 0,0847 | 9840,38 |
| +23,44 | 1740,41 | 0,0725 | 8705,03 |

Flaga `converged=true` oznacza zbieżność iteracji numerycznej, a nie ścisłą
zgodność obserwatorów. RMS stanowi około `7-17%` promienia soczewki i około
`20-27%` odległości punktu od jej środka. Położenie źródła jest zatem szerokim
kompromisem między krzywymi, nie ostrym przecięciem.

## Zachowanie tarczy

| deklinacja | średnica [km] | axis ratio | dłuższa oś | offset środka |
|---:|---:|---:|:---:|---:|
| -23,44 | 88,73 | 1,4480 | E-W | 0,155% |
| -11,72 | 87,98 | 1,3546 | N-S | 0,278% |
| +11,72 | 79,73 | 1,3448 | N-S | 0,087% |
| +23,44 | 74,24 | 1,2340 | N-S | 0,075% |

Mały offset środka względem centroidu czterech brzegów jest wynikiem
pozytywnym. Jednocześnie między `-23,44` a `-11,72 deg` dłuższa oś zmienia się
z E-W na N-S. W połączeniu z załamaniem śladu wskazuje to na przejście przez
znaną granicę rozwiązania, a nie na spokojną ewolucję jednej elipsy.

## Następny test

Nie należy jeszcze zagęszczać całej trajektorii dobowej. Najpierw potrzebna
jest tania, jednokierunkowa kontynuacja samego środka na przedziale
`-23,44 ... -11,72 deg`, z punktami co około `1 deg` i dwoma przejściami:

1. od `-23,44` ku `-11,72 deg`, z ciepłym startem z poprzedniego punktu,
2. od `-11,72` ku `-23,44 deg`, również z ciepłym startem.

Rozbieżność obu przejść pokaże histerezę i współistnienie basenów. Zgodność
przy pojedynczym ostrym skoku wskaże geometryczną granicę jednej kontynuacji.
Test obejmuje wyłącznie środek, bez czterech brzegów tarczy, i powinien być
znacznie tańszy od pełnego SVD.

Pełną animację dobową warto policzyć dopiero po zlokalizowaniu tej granicy;
inaczej interpolacja ukrywałaby główną nieciągłość modelu.

Surowy zapis: `solver/results/v2-scalar-trajectory.json`.
