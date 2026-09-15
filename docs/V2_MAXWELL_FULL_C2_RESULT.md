# Wynik pełnego testu C-2 Maxwella v2

> Ten raport zachowuje pierwszy przebieg ze stałym promieniem kątowym
> `0,2666°`. Jego wniosek o drodze brzegowej pozostaje ważny, ale surowa
> interpretacja sezonowej zmienności została zastąpiona skorygowanym
> kontraktem v2.1 z datowo zmiennym promieniem Słońca.

## Decyzja

Wcześniej wybrany kandydat `R/Rbase=1,20`, `z0/Rbase=0,40` nie przeszedł
zamrożonej pełnej bramki. Wynik to **FAIL**. Nie zmieniamy progów ani nie
pomijamy wadliwego momentu po obejrzeniu danych.

Kandydat nadal przechodzi test centrów Słońca i regresję C-3. Pełne C-2
ujawnia jednak dwa ograniczenia niewidoczne w taniej bramce: utratę jednej
drogi brzegowej oraz zbyt dużą zmianę rekonstruowanej średnicy tarczy między
porami roku.

## Wynik bramki

Warunki zaliczone:

- średni kierunkowy RMS centrów Słońca wynosi `15,0900°` wobec `37,8288°`
  dla `n=1`, czyli poprawa wynosi `60,11%`,
- wszystkie 75 celów mają konsensus punktu pomiędzy czterema ziarnami,
- wszystkie 75 celów ma także identyczne pełne przypisanie obserwatorów do
  gałęzi `P/JPJ` pomiędzy ziarnami,
- wszystkie 75 źródeł leży wewnątrz lustra i nie poniżej mapy,
- oba bieguny C-3 pozostają ważne, skierowane w przód, rozdzielone i lepsze
  od `n=1`.

Warunki niezaliczone:

| Warunek | Próg | Wynik |
|---|---:|---:|
| kompletność tarcz | `15/15` | `14/15` |
| kompletność celów | `75/75` | `74/75` |
| minimalny margines drogi C-2 | `>= sin(10°) = 0,173648` | `-0,778655` |
| globalny CV średnicy | `<= 0,05` | `0,186320` |
| globalny stosunek max/min średnicy | `<= 1,10` | `1,617002` |
| największa owalność ważnej tarczy | `axis_ratio <= 1,10` | `1,103568` |
| największe przesunięcie środka | `<= 0,05` | `0,001908` — spełnione dla ważnych tarcz |

Formalny warunek przesunięcia środka ma w JSON wartość `false`, ponieważ
zgodnie z kontraktem wymaga również kompletu 15 kształtów. Wszystkie 14
policzonych tarcz ma jednak bardzo małe przesunięcie środka; ta metryka sama w
sobie nie jest źródłem porażki.

## Jedyny nieważny cel

Nieważny jest `west_limb` z toru równonocy marcowej o `10:00 UTC`:

- `minimum_forward_sine = -0,778655`,
- wszystkie ziarna wybierają to samo rozwiązanie,
- wszystkie ziarna zgadzają się także co do przypisania gałęzi,
- maksymalny rozrzut punktu na `S^3` wynosi `0 km`.

To nie jest niepewność optymalizatora. Jest to stabilnie odtworzona,
niefizyczna droga wstecz konkretnego promienia brzegowego. Pozostałe 74 cele
przekraczają bufor `10°`; następny najmniejszy `forward_sine` wynosi
`0,218838`.

## Stałość średnicy

| Tor | Ważne tarcze | Średnia średnica | CV | Max/min |
|---|---:|---:|---:|---:|
| równonoc marcowa | `4/5` | `74,6319 km` | `0,05854` | `1,15328` |
| przesilenie czerwcowe | `5/5` | `70,2403 km` | `0,03514` | `1,09007` |
| przesilenie grudniowe | `5/5` | `103,0948 km` | `0,05266` | `1,13548` |
| globalnie | `14/15` | `83,2288 km` | `0,18632` | `1,61700` |

Tor czerwcowy samodzielnie spełnia oba progi stałości. Marcowy i grudniowy są
nieznacznie poza progami wewnątrz dnia, natomiast główna niespójność powstaje
między sezonami: grudniowa tarcza jest rekonstruowana znacznie większa od
czerwcowej i marcowej.

Dla porównania kontrola `n=1` jest jeszcze mniej stała globalnie
(`CV=0,40665`, `max/min=4,62779`), ale kontrakt wymagał spełnienia absolutnych
progów, a nie tylko poprawy względem słabej kontroli. Poprawa nie zamienia więc
wyniku w `PASS`.

## Wniosek metodologiczny

Kontrola wielu restartów działa na dwóch poziomach:

- w skanie `R/Rbase=1,50` wykryła dwa różne minima i prawidłowo odrzuciła
  niejednoznaczny punkt,
- w pełnym C-2 potwierdziła, że obecny `FAIL` nie jest artefaktem wyboru
  minimum: wszystkie 75 celów jest zgodne między ziarnami.

Nie należy teraz przesuwać progu drogi, rozluźniać tolerancji tarczy ani
automatycznie próbować `R/Rbase=1,35`. Każdy kolejny kandydat lub rozszerzenie
rodziny wymaga nowego kontraktu zapisanego przed przebiegiem.

Maszynowy raport: `solver/results/v2-maxwell-full-c2.json`.
