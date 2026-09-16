# Zamrożona diagnostyka basenów dla tarczy `delta=-11,72 deg`

## Cel

Sprawdzamy, czy zły `axis_ratio` jest stabilną własnością krzywych, czy
artefaktem wyboru konkurencyjnych minimów. Nie zmieniamy pola. Używamy
`dipole_epsilon=0,20`, `R=1,20 Rbase`, `z0=0,40 Rbase` oraz tej samej wspólnej
kohorty i pięciu elementów tarczy co w bramce skali.

## Mapa basenów

Dla każdego elementu tarczy budujemy pełne krzywe numeryczne raz. Uruchamiamy
osiem dotychczasowych startów ICP i grupujemy wyniki według odległości źródeł
z progiem `1e-6 R`. Jeżeli istnieją co najmniej dwa klastry, wybieramy start
ciepły i pierwszy start kończący w innym klastrze, a następnie próbkujemy 65
punktów na odcinku pomiędzy ich wektorami początkowych parametrów `alpha`.

Raportujemy liczbę klastrów, przejścia etykiet wzdłuż przekroju, odległości
między źródłami i różnice RMS. Nie uśredniamy źródeł należących do różnych
basenów.

## Wpływ na kształt tarczy

Z reprezentantów wykrytych klastrów tworzymy wszystkie kombinacje pięciu
elementów tarczy (maksymalnie 1024; przekroczenie limitu przerywa tę część).
Dla każdej kombinacji liczymy średnicę i `axis_ratio`.

- Jeżeli wybór basenu przenosi `axis_ratio` przez próg `1,10`, dotychczasowy
  konflikt kształtu jest co najmniej częściowo artefaktem rekonstrukcji.
- Jeżeli cały zakres pozostaje powyżej `1,10`, konflikt kształtu jest odporny
  na wykryte wybory basenu w tym przekroju.

To diagnostyka jednego przypadku, nie walidacja pola ani C-2.
