# Wynik pełnego testu osiągalności skalarnego `n(x)`

## Werdykt

Przebieg zakończył wszystkie `9/9` analiz: trzy punkty bazowe lokalnego
dipola (`epsilon = 0,00`, `0,20`, `0,40`) oraz trzy zagnieżdżone bazy
skalarnego pola (`3`, `6`, `10` funkcji).

Wynik **nie potwierdza lokalnego no-go** dla badanej klasy gładkich pól
skalarnych `n(rho,z)`. Jeden kandydat — `epsilon=0,40`, baza stopnia 3 —
zmniejszył jednocześnie normę rezyduum na zbiorze dopasowania i na wcześniej
niewidzianym zbiorze held-out.

Nie jest to jednak fizyczny `PASS`. Kształt tarczy pozostaje daleko poza
zamrożonym limitem `axis_ratio <= 1,10`, a jeden z dwóch kontrolnych składników
kształtu minimalnie się pogarsza. Pełne C-2 pozostaje zablokowane.

## Wyniki wszystkich dziewięciu analiz

Wartość dodatnia oznacza spadek normy błędu; wartość ujemna — pogorszenie.

| epsilon | baza | ranga | fit | held-out | oba lepsze |
|---:|:---|---:|---:|---:|:---:|
| 0,00 | stopień 1 | 3 | +41,370% | -4,884% | nie |
| 0,00 | stopień 2 | 5 | +3,903% | -1,515% | nie |
| 0,00 | stopień 3 | 5 | +12,598% | -1,706% | nie |
| 0,20 | stopień 1 | 3 | +37,223% | -13,071% | nie |
| 0,20 | stopień 2 | 5 | +3,146% | -1,917% | nie |
| 0,20 | stopień 3 | 5 | +9,825% | -0,033% | nie |
| 0,40 | stopień 1 | 3 | +29,299% | -4,344% | nie |
| 0,40 | stopień 2 | 5 | +4,274% | -0,191% | nie |
| 0,40 | stopień 3 | 5 | **+10,314%** | **+2,477%** | **tak** |

Niższe bazy potrafią mocno poprawić fit, ale systematycznie pogarszają dane
held-out. Dopiero kombinacja najwyższego badanego punktu bazowego i pełnej
bazy stopnia 3 daje dodatnią, choć małą predykcję poza zbiorem dopasowania.

## Najlepszy kandydat

Dla `epsilon=0,40`, stopnia 3:

- norma fit: `0,387141 -> 0,347211` (`-10,314%`),
- norma held-out: `0,313367 -> 0,305606` (`-2,477%`),
- przewidywanie liniowe i pełna kontrola nieliniowa są bliskie:
  `0,349403` wobec `0,347211` dla fit oraz `0,304559` wobec `0,305606`
  dla held-out,
- C-3 pozostaje praktycznie na progu: północ przekracza cel tylko o około
  `0,00074%`, południe go nie przekracza,
- wymagany stosunek skali na fit poprawia się z `1,21737` do `1,19516`,
- wymagany stosunek skali held-out poprawia się z `1,11708` do `1,10339`.

Kształt tarczy nadal nie przechodzi:

| zbiór | axis ratio 1 przed | axis ratio 1 po | axis ratio 2 przed | axis ratio 2 po |
|:---|---:|---:|---:|---:|
| fit | 1,49696 | 1,44803 | 1,24954 | 1,23396 |
| held-out | 1,35242 | 1,35456 | 1,35433 | 1,34482 |

Limit każdego axis ratio wynosi `1,10`. Trzy składowe poprawiają się, ale
pierwsza składowa held-out pogarsza się o około `0,16%` w wartości bezwzględnej.
Dlatego dodatni wynik normy nie może być interpretowany jako przejście
zamrożonej bramki fizycznej.

## Co mówi SVD

Bazy stopnia 2 i 3 mają rangę efektywną `5`, równą liczbie obserwabli fit.
Lokalnie badana rodzina potrafi więc poruszać wszystkimi pięcioma kierunkami
funkcji kosztu. Nie oznacza to jeszcze, że istnieje globalne rozwiązanie:

- każdy krok został ograniczony promieniem zaufania `||c|| <= 0,25`,
- najlepszy kandydat leży dokładnie na tej granicy,
- nieograniczona norma współczynników dla niego wynosi `2,56467`, ponad
  dziesięć razy więcej,
- tak duża ekstrapolacja nie może być uznana na podstawie jednej
  linearizacji.

Test wyklucza zatem mocne twierdzenie „w tym punkcie nie istnieje nawet
lokalny kierunek poprawiający fit i held-out”. Nie dowodzi twierdzenia
przeciwnego, że dowolne skalarne `n(x)` rozwiąże C-2.

## Zamrożony następny krok

Nie uruchamiać pełnego C-2 ani nowej siatki wielowymiarowej. Następnym testem
jest jednowymiarowa kontynuacja najlepszego kierunku przy
`epsilon=0,40`, z zachowaniem tej samej kohorty fit/held-out:

1. skalować wyłącznie znaleziony wektor dziesięciu współczynników małymi
   krokami wokół obecnego promienia zaufania,
2. kontrolować osobno wszystkie składowe rezyduum, C-3, dodatniość pola,
   drogę w przód oraz stabilność konkurencyjnych minimów,
3. promować punkt tylko wtedy, gdy nie pogarsza żadnej składowej held-out,
   a nie wyłącznie jego normy,
4. jeżeli poprawa utrzyma się do brzegu kolejnego małego kroku, ponownie
   policzyć Jacobian w zaakceptowanym punkcie zamiast ekstrapolować do
   nieograniczonego rozwiązania,
5. zatrzymać linię natychmiast po utracie held-out albo warunków fizycznych.

To jest test znacznie tańszy od zakończonego przebiegu: wykorzystuje jeden
punkt bazowy i jeden kierunek zamiast trzech punktów i dziesięciu kolumn
różnic skończonych.

## Zakres wniosku

Wynik jest lokalnym testem osiągalności badanej, skończonej bazy gładkich pól
skalarnych. Nie jest dowodem istnienia rozwiązania, globalnym dowodem no-go,
pełnym C-2 ani argumentem za ośrodkiem anizotropowym.

Surowy zapis maszynowy: `solver/results/v2-scalar-nx-svd.json`.
