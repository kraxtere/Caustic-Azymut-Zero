# Wynik taniej bramki Maxwella v2

## Decyzja

Zamrożony kandydat `R=20015,086796 km`, `centre=(0,0,0)` otrzymuje wynik
**FAIL**. Pełne C-2 pozostaje zablokowane. Jest to odrzucenie tego jednego,
wcześniej zadeklarowanego ustawienia, a nie całej rodziny Maxwella.

Kryteria zostały zapisane przed przebiegiem w `V2_MAXWELL_CHEAP_GATE.md`.
Raport maszynowy znajduje się w
`solver/results/v2-maxwell-cheap-gate.json`.

## Wyniki porównawcze

Wspólną metryką jest RMS różnicy między kierunkiem obserwowanym i kierunkiem
przewidzianym do zrekonstruowanego źródła. Kilometry płaskiej triangulacji i
kilometry na pomocniczej `S^3` są raportowane osobno, ale nie są ze sobą
porównywane.

| Cel | `n=1` | Maxwell | Zmiana | Bramka |
|---|---:|---:|---:|---|
| 15 centrów Słońca — średnia | `37,8288°` | `15,3851°` | `-59,33%` | PASS |
| północny biegun niebieski | `11,3545°` | `12,4559°` | `+9,70%` | **FAIL** |
| południowy biegun niebieski | `141,7745°` | `24,0215°` | `-83,06%` | PASS |

Wynik końcowy jest `FAIL`, ponieważ wszystkie trzy poprawy RMS były wymagane
jednocześnie.

## Pozostałe kontrole

- wszystkie 15 centrów i oba bieguny dały ważną rekonstrukcję,
- wszystkie drogi Maxwella spełniły warunek ruchu w przód,
- najmniejsza wartość `sin(alpha)` wyniosła `0,2620`,
- cztery ziarna dały identyczne najlepsze punkty; maksymalny rozrzut na `S^3`
  wyniósł `0 km`,
- wszystkie źródła leżały wewnątrz lustra i nad mapą,
- bieguny nie zapadły się w jedno źródło: ich separacja wyniosła
  `0,38238 rad = 21,9088°`, przy zamrożonym minimum `0,001 rad`.

Jedynym niespełnionym kryterium była poprawa północnego bieguna.

## Interpretacja

Analityczny pipeline działa stabilnie i nie odtworzył dwóch wcześniejszych
usterek: przecięć za obserwatorem ani zapadnięcia obu biegunów w jeden punkt.
Nie daje to jednak prawa do pełnego C-2, ponieważ domyślna skala i położenie
lustra pogarszają północny biegun względem `n=1`.

Ewentualny kolejny eksperyment powinien zostać zadeklarowany jako osobny tani
skan geometrii `(R,z0)`. Nie należy rozszerzać pełnego C-2 ani zmieniać progu
tej zakończonej bramki.
