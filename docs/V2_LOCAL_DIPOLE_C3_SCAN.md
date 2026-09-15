# Zamrożony tani skan `epsilon` lokalnego dipola na C-3

## Zakres

Test obejmuje wyłącznie północny i południowy biegun niebieski. Nie liczy
Słońca ani tarczy C-2. Parametry `R=1,20 Rbase` i `z0=0,40 Rbase` pozostają
zamrożone.

Siatka amplitudy:

```text
epsilon = -0.40, -0.20, -0.10, -0.05, 0,
           0.05,  0.10,  0.20,  0.40
```

## Dopasowanie krzywych

Dla każdego obserwowanego kierunku budowana jest pełna numeryczna krzywa
`0<=alpha<=pi`. Wspólny punkt i parametry `alpha_i` są dopasowywane
naprzemiennie: najbliższy punkt każdej krzywej do aktualnego źródła, następnie
średnia punktów. Start podstawowy pochodzi z analitycznego rozwiązania `4x4`
przy `epsilon=0`. Cztery deterministycznie perturbowane i trzy równomierne
starty sprawdzają konkurencyjne minima. Rozwiązania nie są uśredniane między
minimami. Za konkurencyjne uznaje się minima o średnim kwadracie residuum nie
większym niż `best + max(0,01*best, 1e-12 R^2)`.

## Bramka

`epsilon=0` jest kontrolą. Niezerowy kandydat przechodzi wyłącznie, jeśli:

1. RMS odległości krzywych jest ściśle mniejszy od kontroli jednocześnie dla
   obu biegunów,
2. wszystkie konkurencyjne najlepsze restarty wskazują ten sam punkt w
   granicy `1e-6 R`,
3. źródła leżą wewnątrz lustra i nad mapą,
4. oba bieguny pozostają rozdzielone o co najmniej `1e-3 R`,
5. wszystkie `alpha_i` leżą wewnątrz pierwszego przedziału z marginesem
   `1e-4 rad`.

Brak kandydata spełniającego wszystkie warunki zatrzymuje dipol przed testem
skali. Progów i siatki nie zmieniamy po wyniku.
