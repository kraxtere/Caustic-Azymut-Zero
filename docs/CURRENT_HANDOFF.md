# Caustic Azymut Zero — aktualne przekazanie

## Repozytorium i publikacja

- Repozytorium: `kraxtere/Caustic-Azymut-Zero`
- Główna gałąź: `main`
- GitHub Pages: `https://kraxtere.github.io/Caustic-Azymut-Zero/`
- Workflow: `.github/workflows/deploy-pages.yml`
- Każdy push do `main` uruchamia testy, build Vite i publikację katalogu `dist`.

## Aktualny stan interfejsu

- interaktywna scena inwersji sferycznej,
- katalog Słońca, Księżyca, planet i wybranych gwiazd,
- wiele kopuł obserwatorów,
- gładkie analityczne krzywe bazowej inwersji,
- osobna granica przejścia: krzywa do granicy, prosty odcinek od granicy do oka,
- tabela odległości oraz skali po transformacji,
- panel otoczenia punktu `P∞` z logarytmicznym powiększeniem,
- porównanie mapy stereograficznej i azymutalnej równodystansowej,
- zsynchronizowane trajektorie planet w widoku geocentrycznym, heliocentrycznym i po inwersji,
- tryby 1 rok, 5 lat i cykl synodyczny,
- pełna albo narastająca ścieżka oraz sterowanie prędkością,
- zwijane panele,
- osobne laboratorium refrakcji jako narzędzie pomocnicze.

## Walidacja

- `npm test`: 24/24 testy przechodzą,
- `npm run build`: przechodzi,
- Vite używa `base: './'`, więc zasoby działają w podkatalogu GitHub Pages.

## Ważne rozróżnienia

- Analityczne łuki dotyczą bazowej, czystej inwersji sferycznej.
- Granica prostego odcinka jest obecnie parametrem prezentacyjnym, a nie jeszcze wyprowadzoną granicą fizycznego ośrodka.
- Skala logarytmiczna przy `P∞` służy wyłącznie czytelności; nie zmienia wyniku transformacji.
- GitHub jest od tej chwili głównym miejscem przechowywania kodu. Hosting ChatGPT nie powinien być traktowany jako źródło projektu.

## Najbliższy rozsądny krok

Sprawdzić produkcyjną wersję GitHub Pages na telefonie i komputerze. Następnie poprawiać sam model oraz interfejs poprzez commity do `main`, pozostawiając publikację workflow GitHub Actions.
