# Wynik skanu promienia `R` Maxwella v2

## Decyzja

Dwa z sześciu wcześniej zadeklarowanych kandydatów przeszły niezmienioną
bramkę centrum Słońca i C-3. Wynik to **2/6 PASS**. Hipoteza skanu została
potwierdzona: zwiększenie promienia przy stałym bezwzględnym `z0` odzyskało
drogi słoneczne w przód bez utraty poprawy obu biegunów.

Do pełnego C-2 zostaje promowany kandydat `R/Rbase=1,20`, ponieważ spośród
przechodzących punktów ma niższy RMS dla Słońca oraz obu biegunów, większy
minimalny margines drogi w przód i większą separację biegunów niż `1,35`.
Pełne C-2 nie jest częścią tego przebiegu i wymaga osobnego, zapisanego
kontraktu.

## Wynik liczbowy

Stałe dla całego skanu:

- `Rbase = 20015,086796 km`,
- `z0 = 8006,034718 km`, bez skalowania wraz z `R`,
- kontrola `n=1`: Słońce `37,8288°`, N `11,3545°`, S `141,7745°`.

| `R/Rbase` | `z0/R` | Słońce RMS | N RMS | S RMS | Ważne grupy | Wynik |
|---:|---:|---:|---:|---:|---:|---|
| `1,05` | `0,381` | — | `9,1665°` | `20,9862°` | `11/15 + 2/2` | FAIL: cztery drogi słoneczne wstecz |
| `1,10` | `0,364` | — | `9,3116°` | `21,8569°` | `12/15 + 2/2` | FAIL: trzy grupy Słońca, w tym brak konsensusu |
| **`1,20`** | **`0,333`** | **`15,0900°`** | **`9,5656°`** | **`23,4738°`** | **`15/15 + 2/2`** | **PASS — wybrany** |
| `1,35` | `0,296` | `15,7114°` | `9,8722°` | `24,0386°` | `15/15 + 2/2` | PASS |
| `1,50` | `0,267` | — | `10,1106°` | `24,4888°` | `14/15 + 2/2` | FAIL: brak konsensusu jednej grupy |
| `1,00` | `0,400` | — | `9,0076°` | `20,0501°` | `11/15 + 2/2` | FAIL: kontrolne cztery drogi wstecz |

Kreska oznacza brak pełnej średniej; częściowy RMS pozostaje w raporcie JSON,
ale nie może zastąpić kompletnego zbioru.

## Margines wybranego punktu

Dla `R/Rbase=1,20`, czyli `R=24018,104155 km`:

- Słońce poprawia się względem `n=1` o `60,11%`,
- biegun północny poprawia się o `15,76%`,
- biegun południowy poprawia się o `83,44%`,
- minimalny `forward_sine` na całym zbiorze wynosi `0,220873`,
- maksymalny rozrzut wyniku między ziarnami wynosi `0 km`,
- separacja rekonstruowanych biegunów wynosi `82,2320°`, daleko od progu
  degeneracji `0,0573°`.

Kandydat `1,35` także przechodzi, lecz wszystkie trzy RMS są nieco wyższe,
minimalny margines drogi w przód jest niższy (`0,181171`), a separacja
biegunów mniejsza (`76,7419°`). Wybór `1,20` nie wymaga więc wtórnej funkcji
celu dopasowanej po obejrzeniu wyniku: dominuje drugi punkt we wszystkich tych
diagnostykach.

## Granice gałęzi

Skan potwierdza, że przestrzeń nie jest gładka. Przy `1,50` wszystkie drogi
są skierowane w przód, ale grupa Słońca z `2026-12-21 16:00 UTC` ma dwa
konkurencyjne minima: ziarna `3,17` wybierają 10 gałęzi lustrzanych, a
`91,2048` wybierają 9. Punkty na `S^3` różnią się o `2005,38 km`, więc
przedrejestrowana kontrola konsensusu prawidłowo odrzuca kandydata.

Nie jest to zmiana liczby literalnych wielokrotnych odbić. Adapter używa
pierwszego interwału wielkiego okręgu i co najwyżej jednego złożenia lustra;
nieciągłość pochodzi z dyskretnego przypisania obserwatorów do `P` albo
`JPJ`.

## Kontrole techniczne

- kontrola `R/Rbase=1,00` dokładnie odtworzyła punkt `z0/R=0,40`,
- wszystkie sześć punktów i kryteria były zapisane w commicie przed runem,
- każdy kandydat użył tych samych czterech ziaren i 16 restartów,
- wynik był zapisywany po każdym punkcie,
- nie uruchomiono brzegów tarczy C-2 ani RK45.

Maszynowy raport: `solver/results/v2-maxwell-radius-scan.json`.
