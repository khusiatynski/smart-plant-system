/*
 * Smart Plant System - Pełna synchronizacja z GUI
 * Wysyła: timestamp,soil,temp,humidity,PRESSURE,light,water,pump,led
 * Odbiera: AUTO, MANUAL, PUMP:ON/OFF, LED:ON/OFF, SET_TIME, SET_THRESHOLDS
 */

#include <Wire.h>
#include <Adafruit_BME280.h>

#define PIN_SOIL     A0
#define PIN_WATER    A1
#define PIN_LIGHT    A2
#define PIN_PUMP     3
#define PIN_LED      5

// Domyślne progi (GUI może je zmienić)
float SOIL_MIN = 40.0;
float SOIL_MAX = 60.0;
float LIGHT_MIN = 35.0;
float LIGHT_MAX = 65.0;

Adafruit_BME280 bme;

float soilMoisture, waterLevel, lightLevel;
float temperature, humidity, pressure;
bool pumpOn = false, ledOn = false, autoMode = true;
bool bme280_ok = false;

// Czas systemowy (synchronizowany przez GUI)
unsigned long startMillis = 0;
unsigned long currentYear = 2026;
unsigned long currentMonth = 4;
unsigned long currentDay = 12;
unsigned long currentHour = 0;
unsigned long currentMinute = 0;
unsigned long currentSecond = 0;

void setup() {
  Serial.begin(9600);
  
  pinMode(PIN_PUMP, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_PUMP, LOW);
  digitalWrite(PIN_LED, LOW);
  
  if (bme.begin(0x76) || bme.begin(0x77)) {
    bme280_ok = true;
    bme.setSampling(Adafruit_BME280::MODE_NORMAL,
                    Adafruit_BME280::SAMPLING_X2,
                    Adafruit_BME280::SAMPLING_X16,
                    Adafruit_BME280::SAMPLING_X1,
                    Adafruit_BME280::FILTER_X16,
                    Adafruit_BME280::STANDBY_MS_0_5);
  }
  
  startMillis = millis();
  Serial.println("Smart Plant System Ready");
}

void loop() {
  readSensors();
  readBME280();
  processCommands();
  
  if (autoMode) {
    // Automatyka zgodna z GUI
    if (soilMoisture < SOIL_MIN && waterLevel > 5.0) {
      pumpOn = true;
    } else if (soilMoisture >= SOIL_MAX) {
      pumpOn = false;
    }
    
    if (lightLevel < LIGHT_MIN) {
      ledOn = true;
    } else if (lightLevel >= LIGHT_MAX) {
      ledOn = false;
    }
    
    // Zabezpieczenie
    if (waterLevel <= 2.0) {
      pumpOn = false;
    }
  }
  
  digitalWrite(PIN_PUMP, pumpOn ? HIGH : LOW);
  analogWrite(PIN_LED, ledOn ? 255 : 0);
  
  sendDataToGUI();
  delay(2000);
}

void readSensors() {
  soilMoisture = map(analogRead(PIN_SOIL), 0, 1023, 0, 100);
  waterLevel = map(analogRead(PIN_WATER), 0, 1023, 0, 100);
  lightLevel = map(analogRead(PIN_LIGHT), 0, 1023, 0, 100);
}

void readBME280() {
  if (bme280_ok) {
    temperature = bme.readTemperature();
    humidity = bme.readHumidity();
    pressure = bme.readPressure() / 100.0F; // hPa
    
    if (isnan(temperature)) temperature = 22.0;
    if (isnan(humidity)) humidity = 50.0;
    if (isnan(pressure)) pressure = 1013.25;
  } else {
    temperature = 22.0;
    humidity = 50.0;
    pressure = 1013.25;
  }
}

void processCommands() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    // SET_TIME:2026-04-12 15:30:45
    if (cmd.startsWith("SET_TIME:")) {
      parseTimeCommand(cmd.substring(9));
      Serial.println("OK:TIME_SET");
    }
    // SET_THRESHOLDS:40.0,60.0,35.0,65.0
    else if (cmd.startsWith("SET_THRESHOLDS:")) {
      parseThresholds(cmd.substring(15));
      Serial.println("OK:THRESHOLDS_SET");
    }
    // AUTO
    else if (cmd.equalsIgnoreCase("AUTO")) {
      autoMode = true;
      Serial.println("OK:AUTO_MODE");
    }
    // MANUAL
    else if (cmd.equalsIgnoreCase("MANUAL")) {
      autoMode = false;
      Serial.println("OK:MANUAL_MODE");
    }
    // PUMP:ON
    else if (cmd.equalsIgnoreCase("PUMP:ON")) {
      autoMode = false;
      if (waterLevel > 2.0) {
        pumpOn = true;
        Serial.println("OK:PUMP_ON");
      } else {
        Serial.println("ERROR:LOW_WATER");
      }
    }
    // PUMP:OFF
    else if (cmd.equalsIgnoreCase("PUMP:OFF")) {
      autoMode = false;
      pumpOn = false;
      Serial.println("OK:PUMP_OFF");
    }
    // LED:ON
    else if (cmd.equalsIgnoreCase("LED:ON")) {
      autoMode = false;
      ledOn = true;
      Serial.println("OK:LED_ON");
    }
    // LED:OFF
    else if (cmd.equalsIgnoreCase("LED:OFF")) {
      autoMode = false;
      ledOn = false;
      Serial.println("OK:LED_OFF");
    }
  }
}

void parseTimeCommand(String timeStr) {
  // Format: YYYY-MM-DD HH:MM:SS
  // Przykład: 2026-04-12 15:30:45
  int year, month, day, hour, minute, second;
  if (sscanf(timeStr.c_str(), "%d-%d-%d %d:%d:%d", 
             &year, &month, &day, &hour, &minute, &second) == 6) {
    currentYear = year;
    currentMonth = month;
    currentDay = day;
    currentHour = hour;
    currentMinute = minute;
    currentSecond = second;
    startMillis = millis();
  }
}

void parseThresholds(String data) {
  // Format: soil_min,soil_max,light_min,light_max
  // Przykład: 40.0,60.0,35.0,65.0
  float s_min, s_max, l_min, l_max;
  if (sscanf(data.c_str(), "%f,%f,%f,%f", &s_min, &s_max, &l_min, &l_max) == 4) {
    SOIL_MIN = s_min;
    SOIL_MAX = s_max;
    LIGHT_MIN = l_min;
    LIGHT_MAX = l_max;
  }
}

void sendDataToGUI() {
  // Format zgodny z GUI:
  // timestamp,soilMoisture,temperature,airHumidity,pressure,lightLevel,waterLevel,pumpOn,ledOn
  
  updateSystemTime();
  
  // Timestamp: YYYY-MM-DD HH:MM:SS
  char timestamp[20];
  sprintf(timestamp, "%04lu-%02lu-%02lu %02lu:%02lu:%02lu",
          currentYear, currentMonth, currentDay,
          currentHour, currentMinute, currentSecond);
  
  Serial.print(timestamp);
  Serial.print(",");
  Serial.print(soilMoisture, 1);
  Serial.print(",");
  Serial.print(temperature, 1);
  Serial.print(",");
  Serial.print(humidity, 1);
  Serial.print(",");
  Serial.print(pressure, 1);        // ✅ DODANE!
  Serial.print(",");
  Serial.print(lightLevel, 1);
  Serial.print(",");
  Serial.print(waterLevel, 1);
  Serial.print(",");
  Serial.print(pumpOn ? "true" : "false");
  Serial.print(",");
  Serial.println(ledOn ? "true" : "false");
}

void updateSystemTime() {
  unsigned long elapsed = (millis() - startMillis) / 1000;
  
  currentSecond += elapsed % 60;
  elapsed /= 60;
  
  currentMinute += elapsed % 60;
  elapsed /= 60;
  
  currentHour += elapsed;
  
  while (currentSecond >= 60) {
    currentSecond -= 60;
    currentMinute++;
  }
  
  while (currentMinute >= 60) {
    currentMinute -= 60;
    currentHour++;
  }
  
  while (currentHour >= 24) {
    currentHour -= 24;
    currentDay++;
  }
  
  // Reset licznika
  startMillis = millis();
}
