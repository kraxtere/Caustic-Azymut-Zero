# Zamrożony pełny test C-2 Maxwella v2

## Status przed uruchomieniem

Kontrakt dotyczy kandydata wybranego przez wcześniej zapisany skan promienia:

- `R = 1,20 * Rbase = 24018,104155 km`,
- `z0 = 0,40 * Rbase = 8006,034718 km`,
- `z0/R = 1/3`,
- bez dalszego dopasowania parametrów, RK45 ani optymalizacji po wyniku.

Ten dokument, implementacja walidatora i testy muszą znaleźć się na `main`
przed pierwszym uruchomieniem pełnego zbioru C-2.

## Projekt obserwacyjny

Walidator zachowuje projekt z zamknięcia v1:

- 64 kandydatów obserwatorów na siatce `8 x 8`,
- trzy dzienne tory: równonoc marcowa oraz przesilenia czerwcowe i grudniowe,
- pięć chwil na tor w odstępach 90 minut,
- stała kohorta obserwatorów w obrębie całego dziennego toru,
- pięć kierunków na chwilę: środek oraz N, S, E i W brzegu tarczy,
- łącznie 15 rekonstruowanych tarcz i 75 osobnych celów,
- ponowiona kontrola obu biegunów C-3,
- kontrola `n=1` na dokładnie tych samych kohortach.

Każdy cel jest triangulowany analitycznie na `S^3` z 16 restartami dla
każdego z ziaren `3, 17, 91, 2048`.

## Uściślenie historii progów

Walidator v1 raportował `diameter_coefficient_of_variation` oraz
`diameter_max_to_min_ratio`, ale dokument `V1_CLOSURE.md` jawnie stwierdzał,
że liczbowe tolerancje naukowe nie były jeszcze ustalone. Poniższe wartości są
więc pierwszymi zamrożonymi progami ilościowymi C-2, a nie zmianą istniejących
wartości po obejrzeniu wyniku pełnego testu.

## Zamrożona bramka C-2

Kandydat przechodzi tylko wtedy, gdy wszystkie warunki zachodzą jednocześnie:

1. wszystkie 15 tarcz i wszystkie 75 celów mają ważną rekonstrukcję,
2. średni kierunkowy RMS piętnastu środków jest niższy niż dla `n=1`,
3. globalnie i osobno w każdym dziennym torze:
   - `diameter_coefficient_of_variation <= 0,05`,
   - `diameter_max_to_min_ratio <= 1,10`,
4. każda z 15 tarcz spełnia:
   - `axis_ratio <= 1,10`,
   - `normalised_centre_offset <= 0,05`,
5. każdy z 75 celów ma ten sam najlepszy punkt pomiędzy czterema ziarnami z
   dokładnością `1e-6 R` na `S^3`,
6. każdy z 75 celów ma identyczne przypisanie obserwatorów do gałęzi `P/JPJ`
   pomiędzy czterema ziarnami; zgodność samego punktu nie zastępuje zgodności
   przypisań,
7. każdy z 75 celów ma `minimum_forward_sine >= sin(10 deg) = 0,173648`;
   jest to jawny bufor 10 stopni od granicy drogi wstecz, a nie tylko test
   znaku,
8. wszystkie źródła leżą wewnątrz lustra i nie poniżej mapy.

Warunki 6 i 7 są niezależne. `forward_sine` nie mierzy odległości od granicy
między minimami dyskretnymi. Pokazał to skan: punkt `R/Rbase=1,35` miał
minimum `0,181171` i pełny konsensus, a `1,50` miał podobne `0,182406`, lecz
dwa rozwiązania gałęzi różniące się o `2005,38 km` na `S^3`.

## Regresja C-3

Oba bieguny muszą ponownie:

- mieć ważną rekonstrukcję i RMS niższy niż odpowiadające `n=1`,
- zachować konsensus punktu oraz pełnego przypisania gałęzi między ziarnami,
- mieć wszystkie drogi w przód i źródła wewnątrz lustra, nie poniżej mapy,
- pozostać rozdzielone o więcej niż `1e-3 rad`.

Bufor `10 deg` jest kryterium nowego zbioru brzegów C-2. C-3 zachowuje
wcześniejszy warunek dodatniej drogi, aby nie zmieniać po fakcie bramki, którą
bieguny już przeszły.

## Decyzja

- `PASS`: Maxwell `R/Rbase=1,20`, `z0/Rbase=0,40` przechodzi pełne C-2 i C-3;
  można przejść do gęstszej walidacji poza próbką bez ponownego strojenia,
- `FAIL`: raport wskazuje osobno niekompletną tarczę, zmienność średnicy,
  deformację kształtu, utratę bufora drogi, brak konsensusu punktu lub gałęzi
  i regresję C-3. Nie wolno uśredniać ani pomijać wadliwego momentu.

Planowane polecenie po utrwaleniu kontraktu:

```bash
./.venv/Scripts/python.exe -m solver.validate_maxwell_c2 \
  --output solver/results/v2-maxwell-full-c2.json
```
