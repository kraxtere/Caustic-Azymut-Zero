# Skorygowany wynik pełnego C-2 Maxwella v2.1

## Decyzja

Po zastąpieniu stałego promienia Słońca wartością zależną od daty kandydat
`R/Rbase=1,20`, `z0/Rbase=0,40` nadal otrzymuje **FAIL**. Wynik nie zależy od
błędnego wymagania zerowej zmiany sezonowej.

## Właściwa rozbieżność sezonowa

Efemeryda daje dla użytych torów średnią wejściową średnicę kątową:

- marzec: `0,535420°`,
- czerwiec: `0,524678°`,
- grudzień: `0,541999°`.

Stosunek grudzień/czerwiec na wejściu wynosi `1,033013`, czyli oczekiwana
zmiana sezonowa to `+3,3013%` z poprawną fazą.

Odtworzona średnica fizyczna wynosi:

- marzec: `74,9418 km` dla czterech ważnych tarcz,
- czerwiec: `69,1177 km`,
- grudzień: `104,7962 km`.

Stosunek grudzień/czerwiec wynosi `1,516200`, czyli `+51,6200%`. Po
podzieleniu przez znaną zmianę wejściową pozostaje:

```text
1,516200 / 1,033013 - 1 = 0,467745
```

Ostatecznie **46,7745% zmiany skali pozostaje niewyjaśnione**. To jest liczba
do dalszej diagnozy geometrii `z0`, zamiast surowego globalnego CV ze starego
przebiegu.

## Stałość wewnątrzdobowa

| Tor | Ważne tarcze | CV | Max/min | Wynik progów dobowych |
|---|---:|---:|---:|---|
| równonoc marcowa | `4/5` | `0,05852` | `1,15322` | FAIL |
| przesilenie czerwcowe | `5/5` | `0,03514` | `1,09006` | PASS |
| przesilenie grudniowe | `5/5` | `0,05266` | `1,13549` | FAIL |

Rozdzielenie progów niczego nie ukrywa: czerwiec przechodzi ostry test
dobowy, marzec i grudzień pozostają nieznacznie powyżej obu tolerancji.

## Pozostałe kontrole

- ten sam `west_limb` równonocy marcowej o `10:00 UTC` pozostaje nieważny:
  `minimum_forward_sine=-0,778662`,
- pozostałe 74 cele przekraczają bufor `10°`,
- konsensus punktu i pełnych przypisań `P/JPJ`: `75/75`,
- regresja C-3: PASS,
- średni RMS centrów: `15,0900°` wobec `37,8288°` dla `n=1`,
- największy `axis_ratio` ważnej tarczy: `1,103568` przy progu `1,10`,
- największy znormalizowany błąd środka: `0,001916`, wyraźnie poniżej `0,05`.

Maszynowy raport: `solver/results/v2-maxwell-full-c2-corrected.json`.
