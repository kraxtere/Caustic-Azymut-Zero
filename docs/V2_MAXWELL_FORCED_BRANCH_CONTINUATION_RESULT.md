# Wynik wymuszonej kontynuacji gałęzi Maxwella

## Werdykt

Zamrożony test kończy się **FAIL**, ponieważ nie wszystkie przypisania
`P/JPJ` są zgodne między ziarnami na ośmioosobowej wspólnej kohorcie.
Nie wolno zatem uznać pełnego rozkładu na część gładką i dyskretną za
wyznaczony.

Pozostałe trzy warunki kontraktu przechodzą:

- ta sama kohorta ośmiu obserwatorów jest użyta dla wszystkich celów,
- wszystkie czerwcowe i grudniowe tarcze istnieją w obu kontynuacjach,
- tożsamość multiplikatywna jest spełniona dokładnie w precyzji maszynowej.

## Co pozostaje wiarygodne

Wymuszona gałąź bezpośrednia `P` nie wymaga wyboru dyskretnego i jest
jednoznaczna. Dla tej samej kohorty daje:

| Wielkość | Wynik |
|---|---:|
| średnia średnica czerwca, `P` | `62,933732 km` |
| średnia średnica grudnia, `P` | `78,263887 km` |
| oczekiwany stosunek kątowy grudzień/czerwiec | `1,033013` |
| rezydualny czynnik gładkiej kontynuacji `G` | `1,203849` |
| rezydualna zmiana gładka | **`20,3849%`** |

To jest obecnie właściwa skala zadania dla przyszłej gładkiej poprawki:
powinna skompensować około `20,4%` na kontrolowanej kontynuacji, a nie surowe
`46,7745%` z rozwiązania przechodzącego przez granicę gałęzi.

Nie jest to jednak ścisły „udział procentowy” w pierwotnych `46,7745%`, bo
pierwotny wynik korzystał z różnych dwudziestoosobowych kohort sezonowych.
Iloraz `20,3849/46,7745` można podać jedynie jako orientacyjne `43,58%`, nie
jako wynik dekompozycji.

## Gdzie zawiodła część dyskretna

- grudzień 10:00: brak konsensusu dla centrum i wszystkich czterech brzegów,
- grudzień 16:00: brak konsensusu dla brzegu wschodniego,
- pozostałe cele: zgodne przypisania między ziarnami.

Wybranie jednego z lokalnych minimów mimo tego ostrzeżenia dawałoby średnią
grudniową `466,772819 km`, pozorny całkowity czynnik `7,179865` i mnożnik
gałęzi `5,964089`. Te liczby są zapisane audytowo w JSON-ie, ale są
**niewiarygodne interpretacyjnie** i nie stanowią wyniku fizycznego.

## Konsekwencja dla dalszej pracy

Nie dodajemy jeszcze parametru do `n(r)`. Następny test powinien zachować
ośmioosobową kohortę, ale zakotwiczyć etykiety gałęzi w stabilnych
dwudziestoosobowych rozwiązaniach C-2, zamiast ponownie wybierać je z
uboższego zbioru. Dopiero wtedy można domknąć liczbowo część dyskretną.

Niezależnie od tego projekt nowego parametru ma naturalną bazę multipolową:
dipol `P1(sin(delta))` jako pierwszy składnik oraz kwadrupol
`P2(sin(delta))` jako ewentualny drugi. Po implementacji pierwszą bramką
pozostaje C-3; pełne C-2 dopiero po braku regresji obu biegunów.

Maszynowy raport:
`solver/results/v2-maxwell-forced-branch-continuation.json`.
