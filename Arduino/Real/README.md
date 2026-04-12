# Arduino Real

Kod dla fizycznego Arduino Nano.

Zakładane podłączenia:

- `A0` - czujnik wilgotności gleby
- `A1` - czujnik światła
- `A2` - czujnik poziomu wody
- `A4/A5` - BME280 po I2C
- `D6` - sterowanie LED grow
- `D7` - sterowanie przekaźnikiem pompy

Pliki:

- `smart_plant_real.ino` - bazowa wersja dla rzeczywistego układu
- `smart_plant_gui_sync.ino` - wersja zsynchronizowana z GUI przez UART

Do testów z aplikacją desktopową użyj `smart_plant_gui_sync.ino`.

Przed uruchomieniem na prawdziwym układzie skalibruj zakresy analogowe i sprawdź przypisanie pinów.
