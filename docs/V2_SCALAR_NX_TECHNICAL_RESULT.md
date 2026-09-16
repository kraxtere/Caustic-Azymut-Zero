# Wynik technicznej bramki bazy skalarnego `n(x)`

## Werdykt

Techniczna bramka różnic skończonych kończy się **PASS** we wszystkich trzech
punktach bazowych. Nie wykonano jeszcze obserwacyjnego SVD ani dopasowania.

| `dipole_epsilon` | różnica pochodnej punktu | różnica pochodnej kierunku | wynik |
|---:|---:|---:|---|
| `0,00` | `1,915e-7` | `3,141e-7` | PASS |
| `0,20` | `1,698e-7` | `2,705e-7` | PASS |
| `0,40` | `1,507e-7` | `2,324e-7` | PASS |

Limit dla obu wielkości wynosił `1e-2`. Porównano centralne różnice dla
`h=0,02` i `h/2=0,01` na regularnym modzie `B_11`.

## Co zostało potwierdzone

- ogólna baza `B_ab=u^a v^b(1-u-v^2)` jest zaimplementowana w postaci
  wykładniczej i zachowuje dodatniość `n`,
- jej gradient analityczny zgadza się z różnicą centralną,
- perturbacja zeruje się na lustrze i jest regularna na osi,
- numeryczny propagator daje stabilną pochodną końcowego punktu i kierunku
  promienia w trzech zamrożonych punktach bazowych.

## Ograniczenie

To wymagana walidacja infrastruktury. Nie pokazuje, czy obserwacyjny wektor
korekty leży w przestrzeni osiągalnej, nie ocenia zbioru held-out i nie stanowi
argumentu no-go.

Maszynowy raport: `solver/results/v2-scalar-basis-jacobian-validation.json`.

