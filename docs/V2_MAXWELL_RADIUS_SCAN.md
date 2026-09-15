# Zamrożony skan promienia `R` Maxwella v2

## Uzasadnienie

Przy stałym `R = pi * R_MAP` punkt `z0/R = +0,40` po raz pierwszy poprawił
oba bieguny jednocześnie względem `n=1`. Nie przeszedł jednak bramki, ponieważ
cztery z piętnastu grup słonecznych utraciły drogę w przód. Sprawdzamy teraz
wyłącznie, czy zwiększenie `R` przy zachowaniu tego samego bezwzględnego
położenia środka odsuwa granicę gałęzi od tych czterech przypadków bez utraty
poprawy biegunów.

Skoki bieguna N przy `z0/R = +0,10` i `+0,25` nie wynikają z wielokrotnych
odbić: adapter śledzi tylko pierwszy interwał i co najwyżej jedno złożenie
lustra. Diagnostyka wykazała skok liczby przypisań `JPJ` z `0` do `8`, następnie
`16` i z powrotem `0`, wraz z ujemnym warunkiem drogi w przód. Luka widmowa
pozostała wyraźna. Jest to zatem granica dyskretnej gałęzi `P/JPJ`, a nie
niestabilność dekompozycji własnej.

Ten dokument i kod skanu mają zostać zapisane przed uruchomieniem kandydatów.

## Zamrożony projekt

- promień bazowy: `Rbase = pi * R_MAP = 20015,086796 km`,
- stałe bezwzględne `z0 = +0,40 * Rbase = 8006,034718 km`,
- `R/Rbase = 1,05; 1,10; 1,20; 1,35; 1,50; 1,00`,
- większe promienie są liczone przed kontrolą `R/Rbase=1,00`,
- 15 centrów Słońca i oba bieguny C-3,
- 16 restartów dla każdego z ziaren `3, 17, 91, 2048`,
- bez brzegów tarczy C-2, optymalizacji `alpha`, RK45 i dopasowania `z0`.

Ponieważ `z0` jest stałe w kilometrach, odpowiadające wartości `z0/R` maleją
od około `0,381` do `0,267` wraz ze wzrostem promienia. Skan jest jednostronny
i testuje konkretną hipotezę przesunięcia granicy gałęzi; nie stanowi pełnego
przeszukania rodziny `(R,z0)`.

## Niezmieniona bramka

Każdy kandydat przechodzi wyłącznie wtedy, gdy jednocześnie:

1. wszystkie grupy mają ważną, niedegenerowaną rekonstrukcję,
2. średni kierunkowy RMS centrów Słońca jest ściśle niższy niż dla `n=1`,
3. kierunkowy RMS każdego bieguna osobno jest ściśle niższy niż dla `n=1`,
4. wszystkie drogi są skierowane w przód,
5. cztery ziarna są zgodne do `1e-6 R`,
6. źródła leżą wewnątrz lustra i nie poniżej mapy,
7. separacja biegunów przekracza `1e-3 rad`.

Kontrola `n=1`, kohorty obserwatorów, metryka kątowa i wszystkie tolerancje są
identyczne jak w `V2_MAXWELL_CHEAP_GATE.md` oraz skanie `z0`.

## Decyzja po skanie

- co najmniej jeden `PASS`: najlepszy przechodzący kandydat może wejść do
  pełnego C-2,
- zero `PASS`, a odzyskanie drogi słonecznej psuje co najmniej jeden biegun:
  zapisujemy sprzężenie `R` z wymaganiami Słońce/C-3 i nie uruchamiamy C-2,
- zero `PASS` z innym wzorcem: wynik opisujemy bez rozszerzania siatki po
  obejrzeniu danych; każda dalsza rodzina wymaga nowego kontraktu.
