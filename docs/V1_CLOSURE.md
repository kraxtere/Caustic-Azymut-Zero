# Zamknięcie modelu v1

## Decyzja po pełnych przebiegach

Trzy pełne przebiegi ewolucji różnicowej (`maxiter=120`, `popsize=12`,
`polish`, ziarna 20260915–20260917) doszły do tego samego rozwiązania w
granicach dokładności raportu:

- średni RMS: `2314,034235 km`,
- poprawa względem `n=1`: `6,691390%`,
- `k=0`,
- `A=-0,1` i `s=100 km`, czyli obie wartości na granicach,
- `rho0=11271,315 km`.

To zamyka **dopasowanie treningowe v1** jako stabilne minimum brzegowe tej
rodziny. Nie jest to dobry model globalny: wąski pierścień wybiórczo wpływał
na promienie jednej szerokości geograficznej. Wynik nie rozstrzyga szerszej
hipotezy pola toroidalnego.

Pełne maszynowe wyniki są zachowane w `solver/results/` jako pliki
`full-fit-v1-seed-*.json`.

## Niezależność ziaren

Test `solver/tests/test_optimizer_seed.py` uruchamia dokładnie wrapper projektu
nad `scipy.optimize.differential_evolution`, z `maxiter=0`, dzięki czemu bada
populację po inicjalizacji, przed pierwszą generacją. Sprawdza dwa warunki:

1. powtórzenie tego samego ziarna daje identyczną populację,
2. ziarna 20260915, 20260916 i 20260917 dają trzy różne populacje.

W środowisku kontrolnym skróty SHA-256 populacji wyniosły odpowiednio:

```text
20260915  4430798768b573cfd5d2397065eb3efd62be565dc90cfcadad6a613ddf8a9c1d
20260916  10a1f90efffedcd3446cfbe0ceec554e930a6971ea04f4eb12251e9ab656b3fa
20260917  d9682d493c2a19b12b793062e0875933aa37c5ee8f0cc0c0203f06a9cc9b03af
```

Zbieżne wyniki trzech pełnych przebiegów są więc niezależnymi startami, a nie
trzykrotnym odtworzeniem tej samej populacji.

## Polityka refrakcji

Kierunki generowane przez obecną efemerydę są geometrycznymi kierunkami
alt-az. Nie zawierają korekty refrakcji pozornej. Dlatego walidacja v1 domyślnie
używa polityki `vacuum-geometric` i wymusza `k=0`. Atmosferycznego tła nie
wolno oceniać na tym zbiorze; wymaga ono osobnego zbioru pozornych,
refraktowanych obserwacji. Tryb `as-fitted` pozostaje jedynie testem czułości.

## Walidacja poza próbką

`solver.validate_v1` nie optymalizuje parametrów. Wczytuje zamrożony JSON
jednego pełnego dopasowania i sprawdza:

- gęstą siatkę 64 kandydatów (8 szerokości × 8 długości),
- C-2: środek i cztery brzegi tarczy Słońca w sześciu chwilach,
- C-3: osobne rekonstrukcje półprostych dla obu biegunów niebieskich,
- rozkład ugięcia pomiędzy tło i pierścień.

Raport C-2 podaje RMS każdego punktu tarczy, dwie zrekonstruowane średnice,
anizotropię, przesunięcie środka oraz zmienność średnicy pomiędzy chwilami.
Raport C-3 podaje RMS, liczbę promieni, minimalną odległość w przód i
uwarunkowanie triangulacji. Nie ma arbitralnego `pass/fail`: progi naukowe nie
zostały jeszcze ustalone, więc JSON zachowuje surowe metryki.

Uruchomienie w Git Bash z katalogu repozytorium:

```bash
./.venv/Scripts/python.exe -m solver.validate_v1 \
  --fit-json solver/results/full-fit-v1-seed-20260917.json \
  --workers 6 \
  --output solver/results/v1-closure-validation.json
```

To jest cięższy przebieg (około tysiąca całkowanych promieni) i zgodnie z
ustaleniem należy wykonać go na komputerze prowadzącego.

## Następny etap

v1.5 certyfikuje klasyczne profile Maxwella i Luneburga w ich natywnej
geometrii analitycznej, bez integratora. Szczegóły są w `LENS_MODELS.md`.
Równolegle v2 może zastąpić pojedynczy wąski Gaussian gładką rodziną
toroidalną i dopiero wtedy zostać ponownie oceniony na C-2 oraz C-3.
