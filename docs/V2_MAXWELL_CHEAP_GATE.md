# Zamrożona tania bramka Maxwella v2

## Status przed uruchomieniem

Kryteria w tym dokumencie są deklarowane przed pierwszym przebiegiem danych
centrum Słońca i C-3. Nie wolno ich zmieniać na podstawie otrzymanego wyniku.

Pierwszym kandydatem jest pełna sferyczna soczewka Maxwella z lustrem:

- `R = pi * R_MAP = 20015,086796 km`,
- `centre = (0, 0, 0) km`,
- obserwatorzy leżą na azymutalnej płaszczyźnie `z=0`,
- pierwszy dodatni interwał `0 <= alpha <= pi`,
- 16 restartów wyboru gałęzi dla każdego z czterech ziaren
  `3, 17, 91, 2048`,
- 15 grup centrum Słońca i dwa osobne bieguny C-3,
- bez brzegów tarczy C-2, RK45 i dopasowania parametrów.

## Wspólna metryka porównawcza

Kilometry residuum płaskich półprostych i kilometry cięciwy na pomocniczej
`S^3` nie są tą samą wielkością. Nie wolno ich bezpośrednio porównywać.
Dlatego bramka używa dla obu modeli RMS błędu kierunku w stopniach:

```text
angle(observed_direction, direction_predicted_to_fitted_source).
```

Dla `n=1` wspólne źródło jest rekonstruowane istniejącą triangulacją
półprostych. Dla Maxwella źródło daje solver `4×4` z wyborem gałęzi, a kierunek
do niego jest odtwarzany dokładnie na wielkim okręgu. Raport zachowuje również
modelowo natywne RMS w kilometrach, ale nie używa ich do porównania między
geometriami.

## Bramka promocji do pełnego C-2

Kandydat przechodzi wyłącznie wtedy, gdy wszystkie warunki są spełnione
jednocześnie:

1. wszystkie 15 centrów Słońca i oba bieguny mają ważną, niedegenerowaną
   rekonstrukcję,
2. średni kierunkowy RMS centrów Słońca jest ściśle niższy niż dla `n=1`,
3. kierunkowy RMS północnego bieguna jest ściśle niższy niż dla `n=1`,
4. kierunkowy RMS południowego bieguna jest ściśle niższy niż dla `n=1`,
5. każda obserwacja Maxwella leży na pierwszym dodatnim interwale drogi,
6. wszystkie cztery ziarna wskazują ten sam najlepszy punkt z dokładnością
   `1e-6 R` na pomocniczej sferze,
7. oba bieguny nie zapadają się w jeden punkt: ich pomocnicza separacja kątowa
   musi być większa niż `1e-3 rad`,
8. oba źródła biegunowe oraz wszystkie źródła słoneczne leżą wewnątrz lustra
   i nie poniżej płaszczyzny mapy.

Warunek 7 wykrywa numeryczną degenerację wspólnego centrum; nie narzuca z góry
antypodalności ani konkretnej odległości biegunów. Warunki 5 i 8 są
odpowiednikiem dotychczasowej kontroli półprostych i powrotu pod mapę.

## Decyzja po przebiegu

- `PASS`: wolno uruchomić pełne C-2 z czterema brzegami tarczy bez zmiany
  geometrii i progów.
- `FAIL`: pełne C-2 pozostaje zablokowane. Wynik ma wskazać osobno, czy zawiódł
  RMS, droga w przód, stabilność restartów, położenie źródła czy rozdzielenie
  biegunów.
