# Wynik diagnostyki gałęzi i korekty skali Maxwella

## Strona granicy gałęzi

Rzeczywisty grudniowy tor C-2 leży po tej samej, odbitej stronie co punkt
`delta=-23,44°` ze skanu syntetycznego:

- `delta=-23,44°`: wszystkie części tarczy stabilnie wybierają `6/20` gałęzi
  `JPJ`,
- `delta=-17,58°`: ziarna konkurują między rozwiązaniami bezpośrednimi i
  rozwiązaniami z dwiema gałęziami `JPJ`,
- `delta=-11,72°`: wszystkie części stabilnie wybierają `0/20` gałęzi `JPJ`,
- grudzień C-2: zależnie od godziny wszystkie części tarczy stabilnie wybierają
  od `5/20` do `8/20` gałęzi `JPJ`,
- czerwiec C-2: wszystkie chwile i części tarczy wybierają `0/20` gałęzi
  `JPJ`.

Porównanie jest topologiczne, nie bitowe: kohorty obserwatorów w obu testach
nie są identyczne. Wynik wystarcza do stwierdzenia, że sezonowa para
grudzień–czerwiec przecina granicę gałęzi.

Nie wystarcza natomiast do liczbowego podziału `46,7745%` na część gładką i
skok dyskretny. Taki podział wymagałby nowego, wcześniej zamrożonego testu z
wymuszoną kontynuacją obu gałęzi przez ten sam zakres deklinacji i tę samą
kohortę. Obecny wynik uczciwie rozstrzyga jedynie, że rozbieżność nie jest
wyłącznie gładkim efektem `z0`.

Zamrożony następny test:
[`V2_MAXWELL_FORCED_BRANCH_CONTINUATION.md`](V2_MAXWELL_FORCED_BRANCH_CONTINUATION.md).

## Rezydualna korekta na stabilnej gałęzi

Dla siedmiu stabilnych punktów `-11,72° ... +23,44°` zdefiniowano:

```text
C(delta) = S(0) / S(delta)
```

Otrzymane wartości korekty rosną od `0,87334` do `1,20830`.

| Model | Współczynniki | RMSE | Maks. błąd | Przechodzi |
|---|---|---:|---:|---|
| `1+a*delta` | `a=0,534532` | `0,008123` | `0,017320` | tak |
| `1+a*sin(delta)` | `a=0,544753` | `0,007216` | `0,016005` | **tak — wybrany** |
| `1+a*delta+b*delta²` | `a=0,581635`, `b=-0,177136` | `0,000251` | `0,000449` | tak |
| `exp(a*delta)` | `a=0,505040` | `0,014297` | `0,028510` | nie |

Kąty są w radianach. Zgodnie z zamrożoną regułą najpierw wybierana jest
najmniejsza liczba parametrów, następnie najmniejszy RMSE. Najprostsza
zaakceptowana postać to zatem:

```text
C(delta) = 1 + 0,544753 * sin(delta)
```

Ta postać ma uzasadnienie wynikające z symetrii, a nie tylko z jakości
dopasowania. Dla profilu radialnego przesuniętego osiowo o `z0`:

```text
f(|r - z0 e_z|) = f(r) - z0 f'(r) cos(theta) + O(z0^2)
```

Wiodąca perturbacja kątowa jest więc dipolem `l=1`, czyli
`P1(cos(theta))=cos(theta)`. W użytej konwencji osiowej `cos(theta)=sin(delta)`,
stąd naturalnie pojawia się właśnie `sin(delta)`. Jest to wskazanie klasy
symetrii nowego parametru, a nie dowód, że sama empiryczna korekta skali jest
gotową postacią `n(r)`.

Kwadrupol `l=2` ma postać:

```text
P2(sin(delta)) = (3 sin(delta)^2 - 1) / 2
```

W rozwinięciu samego przesuniętego profilu radialnego drugi rząd po `z0/r`
rzeczywiście zawiera mieszaninę `P0+P2`. Nie wolno jednak utożsamiać wartości
lokalnego pola z `C(delta_source)`, które jest nieliniową odpowiedzią
scałkowaną wzdłuż całego zagiętego toru.

Jest on parzysty w `delta`, więc ma identyczną wartość przy obu przesileniach
i nie może zmniejszyć sezonowej asymetrii czerwiec–grudzień. Może opisywać
jedynie wspólny poziom lub krzywiznę kontrolowaną m.in. przez równonoc. Jeśli
dipol nie wystarczy do asymetrii, naturalnym następnym składnikiem jest
nieparzysty oktupol `l=3`, `P3(x)=(5x^3-3x)/2`, rozdzielany od `P1` przez
deklinacje pośrednie.

Co ważniejsze, `delta` w tabeli jest deklinacją źródła i tylko etykietuje
odpowiedź układu. Nie może stać się argumentem `n`. Statyczne pole może użyć
lokalnej współrzędnej `mu(x)=cos(theta(x))`; dopiero odpowiedź takiego pola
jest badana jako funkcja `delta_source`.

Dwupunktowa krzywizna w modelu kwadratowym poprawia RMSE około 29 razy, ale
nie jest konieczna do spełnienia progów `1%/2%`.

## Wskazówka dla następnej rodziny

Pierwszym kandydatem nie powinno być kolejne globalne `R`. Dane wskazują na
jeden nieparzysty osiowy stopień swobody:

- proporcjonalny w pierwszym przybliżeniu do osiowej współrzędnej
  `sin(delta)`,
- równy zero na równiku,
- o przeciwnym znaku na północ i południe,
- działający na lokalną skalę odwzorowania, nie na wybór gałęzi.

To jest docelowy kształt odpowiedzi nowego parametru, a nie jeszcze gotowa
postać współczynnika załamania. Osobny mechanizm lub warunek nadal musi
kontrolować granice `P/JPJ` i drogi w przód.

Maszynowy raport: `solver/results/v2-maxwell-scale-correction.json`.
