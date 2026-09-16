# Zamrożona tania bramka skali lokalnego dipola

## Cel i zakres

Test rozstrzyga, czy amplitudy `epsilon=0,10`, `0,20`, `0,40`, które przeszły
C-3, poprawiają transfer skali tarczy bez pełnego C-2. `epsilon=0` jest
kontrolą. Parametry `R=1,20 Rbase` i `z0=0,40 Rbase` pozostają zamrożone.

Używamy jednej wspólnej kohorty obserwatorów, stałego promienia wejściowego
`0,2666 deg` oraz pięciu deklinacji:

```text
-23,44; -11,72; 0; +11,72; +23,44 deg
```

Dla każdej deklinacji rekonstruujemy środek i cztery brzegi tarczy numerycznym
propagatorem lokalnego dipola. To 25 celów na amplitudę, wobec pełnych torów
czasowych C-2.

## Metryki skali

Dla każdej tarczy liczymy średnicę jako średnią średnic N-S i E-W, a następnie:

- współczynnik zmienności pięciu średnic,
- bezwzględną logarytmiczną asymetrię skali pary `+-11,72 deg`,
- bezwzględną logarytmiczną asymetrię skali pary `+-23,44 deg`.

Stały wejściowy rozmiar kątowy oznacza, że ideałem dla każdej z tych metryk
jest zero.

## Bramka all-or-nothing

Niezerowa amplituda przechodzi wyłącznie, jeśli jednocześnie:

1. wszystkie trzy metryki skali są ściśle mniejsze niż przy `epsilon=0`,
2. wszystkie 25 dopasowań zachowuje konsensus konkurencyjnych minimów,
3. wszystkie źródła leżą wewnątrz lustra i nad mapą,
4. wszystkie parametry toru zachowują margines `alpha >= 1e-4`,
5. wszystkie tarcze mają `axis_ratio <= 1,10` i znormalizowane przesunięcie
   środka `<= 0,05`, zgodnie z zamrożonymi progami pełnego C-2.

Nie wybieramy amplitudy na podstawie samego najniższego RMS C-3. Jeżeli kilka
punktów przejdzie, wszystkie pozostają kandydatami; pełne C-2 wymaga osobnej
decyzji. Siatki nie zagęszczamy po zobaczeniu wyniku.

