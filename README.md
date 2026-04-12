# Smart Plant System

Projekt działa jako desktopowa aplikacja GUI w `tkinter`.

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

## Struktura

- `app.py` - launcher aplikacji z katalogu głównego
- `GUI/` - właściwy kod desktopowego GUI
- `Arduino/Wokwi/` - kod i pliki do symulacji w Wokwi
- `Arduino/Real/` - kod dla prawdziwego Arduino
- `schemat/` - miejsce na schematy połączeń i dokumentację montażu
- `logs/plant-log.csv` - log pomiarów
- `index.html` - strona opisowa projektu

## Wokwi

Publiczny projekt Wokwi:

`https://wokwi.com/projects/461119979508150273`

## Repozytorium

Repozytorium zawiera aplikację Python, stronę opisową projektu oraz logi pomiarów.
