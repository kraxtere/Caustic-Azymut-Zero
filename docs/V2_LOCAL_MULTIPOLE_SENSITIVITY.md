# Zamrożony ekran czułości drugiego lokalnego składnika

## Cel

Nie zakładamy z góry, że drugim parametrem ma być kwadrupol. Porównujemy trzy
regularne lokalne składniki wykładnika pola Maxwella, każdy z obwiednią
`1-r^2/R^2`, zerującą perturbację na lustrze:

```text
M0 = q^2 (1-q^2)
M2 = q^2 P2(mu) (1-q^2)
M3 = q^3 P3(mu) (1-q^2)
```

W postaci kartezjańskiej wszystkie są wielomianowe i regularne w centrum.
Badamy je wokół punktu `dipole_epsilon=0,20`, który przeszedł C-3.

## Projekt

Dla każdego składnika liczymy centralną różnicę przy amplitudach `-0,05` i
`+0,05`. Zestaw diagnostyczny obejmuje oba bieguny C-3 oraz tarcze dla
`delta=-23,44, 0, +23,44 deg`, po pięć elementów każda. Używane są te same
restarty, konsensus i propagator co w poprzednich bramkach.

Wektor odpowiedzi tworzą pochodne logarytmiczne:

- RMS bieguna północnego,
- RMS bieguna południowego,
- bezwzględna asymetria przesileniowa średnicy,
- CV trzech średnic,
- średni `axis_ratio` trzech tarcz.

Osobno wyznaczamy taki sam wektor dla samego dipola przez `epsilon=0,15` i
`0,25`. Bezwzględny cosinus między wektorami jest diagnostyką podobieństwa,
nie dowodem fizycznej ortogonalności.

## Zasada wyboru

Znak każdego nowego składnika wolno odwrócić. Kandydat jest użyteczny do
dalszego skanu tylko wtedy, gdy po orientacji znaku jednocześnie zmniejsza
asymetrię, CV i średni `axis_ratio`. Spośród użytecznych kandydatów wybieramy
najmniejszy bezwzględny cosinus z odpowiedzią dipola. Ten przebieg nie
autoryzuje jeszcze pełnego C-2 ani skanu wielu parametrów.

