# Kontrakt analityczny Maxwella z lustrem

## Decyzja

Pierwszy dodatni interwał obrazowania rybiego oka Maxwella z lustrem można
śledzić dokładnie, bez RK45 i bez krokowego wykrywania odbić. Nie istnieje
jednak ogólna zamknięta formuła, która z pojedynczej pozycji i kierunku
obserwacji zwracałaby jeden dowolny punkt źródła. Pojedyncza obserwacja
wyznacza krzywą promienia; jednoznaczny antypodalny punkt sprzężony pojawia
się dopiero po narzuceniu pełnego interwału obrazowania.

W konsekwencji Maxwell pozostaje główną hipotezą v2, ale jej rekonstrukcja
ma porównywać analityczne krzywe wielu obserwatorów, a nie punkty `-observer`.

## Geometria

Dla profilu

```text
n(r) = 2 n0 / (1 + (r/R)^2)
```

trójwymiarowa przestrzeń fizyczna jest stereograficznym obrazem pomocniczej
trójsfery `S^3` osadzonej w `R^4`. Dla `x in R^3`, `q in S^3`:

```text
q_xyz = 2 R^2 x / (|x|^2 + R^2)
q_w   = R (|x|^2 - R^2) / (|x|^2 + R^2)

x = R q_xyz / (R - q_w)
```

Promień o pozycji `q` i jednostkowej stycznej `t` jest wielkim okręgiem:

```text
q(alpha) = q cos(alpha) + R t sin(alpha).
```

Lustro `|x|=R` odpowiada równikowi `q_w=0`. Odbicie realizuje dokładne
złożenie półkul:

```text
(q_xyz, q_w) -> (q_xyz, -q_w)
```

wraz z tą samą zmianą znaku składowej `w` stycznej. Jest to odbicie
zwierciadlane na sferycznej granicy w przestrzeni fizycznej. W pierwszym
interwale `0 <= alpha <= pi` promień wychodzący z wnętrza ma dokładnie jedno
odbicie. Droga optyczna ma zamkniętą postać `n0 R alpha`.

Implementacja znajduje się w `solver/maxwell_mirror.py` i działa w pełnych
trzech wymiarach. Dwuwymiarowa sfera `S^2` z wcześniejszego testu pozostaje
tylko ilustracją przekroju.

## Co daje pojedyncza obserwacja

Pozycja obserwatora i kierunek wyznaczają dwuwymiarową płaszczyznę w `R^4`
rozpiętą przez `q` i `t`, a więc jeden wielki okrąg na `S^3`. Po złożeniu na
lustrze jest to dokładna krzywa dopuszczalnych pozycji źródła.

Dla `alpha=pi` zachodzi:

```text
q(pi) = -q(0)
x_image = 2 centre - x_source.
```

Wynik nie zależy od kierunku. Jest to własność idealnego obrazowania: jeśli
jeden punkt jest źródłem, drugi jest jego obrazem sprzężonym. Nie oznacza to,
że każdy obserwator patrzący w dowolnym kierunku może potraktować
`2*centre-observer` jako pozycję wspólnego źródła. Dla różnych obserwatorów
te punkty są różne i utracono by informację kierunkową.

## Kontrakt rekonstrukcji v2

Następny adapter ma zachować:

1. pozycję i pełny kierunek każdej obserwacji,
2. dodatni parametr drogi `alpha in [0, pi]`,
3. analityczne złożenie na równiku,
4. wspólny punkt dopasowany do wielu złożonych krzywych,
5. istniejące grupy oraz metryki centrum, C-2 i C-3.

Pierwszym solverem powinno być najbliższe wspólne zbliżenie krzywych
parametryzowanych analitycznie. Nie wymaga ono integratora ani obsługi wielu
odbić. Dopiero jeśli pierwszy interwał okaże się niewystarczający, wariant
zapasowy może dodać ustaloną liczbę odbić i tę samą metrykę najbliższego
zbliżenia krzywych.

## Zakres potwierdzenia

Testy jednostkowe potwierdzają:

- odwracalność projekcji `R^3 <-> S^3`,
- poprawność różniczki kierunku,
- wspólny punkt `2*centre-position` po `alpha=pi` dla różnych kierunków,
- zgodność z prawem odbicia na sferycznym lustrze,
- dodatni, ograniczony pierwszy interwał drogi,
- rozróżnienie krzywej obserwacyjnej od punktu sprzężonego.

Nie jest to jeszcze wynik C-2/C-3 dla mapy. Położenie i skala lustra nad
płaszczyzną pozostają parametrami adaptera hybrydowego.

## Źródło

Podstawą konstrukcji jest U. Leonhardt, „Perfect imaging without negative
refraction”, *New Journal of Physics* 11, 093040 (2009), w szczególności
stereograficzna reprezentacja sfery, wielkie okręgi, obraz antypodalny i
złożenie półsfery przez lustro na równiku:
https://arxiv.org/abs/0909.5305
