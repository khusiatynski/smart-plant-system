# Smart Plant System - Schemat Elektryczny
**Wersja: 1.0 - Produkcja**

---

## 📋 Spis Treści
1. [Schemat Blokowy](#schemat-blokowy)
2. [Połączenia Pin-po-Pin](#połączenia-pin-po-pin)
3. [Sekcja Zasilania](#sekcja-zasilania)
4. [Czujniki Analogowe](#czujniki-analogowe)
5. [Magistrala I2C](#magistrala-i2c)
6. [Sekcja Mocy (Pompa + LED)](#sekcja-mocy)
7. [Lista Elementów](#lista-elementów)
8. [Uwagi Bezpieczeństwa](#uwagi-bezpieczeństwa)

---

## 🔌 Schemat Blokowy

```
                    ┌─────────────────────────────┐
                    │                             │
    Zasilanie 5V ───┤  Arduino Nano (CH340)       │
    USB lub DC   ───┤  ATmega328P @ 16MHz         │
                    │                             │
                    └─────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ANALOGOWE              I2C (TWI)              CYFROWE
        │                     │                     │
    ┌───┴───┐           ┌────┴────┐           ┌────┴────┐
    │       │           │         │           │         │
    A0  A1  A2      SDA(A4) SCL(A5)         D3      D5
    │   │   │           │         │           │         │
    │   │   │       ┌───┴───┐ ┌──┴──┐    ┌──┴──┐  ┌───┴───┐
    │   │   │       │BME280 │ │LCD  │    │PUMP │  │LED 3W │
    │   │   │       │Sensor │ │(opt)│    │ DC  │  │Grow   │
    │   │   │       └───────┘ └─────┘    └─────┘  └───────┘
    │   │   │
 ┌──┴─┐ │ ┌─┴──┐
 │Soil│ │ │Light│
 │Sens│ │ │Photo│
 └────┘ │ └────┘
      ┌─┴──┐
      │Water│
      │Level│
      └────┘
```

---

## 📍 Połączenia Pin-po-Pin

### **Arduino Nano Pinout**

```
              USB
               │
        ┌──────┴──────┐
    D13 │●          ●│ D12      ← SPI (opcja SD)
    3V3 │●          ●│ D11/MOSI ← SPI
    REF │●          ●│ D10/SS   ← SPI
    A0  │●   NANO  ●│ D9
    A1  │●          ●│ D8
    A2  │●          ●│ D7
    A3  │●          ●│ D6
    A4  │● (SDA)   ●│ D5  ← LED Grow (PWM)
    A5  │● (SCL)   ●│ D4
    A6  │●          ●│ D3  ← Pompa (PWM)
    A7  │●          ●│ D2
    5V  │●          ●│ GND
    RST │●          ●│ RST
    GND │●          ●│ RX0
    VIN │●          ●│ TX1
        └─────────────┘
```

---

## ⚡ Sekcja Zasilania

### **Wymagane Napięcia:**
| Element | Napięcie | Prąd | Uwagi |
|---------|----------|------|-------|
| Arduino Nano | 5V | ~50mA | USB lub VIN (7-12V) |
| BME280 | 3.3V lub 5V | <1mA | Sprawdź moduł! |
| Czujnik gleby M335 | 3.3-5V | <30mA | |
| Czujnik wody | 3.3-5V | <30mA | |
| Fotoresystor LM393 | 3.3-5V | <15mA | |
| LCD I2C (opcja) | 5V | ~30mA | |
| Pompa DC 3-5V | 5V | **500-800mA** | Osobne zasilanie! |
| LED 3W Full Spectrum | 3-3.5V | **700mA** | Osobne zasilanie! |

### **⚠️ KRYTYCZNE: Zasilanie mocy**

```
┌─────────────────────────────────────────────────────────────┐
│  NIE podłączaj pompy/LED do pinu 5V Arduino!                │
│  Arduino może dostarczyć MAX 500mA → przepalenie!           │
│                                                               │
│  ROZWIĄZANIE: Osobny zasilacz 5V/2A dla pompy + LED         │
└─────────────────────────────────────────────────────────────┘

Schemat zasilania:

    ┌──────────┐
    │ Zasilacz │
    │  5V 2A   │
    └────┬─────┘
         │
    ┌────┴────┐
    │    +    │────► Pompa (przez MOSFET)
    │         │
    │    +    │────► LED 3W (przez MOSFET + rezystor)
    │         │
    │   GND   │────┐
    └─────────┘    │
                   │
    ┌──────────┐   │
    │  Arduino │   │
    │   Nano   │   │
    │   GND    │───┴─────► WSPÓLNA MASA (!!!)
    └──────────┘
```

**UWAGA:** Wszystkie masy muszą być połączone razem!

---

## 📡 Czujniki Analogowe

### **1. Czujnik Wilgotności Gleby M335 → A0**

```
   Czujnik M335
   ┌─────────┐
   │   VCC   │────► 5V Arduino
   │   GND   │────► GND Arduino
   │   SIG   │────► A0
   └─────────┘
```

**Kalibracja:**
- Sucha ziemia: ~0-200 (ADC)
- Wilgotna: ~400-600
- W wodzie: ~800-1023

**Kod konwertuje:** `map(analogRead(A0), 0, 1023, 0, 100)`

---

### **2. Czujnik Poziomu Wody → A1**

```
   Czujnik Wody
   ┌─────────┐
   │    +    │────► 5V Arduino
   │    -    │────► GND Arduino
   │    S    │────► A1
   └─────────┘
```

**Uwaga:** Kontakty mogą korodować w wodzie → regularna wymiana!

---

### **3. Fotoresystor LM393 → A2**

```
   Moduł LM393 (z komparatorem)
   ┌─────────┐
   │   VCC   │────► 5V Arduino
   │   GND   │────► GND Arduino
   │   AO    │────► A2 (analogowy)
   │   DO    │──x  (nie używamy)
   └─────────┘
```

**Kalibracja:**
- Ciemno: ~900-1023
- Światło: ~0-300

**Kod konwertuje:** `map(analogRead(A2), 0, 1023, 0, 100)`  
*Uwaga: odwrotna skala - mniej światła = więcej voltage*

---

## 🔗 Magistrala I2C (TWI)

### **BME280 → A4 (SDA) + A5 (SCL)**

```
   Moduł BME280 (kupiony)
   ┌─────────┐
   │   VCC   │────► 5V Arduino ✅
   │   GND   │────► GND Arduino
   │   SDA   │────► A4 (SDA)
   │   SCL   │────► A5 (SCL)
   └─────────┘

⚠️ Adres I2C: 0x76 lub 0x77
   (kod automatycznie sprawdza oba)
```

**✅ Większość modułów BME280 ma:**
- Wbudowany regulator 3.3V (AMS1117-3.3)
- Level shifter 5V↔3.3V (BSS138 MOSFET)
- Można bezpiecznie zasilać 5V

**⚠️ Sprawdź przed podłączeniem:**
- Jeśli moduł ma **4 piny** (VCC, GND, SDA, SCL) → prawdopodobnie 5V OK
- Jeśli moduł ma **6-8 pinów** (CSB, SDO, etc.) → sprawdź czy ma regulator
- Szukaj na płytce układu **662K** lub **AMS1117** → to regulator 3.3V

**Jeśli NIE ma regulatora:**
- Podłącz do 3.3V Arduino (nie 5V!)
- Użyj level shiftera dla SDA/SCL

---

### **LCD I2C 16x2 (opcjonalne) → A4 + A5**

```
   LCD z I2C
   ┌─────────┐
   │   VCC   │────► 5V Arduino
   │   GND   │────► GND Arduino
   │   SDA   │────► A4 (SDA) ───┐
   │   SCL   │────► A5 (SCL) ───┤ równolegle z BME280
   └─────────┘                  │
```

**Adres I2C:** Zazwyczaj 0x27 lub 0x3F

---

## 🔋 Sekcja Mocy (Pompa + LED)

### **✅ Moduł PWM 2x MOSFET 400W (KUPIONY)**

**Specyfikacja modułu:**
- Model: XY-MOS
- 2x tranzystor N-MOSFET (AOD4184A)
- Napięcie sterowania: 3.3V-20V (logic-level!)
- Napięcie zasilania: 5-36V DC
- Obciążenie: 15A ciągłe (30A z chłodzeniem)
- Moc: 400W
- Wymiary: 17x34mm
- Złącza: Śrubowe (AK)
- LED: Sygnalizacja pracy
- PWM: do 20kHz

#### **Pinout modułu:**
```
   Moduł PWM 2x MOSFET
   ┌────────────────┐
   │  VCC   (5-36V) │◄─── Zasilacz 5V 2A (+)
   │  GND           │◄─── GND wspólna
   │                │
   │  CH1/PWM1      │◄─── D3 Arduino (pompa)
   │  CH2/PWM2      │◄─── D5 Arduino (LED)
   │                │
   │  OUT1+ OUT1-   │───► Pompa DC
   │  OUT2+ OUT2-   │───► LED 3W (+ rezystor!)
   └────────────────┘
```

---

### **1. Połączenie Pompy → Kanał 1**

```
                    ┌──────────────────┐
                    │   Zasilacz 5V    │
                    │      2A          │
                    └────┬─────────┬───┘
                         │         │
                    +5V  │         │ GND
                         │         │
    ┌────────────────────┼─────────┼──────────┐
    │  Moduł PWM MOSFET  │         │          │
    │                    │         │          │
    │  VCC ──────────────┘         │          │
    │  GND ────────────────────────┘          │
    │                                          │
    │  CH1/PWM1 ◄──────────── D3 Arduino      │
    │                                          │
    │  OUT1+ ───────┐                          │
    │  OUT1- ───┐   │                          │
    └───────────┼───┼──────────────────────────┘
                │   │
                │   └────► Pompa DC (+)
                └────────► Pompa DC (-)
```

**⚠️ Moduł ma WBUDOWANE diody flyback!**
- Nie trzeba dodawać zewnętrznych diod
- Można bezpiecznie sterować silnikami

**Kod Arduino:**
```cpp
digitalWrite(PIN_PUMP, HIGH);  // Pompa ON
digitalWrite(PIN_PUMP, LOW);   // Pompa OFF
```

---

### **2. Połączenie LED 3W → Kanał 2**

```
    ┌────────────────────────────────────────┐
    │  Moduł PWM MOSFET                      │
    │                                        │
    │  CH2/PWM2 ◄──────────── D5 Arduino    │
    │                                        │
    │  OUT2+ ───────┐                        │
    │  OUT2- ───┐   │                        │
    └───────────┼───┼────────────────────────┘
                │   │
                │   │    ┌──────────┐
                │   └────┤ Rezystor │  2.2Ω 5W
                │        │  MOCY    │
                │        └─────┬────┘
                │              │
                │        ┌─────┴─────┐
                │        │  LED 3W   │
                │        │ Epistar   │
                │        └─────┬─────┘
                │              │
                └──────────────┘
```

**⚠️ Rezystor 2.2Ω 5W jest OBOWIĄZKOWY!**
- LED 3W @ 3.2V forward voltage
- Prąd: 700mA
- Rezystor: (5V - 3.2V) / 0.7A = 2.57Ω → użyj 2.2Ω
- Moc: (5V - 3.2V)² / 2.2Ω = 1.5W → **MINUMUM 5W!**

**Kod Arduino:**
```cpp
analogWrite(PIN_LED, 255);  // LED 100%
analogWrite(PIN_LED, 128);  // LED 50%
analogWrite(PIN_LED, 0);    // LED OFF
```

---

## 🧰 Lista Elementów (KUPIONE)

### **Główne komponenty:**
| Lp. | Element | Specyfikacja | Link |
|-----|---------|--------------|------|
| 1 | Arduino Nano V3 | CH340, USB-C, 5V | [Allegro](https://allegro.pl/oferta/arduino-nano-v3-0-atmega328-ch340-usb-c-zlutowany-18313378391) |
| 2 | Czujnik gleby M335 | Analogowy, odporny na korozję | [Allegro](https://allegro.pl/oferta/czujnik-wilgotnosci-gleby-m335-sensor-higrometr-odporny-na-korozje-arduino-17595903542) |
| 3 | Czujnik poziomu wody | Analogowy | [Allegro](https://allegro.pl/oferta/analogowy-czujnik-poziomu-wody-deszczu-modul-arduino-15587730642) |
| 4 | **Moduł PWM 2x MOSFET 400W** | 15A, 5-36V, logic-level | [Allegro](https://allegro.pl/oferta/modul-pwm-2x-mosfet-regulator-mocy-400w-arduino-12935378544) |
| 5 | LM393 czujnik światła | Fotoresystor 4-pin | [Allegro](https://allegro.pl/oferta/lm393-modul-czujnik-swiatla-fotorezystor-4pin-31mm-x-14mm-14835936181) |
| 6 | Czytnik kart micro SD | SPI, 3.3V | [Allegro](https://allegro.pl/oferta/mini-modul-czytnik-kart-pamieci-micro-sd-spi-3-3v-arduino-15587875371) |
| 7 | BME280 | I2C, temp + wilgotność + ciśnienie | [Allegro](https://allegro.pl/oferta/bme280-pomiar-temperatury-wilgotnosci-i-cisnienia-17603546442) |
| 8 | Pompa DC JT-DC3W | 3-5V, 70-120L/H | [Allegro](https://allegro.pl/oferta/jt-dc3w-pompa-wody-plynu-dc-3-5v-70-120l-h-17599442508) |
| 9 | Wężyki | Do pompki | - |
| 10 | LED 3W Epistar | Full Spectrum, 700mA | [Allegro](https://allegro.pl/oferta/dioda-power-led-3w-epistar-white-full-spectrum-45mil-pcb-14465221442) |
| 11 | LCD I2C 16x2 (opcja) | Wyświetlacz | - |

### **Elementy pasywne - DO KUPIENIA:**
| Ilość | Element | Wartość | Uwagi |
|-------|---------|---------|-------|
| 1 | **Rezystor mocy** | **2.2Ω 5W** | **KRYTYCZNY - dla LED 3W!** |
| 10 | Kable dupont | F-F, M-F | Połączenia |
| 1 | Płytka stykowa | 830 pkt | Prototyp (opcja) |
| 1 | Zasilacz | 5V 2A | DC power supply |

### **Opcjonalne - DO KUPIENIA:**
| Ilość | Element | Uwagi |
|-------|---------|-------|
| 1 | Radiator | Dla LED 3W (zalecane!) |
| 1 | Pasta termoprzewodząca | Do radiatora LED |
| 1 | Obudowa | Wodoodporna IP65 |
| 1 | Level shifter 5V↔3.3V | Dla czytnika SD (SPI) |

---

## ⚠️ Uwagi Bezpieczeństwa

### **🔴 KRYTYCZNE:**

1. **WSPÓLNA MASA (GND)**
   ```
   Arduino GND ─┬─ Zasilacz GND
                ├─ Moduł PWM GND
                ├─ Wszystkie czujniki GND
                └─ NIGDY nie rozdzielaj!
   ```

2. **OSOBNE ZASILANIE mocy**
   - Arduino: USB (5V 500mA) lub DC 7-12V
   - Pompa + LED: **Osobny zasilacz 5V 2A**
   - Moduł PWM VCC → zasilacz 5V (**NIE** Arduino 5V!)
   - **NIE łącz** linii +5V Arduino z zasilaczem!

3. **Rezystor mocy dla LED**
   - LED 3W bez rezystora = 💥 natychmiast!
   - Użyj 2.2Ω **5W** (nie 1/4W - przepali się!)
   - Podłącz **szeregowo**: zasilacz → rezystor → LED

4. **BME280 - sprawdź napięcie!**
   - Moduł z 4 pinami (VCC, GND, SDA, SCL) → zazwyczaj 5V OK
   - Szukaj regulatora **662K** lub **AMS1117** na module
   - Jeśli NIE ma regulatora → tylko 3.3V!

5. **Moduł PWM - nie przeciążaj!**
   - Max 15A ciągły na kanał
   - Pompa ~0.5A + LED ~0.7A = OK ✅
   - Dodaj chłodzenie jeśli > 10A

---

### **🟡 WAŻNE:**

6. **Czujnik wody - korozja**
   - Regularnie czyść kontakty
   - Rozważ czujnik ultradźwiękowy (bezkontaktowy)

7. **SD card reader - 3.3V!**
   - Większość: tylko 3.3V logic
   - Podłącz do 3.3V Arduino
   - Użyj level shiftera 5V→3.3V dla SPI

8. **LED 3W - chłodzenie**
   - LED generuje ciepło (1.2W)
   - Dodaj radiator aluminiowy
   - Pasta termoprzewodząca

9. **Izolacja**
   - Jeśli używasz w ziemi/wodzie → obudowa IP65
   - Uszczelki dla przewodów
   - Silikon na połączenia

10. **Moduł PWM - montaż**
    - Złącza śrubowe - dokręć mocno
    - Sprawdź polaryzację OUT1/OUT2
    - LED na module świeci gdy aktywny

---

## 🔧 Montaż Krok-po-Kroku

### **Krok 1: Zasilanie**
1. Podłącz Arduino przez USB (testy)
2. Przygotuj zasilacz 5V 2A
3. **Połącz wszystkie GND razem:** Arduino GND + Zasilacz GND + Moduł PWM GND

### **Krok 2: Czujniki**
1. BME280 → I2C (A4, A5) + VCC→5V, GND→GND
2. Czujnik gleby M335 → VCC→5V, GND→GND, SIG→A0
3. Czujnik wody → +→5V, -→GND, S→A1
4. Fotoresystor LM393 → VCC→5V, GND→GND, AO→A2
5. Test: uruchom kod, sprawdź Serial Monitor

### **Krok 3: Moduł PWM + Pompa + LED**
1. **Moduł PWM podłączenie:**
   - VCC → Zasilacz 5V (+)
   - GND → GND wspólna
   - CH1/PWM1 → D3 Arduino
   - CH2/PWM2 → D5 Arduino

2. **Pompa do OUT1:**
   - Pompa (+) → OUT1+
   - Pompa (-) → OUT1-
   - Test: `digitalWrite(3, HIGH)` → pompa powinna działać

3. **LED 3W do OUT2:**
   - **WAŻNE:** Najpierw przylutuj rezystor 2.2Ω 5W do nóżki LED!
   - Zasilacz 5V → Rezystor 2.2Ω → LED+ → OUT2+
   - LED- → OUT2-
   - Przykręć radiator do LED (pasta termoprzewodząca!)
   - Test: `analogWrite(5, 128)` → LED powinien świecić

### **Krok 4: Finalizacja**
1. Zabezpiecz połączenia (lutowanie/złącza śrubowe)
2. Testuj w trybie AUTO i MANUAL
3. Sprawdź GUI przez Serial
4. Umieść w obudowie
5. Instaluj w docelowym miejscu

---

## ⚠️ **KRYTYCZNE - Sprawdź przed włączeniem zasilania:**

1. **Rezystor 2.2Ω 5W jest podłączony szeregowo z LED?**
   - Bez niego LED przepali się natychmiast!
   
2. **Wspólna masa połączona?**
   - Arduino GND
   - Zasilacz GND
   - Moduł PWM GND
   - Wszystkie czujniki GND

3. **Moduł PWM VCC podłączony do zasilacza 5V, NIE do Arduino 5V?**
   - Arduino może dać max 500mA
   - Pompa + LED = ~1.2A → przepalenie Arduino!

## 📝 Sprawdzenie Przed Uruchomieniem

- [ ] Wszystkie GND połączone razem (Arduino + zasilacz + moduł PWM)
- [ ] Arduino zasilane przez USB (testy) lub VIN 7-12V
- [ ] Pompa + LED na osobnym zasilaczu 5V 2A
- [ ] Moduł PWM podłączony:
  - [ ] VCC → zasilacz 5V
  - [ ] GND → GND wspólna
  - [ ] CH1/PWM1 → D3 Arduino
  - [ ] CH2/PWM2 → D5 Arduino
  - [ ] OUT1 → Pompa
  - [ ] OUT2 → Rezystor 2.2Ω 5W → LED 3W
- [ ] Rezystor 2.2Ω 5W szeregowo z LED (KRYTYCZNE!)
- [ ] BME280 podłączony (sprawdź czy 5V OK - moduł z regulatorem)
- [ ] Czujniki analogowe: gleba→A0, woda→A1, światło→A2
- [ ] Kod wgrany, Serial Monitor pokazuje dane
- [ ] Połączenie z GUI działa

---

## 🎓 Dodatkowe Zasoby

- **Datasheet IRLZ44N:** [Link](https://www.infineon.com/dgdl/irlz44n.pdf)
- **BME280 Library:** Adafruit BME280
- **Kalkulator rezystorów dla LED:** [Link](https://www.digikey.com/en/resources/conversion-calculators/conversion-calculator-led-series-resistor)

---

**Autor:** Smart Plant System Team  
**Data:** 2026-04-12  
**Wersja:** 1.0 Production
