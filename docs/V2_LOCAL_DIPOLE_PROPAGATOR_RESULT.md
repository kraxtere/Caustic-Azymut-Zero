# Wynik bramki propagatora lokalnego dipola v2.1

## Werdykt

Zamrożona bramka `epsilon=0` kończy się **PASS**. Nie uruchomiono jeszcze
skanu amplitudy ani C-3.

## Pole

Zaimplementowano zatwierdzoną postać:

```text
n(x) = n_Maxwell(r) * exp[epsilon * (z/R) * (1-r^2/R^2)]
```

Gradient jest analityczny. Test różnicą centralną, regularność w centrum,
zerowanie wykładnika na lustrze i dodatniość indeksu przechodzą bez wyjątków.

## Granica analityczna

Numeryczny propagator eikonalny z odbiciem od `r=R` porównano z dokładnymi
wielkimi okręgami `S3` dla 12 kombinacji położenia, kierunku i kąta
centralnego. Zestaw obejmuje tory bez odbicia i z odbiciem.

Wszystkie przypadki spełniają zamrożone progi:

- błąd punktu `<=1e-7 R`,
- błąd kierunku `<=1e-5°`,
- identyczna parzystość odbicia.

Największy zmierzony błąd punktu wyniósł `8,87e-11 km` przy limicie
`1,00e-6 km`; błąd kierunku był numerycznie równy `0°` przy limicie
`1e-5°`.

Zaostrzenie tolerancji oraz dwukrotne zmniejszenie maksymalnego kroku nie
zmieniły punktu o więcej niż `1,01e-14 km` przy limicie `1,00e-6 km`.

Pozostałe maksymalne błędy:

- wartość `n` na lustrze: `0`,
- gradient w centrum: `2,78e-17`,
- gradient analityczny względem różnicy centralnej: `1,60e-10` względnie,
  przy limicie `1e-6`.

## Znaczenie

Nowy propagator odtwarza dokładny solver Maxwella w granicy zerowej
perturbacji. Jest to wymagana bramka techniczna, nie dowód poprawności
fizycznej dipola i nie dopasowanie obserwacyjne.

Następny dozwolony krok to osobny, wcześniej zamrożony tani skan `epsilon` na
C-3. Analityczny punkt `4x4` może być inicjalizacją dla małych perturbacji,
ale numeryczne konkurencyjne minima muszą pozostać oddzielne.

Maszynowy raport:
`solver/results/v2-local-dipole-propagator-validation.json`.
