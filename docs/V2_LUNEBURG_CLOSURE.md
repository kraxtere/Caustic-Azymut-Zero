# Zamknięcie hybrydy Luneburga v2

## Zakres decyzji

Zamykamy sferycznie symetryczny profil Luneburga umieszczony jako kula lub
czasza nad azymutalną płaszczyzną, z dwoma swobodnymi parametrami geometrycznymi:
promieniem `R` i pionowym położeniem środka `z0`.

Jest to falsyfikacja zadeklarowanej rodziny hybrydowej i jej procedury
przeszukiwania, a nie twierdzenie, że klasyczna soczewka Luneburga nie ma swojej
znanej własności ogniskowania. Natywne testy analityczne nadal przechodzą i
pozostają w repo jako kontrola implementacji.

## Zamrożona bramka

Kandydat mógł przejść do pełnego C-2 wyłącznie wtedy, gdy jednocześnie:

1. wszystkie 15 środków Słońca i oba bieguny miały poprawne promienie oraz
   triangulację,
2. średni RMS środków Słońca był ściśle niższy niż dla `n=1`,
3. RMS każdego bieguna osobno był ściśle niższy niż dla `n=1`,
4. każde `minimum_forward_distance_km` było nieujemne.

Kontrole `n=1` wynosiły:

| Cel | RMS |
|---|---:|
| 15 środków Słońca — średnia | `5594,790 km` |
| północny biegun niebieski | `1194,594 km` |
| południowy biegun niebieski | `14667,618 km` |

## Etap 1 — przesunięcie środka

Przy `R=20015,087 km` sprawdzono `z0/R` równe `-0,75`, `-0,5`, `-0,25`,
`0,25`, `0,5`, `0,75` oraz skorygowaną kontrolę `0`.

Żaden z siedmiu punktów nie przeszedł bramki. Dodatnie przesunięcia dawały
kompletny zbiór, ale wszystkie trzy RMS były gorsze od `n=1`, a wspólne punkty
pozostawały za częścią promieni. Ujemna gałąź zbliżała częściowe wyniki do
kontroli, lecz traciła promienie. To uzasadniło jeden wcześniej zadeklarowany
lokalny skan promienia i położenia środka.

## Etap 2 — lokalna siatka `(R,z0)`

Sprawdzono iloczyn:

- `R/Rbase = 1,2; 1,35; 1,5`,
- `z0/Rbase = -0,9; -0,75; -0,6`.

Wynik: **0 z 9 kandydatów przeszło bramkę**.

- wszystkie dziewięć punktów miało niekompletny zbiór środków Słońca,
- w ośmiu punktach biegun północny nie miał poprawnej rekonstrukcji,
- jedyny ważny wynik bieguna północnego miał RMS `19154,504 km`, czyli
  `16,034×` kontrolę,
- najlepszy częściowy średni RMS Słońca wynosił `12656,208 km`, czyli
  `2,262×` kontrolę,
- najlepszy RMS bieguna południowego wynosił `15953,465 km`, czyli
  `1,088×` kontrolę, a jego minimalna odległość w przód nadal była ujemna:
  `-15259,008 km`,
- żaden kandydat nie spełnił żadnego kryterium poprawy RMS ani pełnego warunku
  odległości w przód.

## Decyzja

Nie uruchamiamy pełnego C-2 i nie rozszerzamy siatki. Rodzina otrzymuje status
`v2-falsified-hybrid`. Implementacja, natywne rozwiązania analityczne,
walidator i skaner pozostają dostępne wyłącznie jako odtwarzalny punkt
odniesienia.

Maszynowe wyniki:

- `solver/results/v2-luneburg-z0-scan.json`,
- `solver/results/v2-luneburg-negative-local-grid.json`.

Głównym kierunkiem pozostaje dokładny profil Maxwella z jawnym lustrem. Jego
adaptacja wymaga osobnego kontraktu propagacji: promienie nie przechodzą do
zewnętrznego obszaru asymptotycznego, więc odbicie i sposób rekonstrukcji
wspólnego punktu na zakrzywionych torach muszą zostać zdefiniowane i
przetestowane przed użyciem obserwacyjnego C-2/C-3.
