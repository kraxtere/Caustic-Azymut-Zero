# Kontrakt testu osiągalności skalarnego `n(x)`

## Zakres wniosku

Test dotyczy statycznych, gładkich, osiowosymetrycznych pól skalarnych
`n(rho,z)` z dodatnim indeksem, regularnością na osi i zerowaniem perturbacji
na lustrze. Wynik nie będzie dowodem dotyczącym dowolnego ośrodka optycznego.

Perturbację wykładnika rozwijamy w bazie:

```text
B_ab(rho,z) = u^a v^b (1-u-v^2)
u = rho^2/R^2
v = z/R
```

gdzie `a,b` są nieujemnymi liczbami całkowitymi. Postać jest regularna w
centrum i osi oraz zachowuje `n=n0` na lustrze. Dodatniość wynika z postaci
wykładniczej.

## Punkty bazowe i lokalność SVD

Macierz czułości jest liczona niezależnie przy:

```text
dipole_epsilon = 0,00; 0,20; 0,40
```

`0,00` ma dokładne referencyjne śledzenie promieni Maxwella, lecz także w tym
punkcie numeryczna rekonstrukcja źródła może mieć płaską dolinę. Każda kolumna
Jacobianu używa kontynuacji tego samego rozwiązania z punktu bazowego; nie
wybiera minimum od nowa.

## Podział danych

- dopasowanie i analiza przestrzeni osiągalnej: `delta=+-23,44 deg`,
- walidacja held-out: `delta=+-11,72 deg`.

Jest to ten sam podział co w pierwszym teście predykcyjnym `P1`.

## Rosnąca baza i kryterium

Pełny przebieg powtarza SVD dla co najmniej trzech zagnieżdżonych baz. Dla
każdej raportuje widmo osobliwe, rząd efektywny, uwarunkowanie i minimalne
regularyzowane residuum celu obejmującego C-3, skalę i kształt tarczy.

Kandydat na numeryczny no-go wymaga dodatniej podłogi residuum jednocześnie:

1. we wszystkich trzech punktach bazowych,
2. przy zagęszczaniu bazy,
3. na zbiorze fit i held-out,
4. po nieliniowym uruchomieniu najlepszego kroku przewidzianego przez SVD.

Sam brak rzędu w jednym lokalnym Jacobianie nie wystarcza.

## Bramka techniczna przed pełnym przebiegiem

Dla jednego modu `B_11` sprawdzamy centralne różnice końcowego punktu i
kierunku promienia przy krokach `h=0,02` oraz `h/2=0,01` we wszystkich trzech
punktach bazowych. Wymagania:

- skończone pochodne,
- względna różnica pochodnych punktu i kierunku `<= 1%`,
- `n=n0` na lustrze i zgodność gradientu pola z różnicą centralną pozostają
  pokryte testami jednostkowymi.

Ta bramka waliduje infrastrukturę różniczkowania, nie hipotezę no-go.

