# Przekazanie solvera i stan po integracji

## Decyzja architektoniczna

Nie zakładamy powierzchni ani wysokości źródła. Promienie są prowadzone wstecz
od obserwatorów, zgodnie z kierunkami alt-az, aż do obszaru zaniku pola.
Punkt i kierunek wyjścia definiują asymptotyczną półprostą. Dla jednego
obiektu i chwili mierzymy zbieżność półprostych wielu obserwatorów.

Krzywa Béziera FE-Dome pozostaje wyłącznie odniesieniem wizualnym. Nie jest
celem dopasowania.

## Otrzymany pakiet

Pakiet wejściowy zawierał:

- efemerydę Słońca Meeusa,
- projekcję azymutalną i lokalną bazę E/N/U,
- pięcioparametrowe pole `n(rho,z)`,
- integrator RK45 i triangulację prostych,
- demonstrację bazową,
- niedokończone dopasowanie Neldera-Meada.

Wynik kontrolny został odtworzony: dla pięciu lokalizacji 21 czerwca 2026 o
15:00 UTC najlepsze przecięcie prostych ma wysokość około `5060 km`, a RMS
wynosi około `1069 km`.

## Zrealizowane po przejęciu

1. Wszystkie parametry są kodowane do `[0,1]^5`; `H` i `s` mają skalę logarytmiczną.
2. Podstawowym optymalizatorem jest `scipy.optimize.differential_evolution`.
3. Dostępny jest alternatywny wielostartowy Nelder-Mead.
4. Domyślny budżet zwiększono do 120 generacji i populacji 12.
5. Integrator faktycznie zatrzymuje się po zaniku całego pola; poprzednie zdarzenie było nieaktywne.
6. Promienie wracające do mapy, nieuciekające albo numerycznie uszkodzone są odrzucane.
7. Dodano metrykę półprostych, aby przecięcia za obserwatorem nie obniżały sztucznie kosztu.
8. Dodano diagnostykę rangi, uwarunkowania i kierunku przecięcia oraz 13 testów regresyjnych.

## Wynik wstępny

Skrócony przebieg globalny, następnie lokalne dopasowanie w dozwolonych
granicach, dał średni RMS `2314,03 km` wobec `2479,98 km` bez pola. To poprawa
o około `6,7%`, ale rozwiązanie doszło do granic amplitudy i szerokości
(`A=-0,1`, `s=100 km`). Nie wolno traktować go jako rozstrzygnięcia. Pełny
przebieg powinien sprawdzić stabilność tego minimum, a następnie osobny zbiór
kontrolny.
