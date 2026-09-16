# Wynik ekranu czułości lokalnych modów

## Werdykt

**Żaden kandydat nie zostaje promowany do skanu 2D.** Radialny monopol,
kwadrupol i oktupol zostały sprawdzone jako regularne lokalne perturbacje
obwiedni Maxwella wokół `dipole_epsilon=0,20`. Każdy może poprawić część
metryk skali po odpowiednim wyborze znaku, lecz żaden nie zmniejsza
jednocześnie asymetrii przesileniowej, CV średnicy i średniego `axis_ratio`.

## Odpowiedź referencyjnego dipola

Logarytmiczna pochodna względem amplitudy dipola wynosi:

| metryka | pochodna |
|---|---:|
| RMS bieguna N | `-0,238855` |
| RMS bieguna S | `-1,078072` |
| asymetria przesileniowa | `+1,179706` |
| CV średnicy | `+0,660621` |
| średni `axis_ratio` | `-0,160718` |

Potwierdza to poprzednią bramkę: dodatni dipol poprawia oba bieguny, ale
zwiększa asymetrię i CV. Jednocześnie nieznacznie poprawia średni stosunek osi,
co pokazuje, że problem skali i eliptyczności nie jest jedną metryką.

## Kandydaci po orientacji znaku na poprawę asymetrii

| składnik | `|cos|` z dipolem | asymetria | CV | `axis_ratio` | użyteczny |
|---|---:|---:|---:|---:|---|
| monopol `M0` | `0,245216` | `-0,330093` | `-0,315584` | `+0,374730` | nie |
| kwadrupol `M2` | `0,630062` | `-0,075899` | `-0,082144` | `+0,152523` | nie |
| oktupol `M3` | `0,782073` | `-0,837125` | `-0,501868` | `+0,077033` | nie |

Wszystkie trzy zmniejszają asymetrię i CV w wybranej orientacji, ale
jednocześnie zwiększają eliptyczność. Najbardziej niezależny od dipola monopol
nie jest przez to najlepszym parametrem fizycznym — niezależność kierunku
odpowiedzi nie wystarcza.

Oktupol `M3` ma najbardziej atrakcyjne liczby surowe: największą korektę
asymetrii i CV przy najmniejszym koszcie `axis_ratio`. Jest równocześnie
najmniej wiarygodnym kandydatem, ponieważ jako jedyny nie zachowuje konsensusu
po żadnej stronie różnicy centralnej. Najładniejsza pochodna pochodzi więc z
najmniej ustabilizowanej diagnostyki i nie jest argumentem za promocją `M3`.

## Stabilność

Różnice centralne nie są w pełni stabilne topologicznie:

- monopol: konsensus dla `-0,05`, brak dla `+0,05`,
- kwadrupol: brak konsensusu dla `-0,05`, konsensus dla `+0,05`,
- oktupol: brak konsensusu po obu stronach.

Dlatego wartości pochodnych są diagnostyką lokalnego kierunku, a nie podstawą
do precyzyjnej optymalizacji. Nie wolno na ich podstawie uruchamiać gęstej
siatki ani wybierać oktupola tylko dlatego, że ma największą korektę skali.

## Decyzja

Nie uruchamiamy skanu `(dipole, drugi_mod)` i nie odblokowujemy C-2. Obecny
problem nie jest brakiem jednego oczywistego multipola. Następny krok powinien
najpierw rozdzielić rekonstrukcję kształtu tarczy od wyboru konkurencyjnego
minimum — najlepiej przez diagnostykę całych krzywych i granic basenów dla
jednej tarczy, zamiast dodawania kolejnych amplitud pola.

Jeżeli po usunięciu wpływu granic basenów konflikt skala–kształt pozostanie,
może to wskazywać na ograniczenie całej klasy skalarnego, lokalnego `n(x)`.
Ośrodek zależny od kierunku promienia jest jednak osobną, znacznie bardziej
złożoną hipotezą i nie jest autoryzowany przez ten wynik.

Maszynowy raport: `solver/results/v2-local-mode-sensitivity.json`.
