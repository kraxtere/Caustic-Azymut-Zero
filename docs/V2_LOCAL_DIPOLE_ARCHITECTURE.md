# Granica architektoniczna lokalnego dipola Maxwella

## Co zostało ustalone

Dokładny solver Maxwella działa dlatego, że radialny profil rybiego oka jest
stereograficznym obrazem jednorodnej `S3`. Promienie są wielkimi okręgami, a
triangulacja sprowadza się do dekompozycji `4x4`.

Lokalny składnik zależny od

```text
mu(x) = axial_coordinate(x) / radius(x)
```

zmienia współczynnik konforemny w sposób osiowy. Metryka nie ma już stałej
krzywizny, promienie nie są wielkimi okręgami, a relacja `P/JPJ` używana przez
analityczną triangulację przestaje być ścisła. Nie wolno podłączyć nowego pola
do starego solvera bez zmiany propagatora.

## Co pozostaje nieokreślone

Identyfikacja `P1` określiła minimalną klasę empirycznej odpowiedzi, ale nie
wyznaczyła radialnej obwiedni lokalnego pola. Ta obwiednia jest fizyczną
hipotezą i wpływa na wszystkie tory.

Minimalny kandydat powinien jednocześnie:

- być regularny w centrum (`P1(mu)` sam jest tam nieokreślony),
- nie zmieniać warunku na powierzchni lustra,
- zachować dodatniość `n`,
- mieć jeden współczynnik amplitudy,
- nie kodować daty, źródła ani `delta_source`.

Jedną możliwą, ale jeszcze **niezatwierdzoną** parametryzacją jest:

```text
q = r/R
n(x) = n_Maxwell(r) * exp[epsilon * q * (1-q^2) * P1(mu)]
```

Ponieważ `q P1(mu)=z/R`, wyrażenie jest regularne w centrum, a czynnik
`1-q^2` zeruje perturbację na lustrze. Wybór tej obwiedni wymaga jawnego
zatwierdzenia przed obliczeniami.

## Wymagany propagator

Nowy solver musi całkować równanie eikonalne wewnątrz sfery i obsługiwać
specularne odbicie na `r=R`. Nie istnieje już asymptotyczny odcinek
field-free. Kontrakt powinien określić:

- liczbę lub kryterium zakończenia odbić,
- sposób porównania całych krzywych z wielu obserwatorów,
- wykrywanie konkurencyjnych minimów,
- niezależność wyniku od kroku integratora,
- odtwarzanie dokładnego rozwiązania Maxwella przy `epsilon=0`.

Ostatni punkt jest bramką jednostkową: implementacja numeryczna musi najpierw
odtworzyć analityczne wielkie okręgi i punkty wspólne w granicy zerowej
perturbacji.

## Kolejność po zatwierdzeniu obwiedni

1. Test numerycznego propagatora przy `epsilon=0` względem analitycznego `S3`.
2. Test lokalności: identyczna geometria, inna etykieta źródła.
3. Tania bramka C-3 dla małej siatki `epsilon`.
4. Dopiero dla kandydatów bez regresji C-3 — test skali na wspólnej kohorcie.
5. Pełne C-2 na końcu.
