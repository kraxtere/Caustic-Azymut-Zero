# Zamrożona diagnostyka gałęzi i korekty skali Maxwella

## Pytania

1. Czy rzeczywisty grudniowy tor C-2 leży po tej samej stronie granicy
   gałęzi co stabilny punkt `delta=-23,44°`?
2. Czy wymagana korekta skali na stabilnym zakresie ma prostą postać
   analityczną, która może wskazać następny stopień swobody pola?

Analiza używa wyłącznie zapisanych JSON-ów. Nie śledzi nowych promieni i nie
zmienia kandydata Maxwella.

## Klasyfikacja strony gałęzi

Pełnych bitowych sygnatur nie porównujemy jeden do jednego, ponieważ
grudniowy C-2 i syntetyczny skan deklinacji mają różne kohorty obserwatorów.
Porównujemy topologię:

- stabilna strona odbita: wszystkie cele i ziarna są zgodne, a liczba `JPJ`
  jest dodatnia,
- stabilna strona bezpośrednia: wszystkie cele i ziarna są zgodne, a liczba
  `JPJ` wynosi zero,
- granica: ziarna wybierają różne przypisania.

Grudzień zostaje uznany za tę samą stronę co `-23,44°`, jeśli wszystkie jego
chwile i części tarczy są zgodne między ziarnami i mają dodatnią liczbę `JPJ`,
podczas gdy referencja `-11,72°` ma zero `JPJ`.

## Rezydualna korekta skali

Stabilny zakres jest zamrożony jako siedem ważnych punktów
`-11,72° ... +23,44°`. Dla skali transferu `S(delta)` definiujemy wymaganą
korektę multiplikatywną:

```text
C(delta) = S(0) / S(delta)
```

Z definicji `C(0)=1`. Przed obliczeniem współczynników deklarujemy cztery
postacie:

1. `C = 1 + a*delta`,
2. `C = 1 + a*sin(delta)`,
3. `C = 1 + a*delta + b*delta^2`,
4. `C = exp(a*delta)`.

Kąty we wzorach są w radianach. Model jest wystarczająco prosty tylko wtedy,
gdy jednocześnie `RMSE <= 0,01` i największy błąd bezwzględny `<=0,02`.
Spośród modeli spełniających oba warunki wybiera się najpierw najmniejszą
liczbę parametrów, a potem najniższy RMSE. Brak modelu spełniającego progi
oznacza, że te cztery proste postacie nie wskazują wystarczającej korekty.
