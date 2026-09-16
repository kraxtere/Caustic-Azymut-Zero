# Wynik taniej bramki skali lokalnego dipola

## Werdykt

Zamrożona bramka kończy się **FAIL: 0/3 kandydatów**. Żadna z amplitud
`epsilon=0,10`, `0,20`, `0,40`, które przeszły C-3, nie poprawia transferu
skali względem kontroli `epsilon=0`.

Jest to konflikt kierunku odpowiedzi: dodatni dipol poprawia oba bieguny C-3,
ale na wspólnej kohorcie tarczy zwiększa wszystkie trzy zamrożone miary błędu
skali.

## Metryki

| `epsilon` | CV średnicy | asymetria `+-11,72 deg` | asymetria `+-23,44 deg` | wynik |
|---:|---:|---:|---:|---|
| `0,00` | `0,059486` | `0,099333` | `0,123598` | kontrola |
| `0,10` | `0,060461` | `0,099678` | `0,136016` | FAIL |
| `0,20` | `0,062660` | `0,101487` | `0,152060` | FAIL |
| `0,40` | `0,072374` | `0,110750` | `0,196679` | FAIL |

Przy `epsilon=0,40` CV jest większe od kontroli o `21,66%`, asymetria pary
pośredniej o `11,49%`, a asymetria przesileniowa o `59,13%`.

## Niezależne problemy diagnostyczne

Werdykt nie zależy wyłącznie od progu skali:

- przy `delta=-11,72 deg` wszystkie pięć elementów tarczy nie osiąga
  konsensusu konkurencyjnych minimów dla każdej badanej amplitudy, także dla
  kontroli;
- wszystkie rekonstruowane tarcze przekraczają zamrożony limit
  `axis_ratio <= 1,10`; zakres wynosi około `1,21-1,87` dla kontroli i
  `1,25-1,50` dla `epsilon=0,40`;
- źródła pozostają wewnątrz lustra i nad mapą, a marginesy `alpha` są
  zachowane — porażka nie wynika z drogi wstecz ani ucieczki źródła.

## Interpretacja i decyzja

Jednoparametrowa amplituda tej konkretnej lokalnej obwiedni nie może zostać
promowana do pełnego C-2. W badanym dodatnim zakresie poprawa C-3 i poprawa
skali nie występują razem. Nie wybieramy `epsilon=0,40` na podstawie najlepszego
RMS biegunów i nie zagęszczamy siatki.

Następny krok powinien być projektowy, nie obliczeniowy: rozdzielić stopień
swobody korygujący bieguny od stopnia swobody korygującego skalę/kształt
tarczy. Osobno trzeba opisać geometrię powtarzalnej niejednoznaczności przy
`delta=-11,72 deg`. Pełny C-2 pozostaje zablokowany.

Maszynowy raport: `solver/results/v2-local-dipole-scale-gate.json`.

