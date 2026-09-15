# Analityczne modele soczewek — etap v1.5

## Zakres

Modele Maxwella i Luneburga są najpierw certyfikowane w ich natywnej,
sferycznie symetrycznej geometrii. Ten etap nie korzysta z integratora RK45 i
nie miesza profili soczewek z azymutalną płaszczyzną. Dopiero po przejściu
testów analitycznych można dodać osobny adapter do geometrii
`płaszczyzna + kopuła`.

Implementacja referencyjna znajduje się w `solver/lenses.py`, a testy w
`solver/tests/test_lenses.py`.

## Rybie oko Maxwella

Używamy profilu

```text
n(r) = 2 n0 / (1 + (r/R0)^2).
```

Dla `r=0` indeks wynosi `2n0`, dla `r=R0` wynosi `n0`, a w nieskończoności
dąży do zera. Profil realizuje stereograficzne odwzorowanie wirtualnej sfery.
Promienie odpowiadają jej wielkim kołom, dlatego wszystkie promienie ze
wspólnego punktu spotykają się ponownie w antypodzie. Lustro na równiku
zawija zewnętrzną półsferę do wnętrza urządzenia; obraz punktu wewnątrz koła
leży po przeciwnej stronie średnicy.

Test jednostkowy nie całkuje równania promienia. Oblicza wielkie koła wprost i
sprawdza wspólny antypod dla różnych kierunków początkowych.

Źródła:

- J. C. Maxwell, „Solutions of Problems”, *Cambridge and Dublin Mathematical
  Journal* 8, 188–189 (1854):
  https://www.damtp.cam.ac.uk/user/gold/pdfs/teaching/old_literature/Maxwell1853.pdf
- U. Leonhardt, „Perfect imaging without negative refraction”, *New Journal
  of Physics* 11, 093040 (2009): https://arxiv.org/abs/0909.5305

## Soczewka Luneburga

Wewnątrz soczewki o promieniu `R` używamy profilu

```text
n(r) = sqrt(2 - (r/R)^2),
```

a na zewnątrz `n=1`. Na powierzchni nie ma skoku indeksu. Równoległa wiązka
ogniskuje się w jednym punkcie przeciwległej powierzchni.

Dla Hamiltonianu `(|p|^2-n^2)/2=0` wewnętrzny promień spełnia dokładnie

```text
d²r/dtau² = -r/R².
```

Jest to oscylator harmoniczny. Dla punktu wejścia `r0` i jednostkowego
kierunku padającej wiązki `d`:

```text
r(tau) = r0 cos(tau/R) + R d sin(tau/R).
```

Przy `tau=pi R/2` każdy promień wiązki znajduje się w punkcie `R d`, bez
względu na parametr uderzenia. Test sprawdza ten fokus oraz zachowanie
hamiltonowskiego warunku `|p|²=n²`.

Źródła:

- R. K. Luneburg, *Mathematical Theory of Optics*, Brown University (1944):
  https://books.google.com/books/about/Mathematical_Theory_of_Optics.html?id=bQsJAQAAMAAJ
- M. Carney, M. A. Kenworthy, „Modeling of a stepped Luneburg lens for
  all-sky surveys” (profil ciągły w równaniu 3):
  https://arxiv.org/abs/1806.05661

## Bariera między v1.5 i geometrią projektu

Przejście testów analitycznych potwierdza implementację klasycznych profili,
ale nie potwierdza jeszcze ich przydatności nad płaską mapą. Adapter hybrydowy
musi jawnie określić:

1. środek i promień wirtualnej sfery,
2. sposób przejścia promienia przez płaszczyznę i kopułę,
3. warunki brzegowe lub lustro,
4. zgodność kierunków po obu stronach interfejsu,
5. osobną funkcję kosztu dla obserwacji, C-2 i C-3.

Nie wolno traktować stereograficznej sfery Maxwella jako automatycznego dowodu
dla azymutalnej geometrii projektu — to dopiero kontrolowany model odniesienia.
