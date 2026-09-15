# Powracająca niejednoznaczność gałęzi `P/JPJ`

## Status

To jest rozpoznany, osobny problem badawczy. Nie jest obecnie główną linią
implementacji dipola, ale każda kolejna walidacja musi raportować jego
diagnostyki. Trzech incydentów nie traktujemy już jako niezależnych usterek.

## Zaobserwowane przypadki

| Przypadek | Objaw | Mechanizm wykrycia |
|---|---|---|
| skan promienia `R/Rbase=1,50` | dwa minima oddalone o `2005 km` na `S3`, odpowiednio 10 i 9 gałęzi odbitych | różne restarty |
| skan deklinacji `delta=-17,58°` | brak konsensusu dla 4 z 5 części tarczy | różne ziarna wyboru dyskretnego |
| grudzień 16:00, brzeg wschodni | skok o `0,218854 rad` na `S3`, pozorna średnica `26,26×` | niespójna sygnatura centrum i brzegu |

W każdym przypadku funkcja celu ma konkurencyjne rozwiązania związane z
granicą reprezentacji `P/JPJ`. Nie jest to szum całkowania ani osobliwość
rzutu stereograficznego.

## Obowiązkowe diagnostyki

Każdy przyszły test raportuje co najmniej:

- dokładną sygnaturę bitową `P/JPJ` dla każdego obserwatora,
- konsensus sygnatur między restartami,
- rozrzut punktów na `S3`, nie tylko różnicę funkcji celu,
- minimalny margines drogi w przód,
- zgodność sygnatury centrum i wszystkich brzegów jednej tarczy,
- odległości centrum–brzeg na `S3`.

Średnia po rozwiązaniach należących do różnych gałęzi jest niedozwolona.

## Pytanie badawcze

Należy później zmapować ryzyko niejednoznaczności jako funkcję geometrii:

1. położenia obserwatora na mapie,
2. kierunku lokalnego promienia,
3. kąta centralnego na `S3`,
4. różnicy residuum `P` i `JPJ` dla pojedynczej obserwacji,
5. luki widmowej wspólnego dopasowania.

Naturalną zmienną ostrzegawczą jest margines dyskretny:

```text
branch_margin_i = |residual_P_i^2 - residual_JPJ_i^2| / R^2
```

Mały margines oznacza bliskość granicy przełączenia. Próg odrzucenia musi
zostać zamrożony na osobnym zbiorze, a nie dobrany do jednego z trzech znanych
incydentów.

## Relacja do nowego pola

Po dodaniu lokalnej anizotropii dokładna struktura wielkich okręgów znika,
więc bitowa granica obecnego solvera nie może zostać bezpośrednio przeniesiona
do nowego modelu. Problem pozostaje jednak ostrzeżeniem ogólnym: numeryczny
solver wielu torów również musi wykrywać konkurencyjne minima i nieciągłe
przeskoki rozwiązania.
