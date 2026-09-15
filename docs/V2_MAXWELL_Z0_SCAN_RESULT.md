# Wynik skanu `z0` Maxwella v2

## Decyzja

Żaden z siedmiu wcześniej zadeklarowanych kandydatów nie przeszedł pełnej
bramki. Wynik to **0/7 PASS**, dlatego pełne C-2 pozostaje zablokowane.

Nie zamykamy całej rodziny Maxwella. Skan pokazał, że przesunięcie środka może
jednocześnie poprawić oba bieguny, lecz przy stałym `R` traci wtedy część
słonecznych dróg w przód. Ewentualna siatka `(R,z0)` wymaga osobnego kontraktu.

## Wynik liczbowy

Kontrola `n=1`:

- centra Słońca: `37,8288°`,
- biegun północny: `11,3545°`,
- biegun południowy: `141,7745°`.

| `z0/R` | Słońce RMS | N RMS | S RMS | Ważne grupy | Główna przyczyna FAIL |
|---:|---:|---:|---:|---:|---|
| `-0,40` | — | `16,0003°` | `119,0757°` | `10/15 + 1/2` | grudzień i S: droga/położenie |
| `-0,25` | — | `14,8523°` | `82,8184°` | `10/15 + 1/2` | grudzień i S: droga w przód |
| `-0,10` | — | `13,4536°` | `73,4435°` | `12/15 + 1/2` | droga w przód; jeden brak konsensusu |
| `+0,10` | `13,0323°` | `86,0659°` | `23,5132°` | `15/15 + 1/2` | N: droga w przód i RMS |
| `+0,25` | `12,6931°` | `124,1157°` | `22,8929°` | `15/15 + 1/2` | N: droga w przód i RMS |
| `+0,40` | — | `9,0076°` | `20,0501°` | `11/15 + 2/2` | cztery grupy Słońca: droga w przód |
| `0` | `15,3851°` | `12,4559°` | `24,0215°` | `15/15 + 2/2` | N: RMS o `9,70%` gorszy |

Kreska oznacza brak pełnej średniej: raport zachowuje wartości częściowe, ale
bramka nie pozwala nimi zastąpić niekompletnego zbioru.

## Najważniejsza informacja strukturalna

Hipoteza prostego, monotonicznego sprzężenia biegunów nie potwierdziła się.
Przy `z0/R=+0,40` oba bieguny jednocześnie spełniają próg RMS i drogę w przód:

- północ poprawia się o `20,67%`,
- południe poprawia się o `85,86%`,
- separacja biegunów wynosi `1,5550 rad = 89,09°`.

Ten kandydat nie przechodzi, ponieważ cztery z 15 grup słonecznych mają
ujemny odpowiednik drogi w przód. Z kolei `+0,10` i `+0,25` dają najlepsze
pełne wyniki Słońca, ale tracą fizyczną gałąź bieguna północnego.

Oznacza to, że pionowe przesunięcie działa w potrzebnym kierunku, lecz przy
zamrożonym promieniu nie istnieje punkt spełniający wszystkie ograniczenia.
Nie jest to ten sam wzorzec co degeneracja jednego centrum w poprzednich
rodzinach.

## Kontrole techniczne

- kontrola `z0=0` dokładnie odtworzyła wcześniejszy przebieg,
- każdy kandydat użył tych samych czterech ziaren i 16 restartów,
- wynik maszynowy był zapisywany po każdym punkcie,
- nie uruchomiono brzegów tarczy ani RK45,
- progi i kolejność punktów nie zostały zmienione.

Maszynowy raport: `solver/results/v2-maxwell-z0-scan.json`.
