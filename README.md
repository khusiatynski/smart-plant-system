# Smart Plant System

Nowa wersja projektu została przepisana z Javy do Pythona i działa jako desktopowa aplikacja GUI w `tkinter`.

## Funkcje

- nowoczesny dashboard z ikonami i ciemnym motywem
- symulacja czujników rośliny w trybie demo
- tryb `AUTO` i `REKA`
- ręczne sterowanie pompą i oświetleniem LED
- konfiguracja progów wilgotności gleby i światła
- logowanie danych do pliku CSV
- wykres wilgotności gleby i natężenia światła
- przygotowany tryb UART

## Uruchomienie

Wymagany jest Python 3.

```powershell
python app.py
```

## Pliki

- `app.py` - główna aplikacja
- `logs/plant-log.csv` - log pomiarów
- `index.html` - strona opisowa projektu

## Repozytorium

Projekt został zmigrowany z wersji Java do jednej aplikacji Python i oczyszczony ze starych katalogów po Javie.
