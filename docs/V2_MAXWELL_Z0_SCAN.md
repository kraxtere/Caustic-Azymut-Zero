# Zamrożony skan położenia `z0` Maxwella v2

## Uzasadnienie

Domyślne ustawienie Maxwella poprawiło centra Słońca i biegun południowy, ale
o `9,70%` pogorszyło biegun północny. Przed zmianą promienia sprawdzamy więc
wyłącznie pionowe położenie środka lustra. Skan rozstrzyga, czy poprawę obu
biegunów można uzyskać jednym `z0`, czy ich błędy są strukturalnie sprzężone.

Ten dokument i kod skanu mają zostać zapisane przed uruchomieniem kandydatów.

## Zamrożony projekt

- promień: `R = pi * R_MAP = 20015,086796 km`, bez zmian,
- `z0/R = -0,40; -0,25; -0,10; +0,10; +0,25; +0,40; 0`,
- przypadki niezerowe są liczone przed kontrolą `z0=0`,
- 15 centrów Słońca i oba bieguny C-3,
- 16 restartów dla każdego z ziaren `3, 17, 91, 2048`,
- bez brzegów tarczy C-2, optymalizacji `alpha`, RK45 i dopasowania `R`.

Zakres `|z0| <= 0,40R` utrzymuje wszystkich używanych obserwatorów wewnątrz
lustra. Skan nie stanowi jeszcze testu całej dwuwymiarowej rodziny `(R,z0)`.

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
identyczne jak w `V2_MAXWELL_CHEAP_GATE.md`.

## Decyzja po skanie

- co najmniej jeden `PASS`: najlepszy przechodzący kandydat może wejść do
  pełnego C-2 bez zmiany `R`,
- zero `PASS`, ale przeciwne trendy N/S: zapisujemy strukturalne sprzężenie i
  nie uruchamiamy pełnego C-2,
- zero `PASS` bez monotonicznego sprzężenia: ewentualny skan `(R,z0)` wymaga
  nowego, osobnego uzasadnienia i zamrożenia.
