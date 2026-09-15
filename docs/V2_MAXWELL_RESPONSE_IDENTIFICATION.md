# Zamrożony kontrakt identyfikacji odpowiedzi multipolowej

## Granica fizyczna

Badana deklinacja `delta_source` jest wyłącznie parametrem wejściowego
kierunku i etykietą zmierzonej odpowiedzi. Nie może być argumentem pola.
Każdy przyszły składnik ośrodka musi zależeć tylko od lokalnego stanu promienia
i lokalnej pozycji, np. od:

```text
mu(x) = cos(theta(x)) = axial_coordinate(x) / radius(x)
```

oraz od radialnej obwiedni. Data, nazwa obiektu i jego deklinacja nie mogą być
przekazane do funkcji `n(x)`.

## Zestaw identyfikacyjny

Używamy istniejącej wspólnej kohorty 20 obserwatorów, jednej chwili i stałego
promienia wejściowego `0,2666°`. Wszystkie tarcze są liczone na wymuszonej
gałęzi bezpośredniej `P`, aby pomiar gładkiej odpowiedzi nie przechodził przez
granicę `P/JPJ`.

Główne punkty identyfikacyjne:

- `delta=0°`,
- `delta=±11,72°`,
- `delta=±23,44°`.

Punkty `±5,86°` i `±17,58°` są zamrożonym zbiorem kontrolnym, którego nie
używa się do wyznaczenia współczynników modelu `P1+P3`.

## Odpowiedź i rozdzielenie parzystości

Dla skali transferu `S(delta)` definiujemy multiplikatywną korektę
`C(delta)=S(0)/S(delta)` oraz `L(delta)=ln C(delta)`. Dla każdej pary:

```text
O(delta) = [L(+delta) - L(-delta)] / 2
E(delta) = [L(+delta) + L(-delta)] / 2
```

`O` jest odpowiedzią nieparzystą istotną dla asymetrii sezonowej. `E` jest
raportowane oddzielnie i nie może zostać przypisane do parametru nieparzystego.

## Kolejność modeli

1. Jeden parametr `O=a P1(sin delta)` jest ustalany wyłącznie z pary
   `±23,44°` i przewiduje wynik przy `±11,72°`.
2. Jeżeli błąd predykcji przekracza `ln(1,02)`, dopuszcza się
   `O=a P1+b P3`, wyznaczone z par `±11,72°` i `±23,44°`.
3. Model dwuskładnikowy przechodzi tylko wtedy, gdy na niewykorzystanych
   parach `±5,86°` i `±17,58°` największy błąd bezwzględny nie przekracza
   `ln(1,02)`.

To identyfikuje kształt empirycznej odpowiedzi, nie gotową postać `n(x)`.

## Darmowy test lokalności

Solver musi zwrócić identyczny wynik dla dwóch grup mających te same pozycje
obserwatorów i kierunki, ale różne etykiety źródła. Po późniejszej
implementacji pole musi przejść mocniejszy test krzyżowy: Księżyc, gwiazda lub
syntetyczne źródło przechodzące przez te same kierunki geometryczne otrzymuje
tę samą poprawkę bez refitu i bez nowego parametru.

## Kolejność po identyfikacji

Identyfikacja nie autoryzuje jeszcze zmiany pola. Najpierw wybieramy minimalną
bazę odpowiedzi, potem projektujemy lokalny składnik `n(x)`, a po jego
implementacji uruchamiamy C-3. Pełne C-2 pozostaje ostatnim krokiem.
