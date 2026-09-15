# Wynik diagnostycznego skanu deklinacji Maxwella v2

## Decyzja

Zamrożona hipoteza globalnie gładkiej, ściśle monotonicznej skali od
`-23,44°` do `+23,44°` otrzymuje **NOT SUPPORTED**. Jeden z dziewięciu
punktów jest niejednoznaczny gałęziowo, więc nie wolno dopasować jednej
gładkiej funkcji przez cały zakres.

Jednocześnie siedmiopunktowy fragment stabilnej gałęzi od `-11,72°` do
`+23,44°` jest ściśle monotoniczny i ma liniowe `R²=0,9775`. Jest to
diagnostyka po wyniku, a nie zamiennik zamrożonego kryterium; pokazuje jednak,
że skala jest silnie związana z deklinacją tam, gdzie gałąź pozostaje stała.

## Wyniki

Stałe wejście wynosiło `0,2666°`; raportowana skala to odtworzona średnica
podzielona przez wejściową średnicę w radianach.

| Deklinacja | Ważna tarcza | Średnica | Skala km/rad | Min. `forward_sine` |
|---:|---|---:|---:|---:|
| `-23,44°` | tak | `85,1826 km` | `9153,42` | `0,6254` |
| `-17,58°` | **nie** | — | — | `0,5302` |
| `-11,72°` | tak | `101,2422 km` | `10879,12` | `0,4928` |
| `-5,86°` | tak | `94,1520 km` | `10117,23` | `0,4880` |
| `0,00°` | tak | `88,4189 km` | `9501,18` | `0,4730` |
| `+5,86°` | tak | `83,6260 km` | `8986,15` | `0,4530` |
| `+11,72°` | tak | `79,5560 km` | `8548,80` | `0,4247` |
| `+17,58°` | tak | `76,0936 km` | `8176,75` | `0,3944` |
| `+23,44°` | tak | `73,1764 km` | `7863,28` | `0,3660` |

## Granica gałęzi przy `-17,58°`

Cztery elementy tarczy — centrum, brzeg północny, wschodni i zachodni — nie
mają konsensusu punktu ani dokładnego przypisania `P/JPJ` między ziarnami.
Rozrzut punktów na `S^3` wynosi około `2576–2592 km`. Brzeg południowy jest
zgodny.

Wszystkie rozwiązania mają duży dodatni margines drogi, około `0,53`.
Niejednoznaczność nie pochodzi więc z przejścia przez zero `forward_sine`.
Jest osobną granicą minimów dyskretnych, podobną metodologicznie do przypadku
`R/Rbase=1,50`.

## Wniosek dla rodziny pola

Na stabilnym fragmencie `-11,72° ... +23,44°` skala maleje o `38,35%` i jest
dobrze opisana trendem monotonicznym. W połączeniu z `46,77%` niewyjaśnionej
zmiany sezonowej w skorygowanym C-2 wspiera to strukturalny związek skali z
deklinacją przy niezerowym `z0`.

Nie uzasadnia to automatycznego testu `R/Rbase=1,35`. Następna hipoteza
powinna mieć stopień swobody rozdzielający naprawę asymetrii biegunów od skali
deklinacyjnej. Kontrola gałęzi i drogi w przód pozostaje oddzielnym warunkiem.

Maszynowy raport: `solver/results/v2-maxwell-declination-scan.json`.
