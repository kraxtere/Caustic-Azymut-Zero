# Caustic Azymut Zero

Eksperymentalne laboratorium do odwzorowywania obserwacji na azymutalnej mapie równodystansowej i badania modeli propagacji promienia nad płaszczyzną.

## Stan początkowy

Repozytorium zawiera teraz:

- uruchamialną aplikację 3D w Vite + TypeScript + Three.js,
- azymutalną mapę z siatką i liniami lądów,
- położenie obserwatora i źródła na elipsoidalnej kopule,
- krzywą Béziera odtwarzającą geometryczny punkt wyjścia aplikacji FE-Dome,
- czyste moduły matematyczne i testy,
- zachowaną kopię oryginalnego kodu Waltera Bislina w `reference/walter-bislin/`,
- miejsce w architekturze na model pola toroidalnego, integrator promieni i dopasowanie do obserwacji.

Krzywa Béziera jest tutaj **modelem bazowym do porównań**, a nie fizycznym wyjaśnieniem ugięcia światła. Następny model powinien określać równanie pola, warunki brzegowe i kryterium dopasowania do danych obserwacyjnych. Szczegóły są w [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Uruchomienie

Wymagany jest Node.js 22 lub nowszy.

```bash
npm install
npm run dev
```

Kontrola jakości:

```bash
npm run check
```

## Układ projektu

```text
src/model/       obliczenia niezależne od interfejsu i renderera
src/scene/       scena Three.js
src/ui/          kontrolki i prezentacja wyników
tests/           testy matematyki modelu
docs/            konwencje oraz plan dalszej rozbudowy
reference/       niemodyfikowana baza źródłowa FE-Dome
```

## Pochodzenie bazy

Punktem odniesienia jest aplikacja **FE-Dome App** Waltera Bislina. Strona źródłowa oznacza materiał jako Public Domain. Pełne informacje i linki znajdują się w [`ATTRIBUTION.md`](ATTRIBUTION.md).

Projekt ma charakter obliczeniowy i porównawczy. Każdy przyszły wariant pola warto sprawdzać jednocześnie względem surowych obserwacji oraz standardowego modelu astronomicznego z refrakcją atmosferyczną.
