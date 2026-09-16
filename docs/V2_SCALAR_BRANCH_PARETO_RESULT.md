# Diagram gałęzi i kompromis ciągłość–RMS

## Zakres

Analiza wykorzystuje wyłącznie 104 zapisane restarty skanu granicy. Nie
wykonuje nowego ray tracingu. W każdym punkcie rozwiązania są grupowane według
pełnej sygnatury odbić i klastra źródła, a następnie wybierana jest globalna
ścieżka przez wszystkie 13 deklinacji.

## Werdykt

Wśród znalezionych stanów **nie istnieje ciągła ścieżka źródła**. Nawet
rozwiązanie minimax, które ignoruje lokalne minimum RMS i minimalizuje przede
wszystkim największy skok trajektorii, zachowuje skok `2950,99 km/deg`.

Mediana tempa niezależnych, stabilnych odcinków wynosi `181,92 km/deg`.
Najlepsza dostępna ścieżka ratunkowa pozostaje więc `16,22x` gwałtowniejsza
od typowego ruchu.

## Krzywa kompromisu

| wybór | średnia kara RMS | łączna kara RMS² | największy skok [km/deg] | sekwencja liczby odbić |
|:---|---:|---:|---:|:---|
| niezależne minima | 0,000% | 0,000% | 3993,22 | 8-6-6-6-6-6-2-0-0-0-0-0-0 |
| mała kara ciągłości | 0,014% | 0,031% | 3918,64 | 8-6-6-6-6-2-2-0-0-0-0-0-0 |
| większa kara | 0,328% | 0,706% | 2988,55 | 6-6-6-6-4-2-2-0-0-0-0-0-0 |
| minimax | 0,391% | 0,849% | **2950,99** | 6-6-6-6-4-2-0-0-0-0-0-0-0 |

Koszt RMS potrzebny do zmiany gałęzi jest bardzo mały. Problemem nie jest
więc brak alternatywnych minimów o podobnym koszcie, tylko brak stanów
geometrycznie łączących ich źródła. Zwiększanie kary ciągłości szybko
przestaje poprawiać trajektorię: rozwiązanie minimax i rozwiązanie ważone
kończą się na tym samym maksymalnym skoku.

## Interpretacja

Sekwencja minimax `6 -> 4 -> 2 -> 0` wygląda jak oczekiwane stopniowe
zmniejszanie liczby odbitych promieni, ale znalezione punkty tych gałęzi są
nadal oddalone o tysiące kilometrów. Sam wybór pośrednich sygnatur nie tworzy
ciągłości.

Wynik odrzuca obwiednię znalezionych minimów jako fizyczną trajektorię. Nie
jest jeszcze globalnym dowodem, że pomiędzy nimi nie istnieją bardzo wąskie,
nieodkryte fragmenty gałęzi. Dlatego uzasadniony jest jeden ostatni,
ograniczony test: adaptacyjna bisekcja i prawdziwa kontynuacja sekwencyjna w
obu kierunkach wokół przejść `8->6`, `6->2` oraz `2->0`.

Przed uruchomieniem należy zamrozić warunek powodzenia: ciągła ścieżka musi
zejść poniżej dwukrotności stabilnej mediany, czyli około `363,85 km/deg`, bez
utraty konsensusu źródło–odbicia–`alpha`. Jeśli nie, kandydat
`epsilon=0,40 / degree_3` zostaje zamknięty i nie wraca do kontynuacji SVD.

## Pliki

- dane: `solver/results/v2-scalar-branch-pareto.json`,
- samodzielny diagram: `solver/results/v2-scalar-branch-diagram.html`,
- analizator: `solver/analyze_scalar_branch_pareto.py`.
