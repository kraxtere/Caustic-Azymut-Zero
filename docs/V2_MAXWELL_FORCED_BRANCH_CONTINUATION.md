# Zamrożony test wymuszonej kontynuacji gałęzi Maxwella

## Cel

Przed dodaniem nowego parametru do `n(r)` rozdzielamy sezonową rozbieżność
`46,7745%` na:

1. gładką zmianę skali na kontynuowanej gałęzi bezpośredniej `P`,
2. mnożnik wywołany dyskretnym przejściem na gałąź `JPJ`.

Test nie zmienia pola i nie dopasowuje żadnego nowego parametru.

## Kontrola kohorty

Używamy przecięcia stałych kohort obserwatorów z trzech torów C-2. To daje
osiem tych samych pozycji dla każdej chwili, pory roku i części tarczy.
Każda para „gałąź wybrana / gałąź wymuszona” jest zatem liczona z dokładnie
tych samych kierunków obserwacyjnych.

## Dwie rekonstrukcje tego samego celu

Dla każdego centrum i czterech brzegów tarczy:

- `selected`: istniejący solver z wieloma restartami wybiera przypisanie
  `P/JPJ`, po czym to przypisanie jest zamrażane i liczone jedną dekompozycją
  `4x4`,
- `direct`: wszystkie obserwacje są wymuszone na `P`, bez kroku dyskretnego.

W kontynuacji bezpośredniej zachowujemy rozwiązanie nawet przy ujemnym
`forward_sine`. To kontrfaktyczny tor matematyczny służący do pomiaru
gładkiego składnika; warunki fizyczne są raportowane osobno i nie są używane
do cenzurowania średnicy.

## Zamrożona dekompozycja

Niech `D*` oznacza grudniową średnicę z gałęzi wybranej, `DP` grudniową
średnicę z wymuszonej gałęzi bezpośredniej, `JP` czerwcową średnicę
bezpośrednią, a `q` oczekiwany stosunek średnic kątowych Słońca z efemerydy.

```text
T = D* / JP / q                 całkowity niewyjaśniony czynnik
G = DP / JP / q                 gładka kontynuacja bezpośrednia
B = D* / DP                     dyskretny mnożnik gałęzi
T = G * B                       kontrola tożsamości
```

Raport podaje czynniki `T`, `G`, `B`, błąd tożsamości oraz udziały
logarytmiczne `ln(G)/ln(T)` i `ln(B)/ln(T)`. Nie wolno przedstawiać udziałów
procentowych jako zwykłej sumy, ponieważ rozkład jest multiplikatywny.

## Warunki wiarygodności

- jedna identyczna kohorta we wszystkich celach,
- zgodne przypisania gałęzi pomiędzy wszystkimi ziarnami dla każdego celu,
- pięć kompletnych tarcz dla czerwca i grudnia w obu kontynuacjach,
- błąd `T-G*B` na poziomie precyzji maszynowej.

## Następny krok po wyniku

Dopiero wynik `G` określa, jak silną gładką korektę ma realizować nowy
parametr. Po jego implementacji pierwszym testem jest tania bramka C-3:
oba bieguny muszą nadal bić `n=1`, zachować kierunek w przód i pozostać
rozdzielone. Pełne C-2 wolno uruchomić dopiero po braku regresji C-3.
