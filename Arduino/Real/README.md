# Arduino Real

Kod dla fizycznego Arduino Nano.

Zakładane podłączenia:

- `A0` - czujnik wilgotności gleby
- `A1` - czujnik światła
- `A2` - czujnik poziomu wody
- `A4/A5` - BME280 po I2C
- `D6` - sterowanie LED grow
- `D7` - sterowanie przekaźnikiem pompy

Przed uruchomieniem na prawdziwym układzie skalibruj zakresy analogowe w pliku `smart_plant_real.ino`.
