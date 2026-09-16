# Skan granicy gałęzi skalarnego kandydata

## Cel

Czteropunktowa diagnostyka trajektorii wykazała zmianę prędkości, kierunku i
orientacji tarczy na odcinku `-23,44 ... -11,72 deg`, który obejmuje znaną
granicę około `-17,58 deg`. Ten skan rozstrzyga, czy jest to tylko silna,
ciągła nieliniowość, czy współistnienie konkurencyjnych basenów.

## Projekt

- 13 równomiernych deklinacji, w tym dokładnie `-17,58 deg`,
- tylko środek Słońca — bez czterech brzegów tarczy,
- zamrożony kandydat `epsilon=0,40 / degree_3`,
- ten sam moment referencyjny i ta sama kohorta obserwatorów,
- osiem startów na punkt: oba końce przedziału, ich interpolacja, dwa starty
  zaburzone i trzy losowe,
- równoległe liczenie punktów i checkpoint po każdym zakończonym punkcie.

Dokładne etykiety `P/JPJ` nie istnieją po zaburzeniu pola, ponieważ znika
analityczna konstrukcja wielkich okręgów. Raportowanym odpowiednikiem są:

- liczba odbić każdego promienia przed wybraną wartością `alpha`,
- skrót całego wektora odbić,
- różnica wektorów `alpha` dla startów z obu stron,
- odległość źródeł otrzymanych z obu stron,
- liczba klastrów konkurencyjnych rozwiązań i ścisły konsensus restartów.

„Ten sam basen” wymaga jednocześnie trzech zgodności:

1. maksymalny rozrzut konkurencyjnych źródeł nie przekracza `1e-6 R`,
2. pełne wektory liczby odbić obserwatorów są identyczne,
3. maksymalna różnica dowolnej składowej `alpha` między konkurencyjnymi
   restartami nie przekracza `1e-5 rad`.

Nie wystarcza samo trafienie do tego samego klastra źródła. Dwie drogi
kończące się w tym samym miejscu, ale mające różne `alpha`, są raportowane
jako brak konsensusu. Oprócz progu maksymalnej składowej zapisywany jest też
RMS różnicy całych wektorów `alpha`.

## Uruchomienie

PowerShell:

```powershell
.\solver\run_scalar_branch_boundary.ps1
```

Git Bash:

```bash
bash solver/run_scalar_branch_boundary.sh
```

Wynik:

`solver/results/v2-scalar-branch-boundary.json`

Stan wznowienia jest zapisywany w:

`solver/results/v2-scalar-nx-svd-checkpoints/branch-boundary/`

Przebieg można bezpiecznie przerwać. Ponowne uruchomienie wykorzysta gotowe
punkty. To nadal obliczenia numeryczne promieni, ale zakres jest znacznie
mniejszy niż pełne SVD: 13 grup środka zamiast trzech baz, 10 kolumn różnic
skończonych i dziewięciu pełnych kandydatów.
