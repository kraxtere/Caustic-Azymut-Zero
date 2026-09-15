# Wynik skanu `epsilon` lokalnego dipola na C-3

## Werdykt

Zamrożoną bramkę przechodzą trzy amplitudy:

```text
epsilon = 0,10; 0,20; 0,40
```

Nie uruchomiono jeszcze testu skali ani C-2. Kontrakt nie przewidywał wyboru
jednego zwycięzcy spośród wielu wartości PASS, dlatego wszystkie trzy
pozostają kandydatami następnego etapu.

## Wyniki RMS krzywych

| `epsilon` | biegun N [km] | biegun S [km] | wynik |
|---:|---:|---:|---|
| `-0,40` | `1063,921` | `5711,349` | FAIL |
| `-0,20` | `1020,554` | `5390,683` | FAIL |
| `-0,10` | `998,671` | `5390,544` | FAIL |
| `-0,05` | `987,682` | `5459,335` | FAIL |
| `0,00` | `976,665` | `5592,806` | kontrola |
| `0,05` | `965,619` | `5616,912` | FAIL — południe gorsze |
| `0,10` | `954,546` | `5350,113` | **PASS** |
| `0,20` | `932,326` | `4821,343` | **PASS** |
| `0,40` | `887,622` | `3844,455` | **PASS** |

Względem `epsilon=0` punkt `0,40` poprawia RMS północy o `9,12%`, a południa
o `31,26%`. Nie jest to jeszcze kryterium wyboru amplitudy.

## Pozostałe warunki

Dla wszystkich trzech wartości PASS:

- wszystkie osiem startów dopasowania zbiegło,
- konkurencyjne minima mają wspólny punkt w granicy `1e-6 R`,
- źródła pozostają wewnątrz lustra i nad mapą,
- bieguny nie zapadają się w jeden punkt,
- wszystkie parametry toru zachowują wymagany margines od `0` i `pi`.

Największy rozrzut konkurencyjnych punktów wśród wartości PASS wynosi mniej
niż `0,005 km`, przy progu około `0,024 km`.

## Interpretacja

Znak jest rozstrzygnięty na tej siatce: mały dodatni dipol może jednocześnie
poprawić oba bieguny, ujemny nie. Punkt `0,05` pokazuje, że sama poprawa
północy nie wystarcza — all-or-nothing gate prawidłowo odrzuca kompromis,
który pogarsza południe.

Następny test powinien objąć wyłącznie `0,10`, `0,20`, `0,40` i kontrolę
`0,00`, na tanim zestawie skali przed pełnym C-2. Żadnego zagęszczania siatki
`epsilon` nie wykonujemy przed tym testem.

Maszynowy raport: `solver/results/v2-local-dipole-c3-scan.json`.

## Reprodukowalność wykonania

Przed uzyskaniem pierwszego punktu skanu poprawiono obsługę kroków pośrednich
integratora tuż poza zdarzeniem lustra. Pierwszy pełny przebieg został następnie
przerwany przed wypisaniem jakiegokolwiek punktu z powodu kosztu wielokrotnego
próbkowania tych samych krzywych. Próbki zostały zbuforowane, a iterację ICP
ograniczono technicznie bez zmiany zamrożonej siatki `epsilon`, startów, danych
ani kryteriów bramki. Tabela powyżej pochodzi z pierwszego ukończonego przebiegu.
