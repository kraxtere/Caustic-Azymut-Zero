# Audyt geometrii gałęzi i hipotezy nawinięcia

## Wynik

Mnożnik `5,964089` jest tylko liczbowo bliski `6` — różnica względna wynosi
`0,5985%`. W obecnym modelu nie może on być indeksem nawinięcia:

- tor analityczny jest jawnie ograniczony do pierwszego przedziału
  `0 <= alpha <= pi`,
- największy kąt centralny w badanym przebiegu wynosi `2,056 rad < pi`,
- stan obserwacji jest pojedynczym bitem `P/JPJ`, a nie liczbą odbić lub
  nawinięć,
- algorytm nie posiada zmiennej całkowitej, która mogłaby przyjąć wartość 6.

Bliskość szóstki jest więc przypadkiem agregacji, nie ukrytą liczbą
topologiczną. Średnią grudniową zawyżają dwa różne zdarzenia:

| Chwila | Wybrana / bezpośrednia średnica | Efektywna odległość wybranej gałęzi | Co się dzieje |
|---|---:|---:|---|
| 10:00 | `1,731×` | `16 088 km` | wspólna sygnatura `00000011`, ale brak konsensusu restartów |
| 16:00 | `26,260×` | `206 413 km` | brzeg wschodni przechodzi na inną sygnaturę niż reszta tarczy |

O 11:30, 13:00 i 14:30 rozwiązanie grudniowe pozostaje bezpośrednie i
stosunek wynosi dokładnie `1`. To pojedynczy skok brzegu o 16:00, a nie sześć
okrążeń, dominuje w średnim mnożniku `5,964089`.

## Iloraz względem średnicy mapy

Dla każdej tarczy policzono

```text
f_eff = reconstructed_diameter / input_angular_diameter_rad
```

oraz `f_eff/(2 R_MAP)`. Diagnostyka bardzo dobrze wykrywa katastrofalny punkt
16:00 (`16,199` średnicy mapy) i słabszą anomalię 10:00 (`1,263`). Nie jest
jednak jeszcze legalnym twardym progiem fizycznym. Efektywna odległość
obrazowania jest lokalną pochodną odwzorowania kąt–długość; sama średnica
apertury nie stanowi ogólnego ograniczenia tej pochodnej. Także zwykły układ
optyczny może mieć ogniskową większą od apertury.

Twardy filtr wymaga wyprowadzenia maksymalnego powiększenia z konkretnego
odwzorowania stereograficznego Maxwella i dozwolonej domeny źródła. Do tego
czasu iloraz jest obowiązkową diagnostyką ostrzegawczą, ale nie kryterium
odrzucenia dobranym po zobaczeniu wyniku.

## Korekta bazy multipolowej

`P2(sin(delta))` jest parzyste i ma tę samą wartość przy obu przesileniach.
Nie może zmienić różnicy czerwiec–grudzień. Sezonową asymetrię mogą korygować
wyłącznie człony nieparzyste:

```text
P1(x) = x
P3(x) = (5x^3 - 3x) / 2
```

Przy `delta=±23,44°` człony `P1` i `P3` są zdegenerowane w jednym pomiarze:
`P3/P1 ≈ -1,105`. Przy `delta=±11,7°` stosunek wynosi około `-1,397`, więc
deklinacje pośrednie rozdzielają dipol od oktupolu. Równonoc zeruje wszystkie
człony nieparzyste i służy jako kontrola wspólnego poziomu oraz ewentualnych
składników parzystych.

## Co oznacza delta

Deklinacja źródła jest wyłącznie etykietą eksperymentu i argumentem
zmierzonej odpowiedzi `C(delta_source)`. Nie wolno użyć jej bezpośrednio w
polu. Statyczny ośrodek może zależeć od lokalnej współrzędnej geometrycznej:

```text
mu(x) = cos(theta(x)) = axial_coordinate(x) / radius(x)
```

Nowy składnik pola musi więc mieć postać zależną od `P1(mu)` lub później
`P3(mu)`, z radialną obwiednią, a nie od daty ani tożsamości Słońca. Daje to
test bez nowych parametrów: Księżyc lub dowolne inne źródło przechodzące przez
te same kierunki geometryczne musi otrzymać tę samą poprawkę.

## Następny test przed implementacją

Nie wystarczą same przesilenia. Zestaw identyfikacyjny musi zawierać tę samą
kohortę dla:

- równonocy `delta=0°`,
- pary pośredniej około `delta=±11,7°`,
- pary przesileniowej `delta=±23,44°`.

Najpierw należy rozdzielić `P1` od `P3` na tych punktach i wyprowadzić
niezależny limit powiększenia Maxwella. Dopiero potem wolno implementować
lokalną anizotropię i uruchomić C-3.

Maszynowy raport: `solver/results/v2-maxwell-branch-geometry-audit.json`.
