# Wynik diagnostyki basenów `delta=-11,72 deg`

## Werdykt

Niejednoznaczność restartów jest realna, ale **nie wyjaśnia złego kształtu
tarczy**. Wszystkie `4^5 = 1024` kombinacje reprezentantów klastrów pięciu
elementów tarczy pozostają wyraźnie powyżej limitu `axis_ratio=1,10`.

```text
minimum axis_ratio = 1,286131
maximum axis_ratio = 1,317694
```

Konflikt skala–kształt jest zatem odporny na wykryte wybory rozwiązania w tym
reprezentatywnym przypadku.

## Struktura niejednoznaczności

Każdy z pięciu elementów tarczy dał cztery klastry w ośmiu zamrożonych
restartach. Gęsty przekrój pomiędzy startem analitycznym i startem z innego
klastra został przez próg `1e-6 R` podzielony na 8–11 kolejnych segmentów:

| element | segmenty | rozpiętość źródeł [km] | zakres RMS [km] |
|---|---:|---:|---:|
| środek | `11` | `0,4207` | `1,10e-5` |
| brzeg N | `8` | `0,2660` | `4,54e-6` |
| brzeg S | `10` | `0,4497` | `1,23e-5` |
| brzeg E | `11` | `0,4317` | `1,15e-5` |
| brzeg W | `10` | `0,2854` | `5,14e-6` |

Etykiety segmentów zmieniają się monotonicznie wzdłuż każdego przekroju, a
RMS pozostaje praktycznie stały. To nie wygląda jak kilka izolowanych minimów
rozdzielonych barierami, lecz jak niemal płaska dolina rozwiązań, którą próg
klastrowania tnie na kolejne fragmenty.

## Wpływ na tarczę

Po wykorzystaniu czterech klastrów faktycznie osiągniętych przez pierwotne
restarty:

- `axis_ratio`: `1,286131–1,317694`,
- średnia średnica: `87,002–88,201 km`,
- kombinacje spełniające `axis_ratio <= 1,10`: `0/1024`.

Wybór miejsca w płaskiej dolinie zmienia liczby, ale nie zmienia werdyktu.
Dotychczasowy warunek konsensusu poprawnie wykrywa nieidentyfikowalność punktu
źródłowego, natomiast nie wolno interpretować każdego przekroczenia progu jako
osobnej gałęzi topologicznej.

## Decyzja

Nie ma podstaw do ponownego uruchamiania skanu multipoli z luźniejszym
kryterium konsensusu. Po oczyszczeniu artefaktu basenów konflikt kształtu
pozostaje. Pełny C-2 i skan 2D pozostają zablokowane.

Kolejny etap wymaga zmiany klasy modelu albo jawnego testu ograniczenia całej
rodziny skalarnego `n(x)`. Ośrodek anizotropowy zależny od kierunku promienia
pozostaje hipotezą rezerwową, nie zatwierdzonym następnym modelem.

Maszynowy raport: `solver/results/v2-local-basin-diagnostic.json`.

