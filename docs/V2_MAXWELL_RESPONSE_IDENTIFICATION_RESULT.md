# Wynik identyfikacji odpowiedzi multipolowej Maxwella

## Werdykt

Zamrożona identyfikacja kończy się **PASS** i wybiera minimalną bazę
nieparzystej odpowiedzi **`P1`**. Pole nie zostało w tym przebiegu zmienione.

Wszystkie dziewięć tarcz na wymuszonej gałęzi `P`:

- używa tej samej kohorty 20 obserwatorów,
- ma źródła wewnątrz lustra i nad mapą,
- zachowuje drogę w przód; najmniejszy `forward_sine` wynosi `0,3660`.

## Test predykcyjny `P1`

Nieparzystą odpowiedź zdefiniowano jako:

```text
O(delta) = [ln C(+delta) - ln C(-delta)] / 2
```

Współczynnik `a=0,661793` w `O=a P1(sin delta)` został wyznaczony wyłącznie
z pary `±23,44°`. Dla niewykorzystanej pary `±11,72°`:

| Wielkość | Wynik |
|---|---:|
| odpowiedź zmierzona | `0,120527` |
| przewidywanie `P1` | `0,134429` |
| błąd logarytmiczny | `0,013902` |
| odpowiednik multiplikatywny | `1,400%` |
| zamrożony limit | `2,000%` |

Model jednoparametrowy przechodzi. Największy błąd `P1` na wszystkich
czterech niezerowych parach również wynosi `0,013902`.

## Kontrola `P1+P3`

Dla kompletności rozwiązanie dwuskładnikowe wyznaczone z `±11,72°` i
`±23,44°` daje:

```text
a_P1 = 0,920259
a_P3 = 0,234031
```

Na zamrożonych punktach kontrolnych błędy wynoszą:

- `±5,86°`: `−0,000539`,
- `±17,58°`: `+0,001394`.

Model przechodzi, lecz nie zostaje wybrany: zgodnie z kontraktem dodatkowy
parametr nie jest dopuszczany, jeżeli `P1` sam spełnia próg predykcyjny.

## Składowa parzysta

Składowa

```text
E(delta) = [ln C(+delta) + ln C(-delta)] / 2
```

nie jest zerowa. Jej wartości dla `|delta|=5,86°, 11,72°, 17,58°, 23,44°`
wynoszą odpowiednio `−0,00355`, `−0,01490`, `−0,03653`, `−0,07404`.
Nie przypisujemy ich współczynnikowi dipolowemu. Mogą wynikać z parzystych
składników lokalnego pola lub z nieliniowości całego odwzorowania.

## Ważne ograniczenie interpretacji

Współczynnik `0,661793` opisuje odpowiedź jednego kontrolowanego układu
kierunków i obserwatorów. Nie jest współczynnikiem gotowego pola `n(x)`.
W szczególności amplitudy tego syntetycznego skanu nie wolno utożsamiać z
sezonowym `G=1,203849` uzyskanym dla innej wspólnej kohorty i rzeczywistych
godzin. Zgodność dotyczy wyboru minimalnej klasy nieparzystej odpowiedzi.

## Lokalność i następny krok

Test regresyjny potwierdza, że zmiana etykiety źródła przy zachowaniu tych
samych pozycji i kierunków nie zmienia rozwiązania. Przyszłe pole może zależeć
od lokalnego `mu(x)`, ale nie od `delta_source`, daty ani nazwy obiektu.

Następny etap to zaprojektowanie jednego lokalnego składnika dipolowego z
radialną obwiednią. Przed pełnym C-2 musi on przejść:

1. test krzyżowy na innym źródle bez refitu,
2. tanią bramkę C-3 bez regresji biegunów,
3. dopiero potem testy skali tarczy.

Maszynowy raport: `solver/results/v2-maxwell-response-identification.json`.
