# Zamrożony diagnostyczny skan deklinacji Maxwella v2

## Pytanie

Sprawdzamy, czy skala odwzorowania tarczy jest gładką, monotoniczną funkcją
deklinacji przy niezerowym `z0`. Potwierdzenie wspiera hipotezę, że sezonowy
problem skali jest strukturalnym skutkiem przesunięcia, które wcześniej
naprawiło asymetrię biegunów, a nie szczególną wadą jednego `R`.

Skan nie testuje kolejnego promienia i nie jest pełnym C-2.

## Zamrożony projekt

- kandydat bez zmian: `R/Rbase=1,20`, `z0/Rbase=0,40`,
- dziewięć równomiernych deklinacji od `-23,44°` do `+23,44°`,
- jedna wspólna chwila `2026-03-20 13:00 UTC`,
- RA dobrana do południka Greenwich w tej chwili,
- jedna wspólna kohorta obserwatorów widzących wszystkie próbki,
- dla każdej deklinacji: centrum oraz cztery brzegi tarczy,
- stały wejściowy promień `0,2666°`, aby izolować odpowiedź geometrii od
  sezonowej zmiany odległości Słońca,
- cztery ziarna `3,17,91,2048`, po 16 restartów.

Choć skan jest nazywany „centrum” w odróżnieniu od pełnych torów C-2, sama
średnica wymaga czterech brzegów. Koszt obejmuje więc tylko jedną tarczę na
deklinację, a nie pięć chwil dziennych.

## Metryka i decyzja

Raportuje się:

```text
normalised_transfer_scale = mean_diameter_km / input_angular_diameter_rad
```

Normalizacja usuwa znany rozmiar wejściowy. Hipoteza jest oznaczona jako
`SUPPORTED` wyłącznie wtedy, gdy:

1. wszystkie dziewięć tarcz ma ważny wynik i konsensus punktu oraz pełnych
   przypisań `P/JPJ`,
2. skala jest ściśle monotoniczna na wszystkich ośmiu przedziałach,
3. dopasowanie liniowe skali do deklinacji ma `R^2 >= 0,95`.

Brak spełnienia nie dowodzi automatycznie braku zależności; oznacza tylko, że
konkretna hipoteza gładkiej, monotonicznej odpowiedzi nie została potwierdzona
tym skanem. Wynik nie zmienia progów skorygowanego C-2.
