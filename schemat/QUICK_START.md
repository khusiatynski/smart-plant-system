# Smart Plant - Quick Start Guide
---

## 📐 Schemat Połączeń

```
┌──────────────────────────────────────────────────────────────┐
│                    Arduino Nano                              │
│                                                              │
│  5V ─────┬──► BME280 (VCC)                                  │
│          ├──► Czujnik gleby (VCC)                           │
│          ├──► Czujnik wody (+)                              │
│          └──► Fotoresystor (VCC)                            │
│                                                              │
│  GND ────┬──► BME280 (GND)                                  │
│          ├──► Czujnik gleby (GND)                           │
│          ├──► Czujnik wody (-)                              │
│          ├──► Fotoresystor (GND)                            │
│          └──► Moduł PWM (GND) ◄────┐                        │
│                                     │                        │
│  A4 ─────┬──► BME280 (SDA)          │                        │
│  A5 ─────┼──► BME280 (SCL)          │                        │
│          │                          │                        │
│  A0 ─────┼──► Czujnik gleby (SIG)   │                        │
│  A1 ─────┼──► Czujnik wody (S)      │                        │
│  A2 ─────┼──► Fotoresystor (AO)     │                        │
│          │                          │                        │
│  D3 ─────┼──► Moduł PWM (CH1/PWM1)  │                        │
│  D5 ─────┴──► Moduł PWM (CH2/PWM2)  │                        │
│                                     │                        │
└─────────────────────────────────────┼────────────────────────┘
                                      │
                  ┌───────────────────┴────────────┐
                  │   Zasilacz 5V 2A               │
                  │                                │
                  │   (+) ──► Moduł PWM (VCC)      │
                  │   (-) ──► Moduł PWM (GND) ─────┘
                  └────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  Moduł PWM 2x MOSFET                         │
│                                                              │
│  OUT1+ ──────────► Pompa (+)                                │
│  OUT1- ──────────► Pompa (-)                                │
│                                                              │
│  OUT2+ ──┐                                                  │
│          │    ┌────────────┐                                │
│          └────┤ Rezystor   │  2.2Ω 5W ◄─── KRYTYCZNY!      │
│               │    MOCY    │                                │
│               └─────┬──────┘                                │
│                     │                                        │
│               ┌─────┴─────┐                                 │
│               │  LED 3W   │  + radiator                     │
│               │  Epistar  │                                 │
│               └─────┬─────┘                                 │
│                     │                                        │
│  OUT2- ─────────────┘                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Instrukcja Krok-po-Kroku

### **1. Przygotowanie (5 min)**

1. **Sprawdź wszystkie elementy**
   - [ ] Arduino Nano
   - [ ] Moduł PWM
   - [ ] 5 czujników (BME280, gleba, woda, światło)
   - [ ] Pompa
   - [ ] LED 3W
   - [ ] **Rezystor 2.2Ω 5W** (dokup jeśli nie masz!)
   - [ ] Zasilacz 5V 2A

2. **Przylutuj rezystor do LED**
   - Rezystor 2.2Ω 5W szeregowo z LED
   - Zasilanie → rezystor → LED+ → OUT2+
   - LED- → OUT2-

---

### **2. Podłączenie czujników (5 min)**

#### **BME280 (I2C):**
```
BME280     Arduino Nano
VCC    →   5V
GND    →   GND
SDA    →   A4
SCL    →   A5
```

#### **Czujnik gleby M335:**
```
M335       Arduino Nano
VCC    →   5V
GND    →   GND
SIG    →   A0
```

#### **Czujnik wody:**
```
Czujnik    Arduino Nano
+      →   5V
-      →   GND
S      →   A1
```

#### **Fotoresystor LM393:**
```
LM393      Arduino Nano
VCC    →   5V
GND    →   GND
AO     →   A2
DO     →   (nie używamy)
```

---

### **3. Moduł PWM + Zasilanie (5 min)**

#### **Zasilacz → Moduł PWM:**
```
Zasilacz 5V 2A
(+)    →   Moduł PWM (VCC)
(-)    →   Moduł PWM (GND)
```

#### **Arduino → Moduł PWM (sygnały):**
```
Arduino    Moduł PWM
D3     →   CH1/PWM1  (pompa)
D5     →   CH2/PWM2  (LED)
GND    →   GND
```

#### **Moduł PWM → Urządzenia:**
```
OUT1+  →   Pompa (+)
OUT1-  →   Pompa (-)

OUT2+  →   Rezystor 2.2Ω → LED(+)
OUT2-  →   LED(-)
```

---

## ⚠️ **PRZED WŁĄCZENIEM - SPRAWDŹ:**

### **Checklist bezpieczeństwa:**

- [ ] **Wspólna masa:**
  - Arduino GND
  - Zasilacz (-)
  - Moduł PWM GND
  - Wszystkie czujniki GND
  - **Wszystko połączone razem!**

- [ ] **Zasilanie:**
  - Arduino → USB (5V)
  - Moduł PWM → Zasilacz 5V 2A (NIE Arduino 5V!)

- [ ] **Rezystor 2.2Ω 5W szeregowo z LED**
  - Bez niego LED przepali się natychmiast!

- [ ] **Polaryzacja:**
  - Pompa: (+) do OUT1+, (-) do OUT1-
  - LED: (+) przez rezystor do OUT2+, (-) do OUT2-

---

## 💻 Wgrywanie Kodu

### **1. Zainstaluj Arduino IDE**
- Pobierz z: https://www.arduino.cc/en/software

### **2. Zainstaluj bibliotekę BME280**
```
Narzędzia → Zarządzaj bibliotekami → Szukaj "Adafruit BME280"
→ Zainstaluj "Adafruit BME280 Library"
```

### **3. Wybierz płytkę**
```
Narzędzia → Płytka → Arduino Nano
Narzędzia → Procesor → ATmega328P
Narzędzia → Port → COM3 (lub inny)
```

### **4. Wgraj kod**
- Otwórz `sketch_gui_sync.ino`
- Kliknij "Wgraj" (strzałka w prawo)
- Czekaj na "Wgrywanie ukończone"

### **5. Sprawdź działanie**
```
Narzędzia → Monitor portu szeregowego
→ Ustaw: 9600 baud

Powinieneś zobaczyć:
Smart Plant System Ready
2026-04-12 11:35:28,55.0,22.5,58.3,1013.2,45.2,80.0,false,false
```

---

## 🎮 Testowanie

### **Test 1: Czujniki**
```cpp
// W Serial Monitor powinieneś widzieć:
// - temperatura 15-30°C
// - wilgotność 30-70%
// - ciśnienie 970-1045 hPa
// - wilgotność gleby 0-100%
// - poziom wody 0-100%
// - światło 0-100%
```

### **Test 2: Pompa**
```cpp
// W Arduino IDE → Serial Monitor wpisz:
PUMP:ON
// Pompa powinna się włączyć, LED na module świeci

PUMP:OFF
// Pompa wyłącza się
```

### **Test 3: LED Grow**
```cpp
// W Serial Monitor wpisz:
LED:ON
// LED powinien świecić, LED na module świeci

LED:OFF
// LED wyłącza się
```

---

## 🐛 Rozwiązywanie Problemów

### **BME280 nie działa:**
- Sprawdź adres I2C (0x76 lub 0x77)
- Kod automatycznie sprawdza oba adresy
- Jeśli dalej nie działa → moduł może być 3.3V only → podłącz do 3.3V

### **Pompa nie działa:**
- Sprawdź połączenie OUT1+ / OUT1-
- Sprawdź polaryzację pompy
- LED na module PWM powinien świecić gdy aktywna

### **LED przepalony:**
- Czy rezystor 2.2Ω 5W jest podłączony?
- Sprawdź polaryzację LED (+/-)
- Użyj multimetru - sprawdź napięcie na LED (~3.2V)

### **Serial Monitor pokazuje śmieci:**
- Ustaw baud rate na 9600
- Sprawdź port COM
- Sprawdź czy wybrałeś "ATmega328P"

---

## 📱 Połączenie z GUI Python

### **1. Zainstaluj Python + biblioteki**
```bash
pip install pyserial tkinter
```

### **2. Uruchom GUI**
```bash
python GUI/app.py
```

### **3. Połącz z Arduino**
- Port: COM3 (lub twój port)
- Baud: 9600
- Kliknij "Połącz UART"

### **4. Gotowe!**
- GUI automatycznie synchronizuje czas
- Widoczne są wszystkie dane
- Możesz sterować pompą i LED
- Tryb AUTO/MANUAL działa

---

## 📚 Pliki Projektu

| Plik | Opis |
|------|------|
| `sketch_gui_sync.ino` | Kod Arduino (główny) |
| `SCHEMAT_POLACZEN.md` | Pełny schemat elektryczny |
| `QUICK_START.md` | Ten plik |
| `GUI/app.py` | Aplikacja Python |

---

## 💡 Wskazówki

1. **Radiator dla LED:**
   - LED 3W generuje ~1.2W ciepła
   - Radiator aluminiowy 20x20mm wystarczy
   - Pasta termoprzewodząca obowiązkowa

2. **Kalibracja czujników:**
   - Sucha ziemia: ~0-20%
   - Mokra ziemia: ~60-80%
   - W wodzie: ~95-100%

3. **Automatyka:**
   - Pompa włącza się gdy gleba < 40%
   - LED włącza się gdy światło < 35%
   - Pompa wyłącza się gdy woda < 2% (zabezpieczenie)

4. **Zasilanie:**
   - Arduino: USB podczas testów
   - Produkcja: Zasilacz 7-12V DC do VIN Arduino
   - Pompa + LED: Zawsze osobny zasilacz 5V 2A!

---

**Powodzenia! 🌱**

Jeśli masz problemy → sprawdź `SCHEMAT_POLACZEN.md` (pełna dokumentacja)
