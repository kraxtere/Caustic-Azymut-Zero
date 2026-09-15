# Zamrożony kontrakt propagatora lokalnego dipola v2.1

## Pole

```text
relative = x - centre
r = |relative|
z = relative_z
q = r/R
n_M = 2 n0 / (1+q^2)
phi = epsilon * (z/R) * (1-q^2)
n = n_M * exp(phi)
```

Gradient jest liczony analitycznie. Pole nie otrzymuje daty, deklinacji ani
identyfikatora źródła.

## Propagacja

Równanie eikonalne jest całkowane wewnątrz `r<R` po fizycznej długości toru:

```text
dx/ds = T
dT/ds = [grad(n) - (grad(n) dot T) T] / n
dLopt/ds = n
```

Na `r=R` stosowane jest specularne odbicie kierunku. Integracja kończy się po
osiągnięciu zadanej długości optycznej. Dla `epsilon=0` i kąta centralnego
`alpha` celem jest `Lopt=n0*R*alpha`, dokładnie jak w rozwiązaniu `S3`.

## Bramki przed danymi obserwacyjnymi

1. Wartość pola na lustrze wynosi dokładnie `n0` dla różnych szerokości.
2. Pole i gradient są skończone w centrum; gradient analityczny zgadza się z
   różnicą centralną z względnym błędem `<=1e-6` poza punktami o zerowym
   gradiencie.
3. Dla `epsilon=0` co najmniej 12 kombinacji położenia, kierunku i kąta,
   obejmujących tory bez odbicia i z odbiciem, spełnia jednocześnie:
   - błąd punktu `<=1e-7 R`,
   - błąd kierunku `<=1e-5 deg`,
   - zgodną parzystość odbicia.
4. Zaostrzenie tolerancji integratora o czynnik 10 zmienia punkt końcowy o
   najwyżej `1e-7 R`.
5. Zmiana etykiety źródła przy identycznym stanie początkowym nie może zmienić
   toru; interfejs propagatora nie przyjmuje takiej etykiety.

Niespełnienie dowolnej bramki zatrzymuje pracę przed C-3. Progów nie zmieniamy
po zobaczeniu wyniku.

## Zakres pierwszego etapu

Ten kontrakt waliduje propagator i pole, nie dobiera `epsilon`. Dopiero po
PASS wolno przygotować osobny, zamrożony skan C-3. Analityczny wynik `4x4`
przy `epsilon=0` będzie punktem startowym późniejszego dopasowania krzywych,
ale każdy restart i konkurencyjne minimum pozostają raportowane osobno.
