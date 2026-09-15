# Maxwell v2 i zamknięta hybryda Luneburga

## Zakres

Rodzina `atmosphere + Gaussian ring` została odrzucona jako główna hipoteza.
Modele Maxwella i Luneburga zostały najpierw certyfikowane w ich natywnej,
sferycznie symetrycznej geometrii. Ten etap nie korzysta z integratora RK45 i
nie miesza profili soczewek z azymutalną płaszczyzną. Dopiero po przejściu
testów analitycznych można dodać osobny adapter do geometrii
`płaszczyzna + kopuła`.

Główna implementacja znajduje się w `solver/field_lens.py`. Udostępnia ona
`n_and_grad` oraz `n_and_grad_components` o tym samym kształcie wywołania co
historyczny `field.py`, a także analityczne trajektorie referencyjne.
`solver/lenses.py` pozostaje wyłącznie zgodnościowym re-eksportem. Testy są w
`solver/tests/test_lenses.py`.

Natywna analityka obu profili jest poprawna. Hybrydowa rodzina Luneburga nad
płaską mapą ma jednak status `v2-falsified-hybrid` po zamrożonych skanach
`z0` i `(R,z0)`. Głównym kierunkiem pozostaje Maxwell z jawnym lustrem.

## Bramka analityczna — zaliczona

Testy bez integratora potwierdzają:

- wartości obu profili i ich analityczne gradienty kartezjańskie,
- stereograficzne przejście płaszczyzna–sfera i jego odwrotność,
- spotkanie różnych wielkich kół Maxwella w antypodzie,
- obraz `-punkt` dla wariantu z lustrem,
- fokus równoległej wiązki Luneburga na przeciwległej powierzchni,
- zachowanie warunku Hamiltona `|p|²=n²` w pełnym 3D.

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

## Bariera między geometrią natywną i geometrią projektu

Przejście testów analitycznych potwierdza implementację klasycznych profili,
ale nie potwierdza jeszcze ich przydatności nad płaską mapą. Adapter hybrydowy
musi jawnie określić:

1. środek i promień wirtualnej sfery,
2. sposób przejścia promienia przez płaszczyznę i kopułę,
3. warunki brzegowe lub lustro,
4. zgodność kierunków po obu stronach interfejsu,
5. użycie bez zmian istniejących metryk obserwacyjnych C-2 i C-3.

Nie wolno traktować stereograficznej sfery Maxwella jako automatycznego dowodu
dla azymutalnej geometrii projektu — to dopiero kontrolowany model odniesienia.

### Niezgodność warunków brzegowych Maxwella

Dokładny profil Maxwella nie ma zewnętrznego obszaru `n=const`: dla
`r→∞` współczynnik dąży do zera, a promienie realizują pełne wielkie koła na
wirtualnej sferze. Wariant Leonhardta ogranicza urządzenie do równika przez
lustro. Obecny ray tracer kończy promień w obszarze zaniku gradientu i nie ma
zdarzenia odbicia, więc nie da się jednocześnie zachować dokładnego modelu
Maxwella, lustra i zakazu zmian obsługi granicy.

Nie wprowadzamy nieudokumentowanego obcięcia `n=const` za `R0`, ponieważ
usunęłoby ono certyfikowaną własność ogniskowania. Adaptacja Maxwella musi
dopuścić osobny, testowalny warunek odbicia na kopule.

Równanie eikonalne wewnątrz ośrodka pozostaje bez zmian. Nie można jednak użyć
bez zmian triangulacji asymptotycznych półprostych: w układzie z lustrem
promień nie opuszcza pola. Następny adapter musi jawnie zdefiniować odbicie,
parametr drogi liczony w przód i rekonstrukcję wspólnego punktu na krzywych.

## Adapter hybrydowy Luneburga — zamknięty punkt odniesienia

`solver/validate_lens.py` umieszcza górną półsferę Luneburga nad mapą `z=0`.
Domyślny środek leży w środku mapy, a promień jest równy odległości mapowej
biegun północny–południowy (`pi * R_MAP`). Poza sferą obowiązuje `n=1`, a
powrót promienia pod płaszczyznę jest traktowany jako wynik niepoprawny.

To kontrolny kandydat geometryczny, nie dopasowany wynik. Przechodzi przez te
same funkcje walidatora C-2/C-3, te same półproste i tę samą triangulację co
zamknięcie v1. Integrator nie został zmieniony.

Historyczne odtworzenie domyślnego przebiegu można wykonać lokalnie:

```bash
./.venv/Scripts/python.exe -m solver.validate_lens \
  --family luneburg \
  --radius-km 20015.086796 \
  --centre-z-km 0 \
  --workers 6 \
  --output solver/results/v2-luneburg-default-validation.json
```

Polecenie z `--family maxwell` celowo kończy się błędem o brakującym warunku
lustra. Zapobiega to przedstawieniu arbitralnie uciętego profilu jako dokładnej
soczewki Maxwella.

### Wynik domyślnego ustawienia i korekta granicy

Pierwszy przebieg dla `R=20015,086796 km`, `z0=0` zdecydowanie przegrał z
`n=1`. Ujawnił też błąd adaptera: promień był uznawany za asymptotyczny dopiero
na wysokości szczytu kuli, a nie przy wyjściu przez jej sferyczną powierzchnię.
Równanie eikonalne było poprawne, ale błędny punkt początku półprostej mógł
tworzyć sztuczne wyniki `max_path` i niepoprawne odległości w przód.

Kryterium wyjścia zostało poprawione bez zmiany RK45, równania promienia,
triangulacji ani metryk C-2/C-3. Pierwszy JSON jest zatem diagnostyczny, a
skorygowany przypadek `z0=0` jest liczony jako ostatni punkt pierwszego skanu.

### Bramka przed pełnym C-2

`solver/scan_luneburg.py` najpierw zmienia wyłącznie pionowe położenie środka
przy stałym `R`. Dopiero po analizie tego wyniku pozwala zbudować lokalną siatkę
`(R,z0)`. Tani zbiór zawiera wszystkie 15 środków Słońca oraz oba bieguny C-3,
ale nie zawiera czterech brzegów tarczy.

Promocja do pełnego C-2 wymaga jednocześnie:

1. kompletnego, niższego niż `n=1` średniego RMS środków Słońca,
2. niższego niż `n=1` RMS bieguna północnego,
3. niższego niż `n=1` RMS bieguna południowego,
4. `minimum_forward_distance_km >= 0` dla każdego ocenionego celu.

Brak triangulacji albo choć jeden niepoprawny promień automatycznie blokuje
promocję. Raport jest atomowo aktualizowany po każdym kandydacie.

Oba etapy zostały wykonane. Żaden z siedmiu punktów pierwszego skanu ani
dziewięciu punktów lokalnej siatki nie przeszedł bramki. Pełne C-2 nie zostało
uruchomione. Decyzję, liczby i ścieżki do wyników zawiera
`V2_LUNEBURG_CLOSURE.md`.
