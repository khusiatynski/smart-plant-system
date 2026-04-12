/*
 * Smart Plant System - Wokwi
 * Z biblioteką Adafruit BME280
 */

#include <Wire.h>
#include <Adafruit_BME280.h>

#define PIN_SOIL     A0
#define PIN_WATER    A1
#define PIN_LIGHT    A2
#define PIN_PUMP     3
#define PIN_LED      5

#define SOIL_MIN     40.0
#define LIGHT_MIN    35.0
#define WATER_MIN    5.0

Adafruit_BME280 bme; // I2C

float soilMoisture, waterLevel, lightLevel;
float temperature, humidity, pressure;
bool pumpOn = false, ledOn = false, autoMode = true;
bool bme280_ok = false;

void setup() {
  Serial.begin(9600);
  Serial.println("Smart Plant System");
  
  pinMode(PIN_PUMP, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_PUMP, LOW);
  digitalWrite(PIN_LED, LOW);
  
  // Inicjalizacja BME280
  if (!bme.begin(0x76)) {
    Serial.println("BME280 not found at 0x76!");
    if (!bme.begin(0x77)) {
      Serial.println("BME280 not found at 0x77!");
      Serial.println("Using default values");
    } else {
      bme280_ok = true;
      Serial.println("BME280 OK at 0x77");
    }
  } else {
    bme280_ok = true;
    Serial.println("BME280 OK at 0x76");
  }
  
  if (bme280_ok) {
    // Konfiguracja
    bme.setSampling(Adafruit_BME280::MODE_NORMAL,
                    Adafruit_BME280::SAMPLING_X2,  // temperature
                    Adafruit_BME280::SAMPLING_X16, // pressure
                    Adafruit_BME280::SAMPLING_X1,  // humidity
                    Adafruit_BME280::FILTER_X16,
                    Adafruit_BME280::STANDBY_MS_0_5);
  }
  
  Serial.println("System Ready");
}

void loop() {
  readSensors();
  readBME280();
  
  if (autoMode) {
    pumpOn = (soilMoisture < SOIL_MIN && waterLevel > WATER_MIN);
    ledOn = (lightLevel < LIGHT_MIN);
    if (waterLevel <= 2.0) pumpOn = false;
  }
  
  digitalWrite(PIN_PUMP, pumpOn ? HIGH : LOW);
  analogWrite(PIN_LED, ledOn ? 255 : 0);
  
  sendData();
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
    pressure = bme.readPressure() / 100.0F; // Pa → hPa
    
    // Sprawdź błędy
    if (isnan(temperature)) temperature = 22.0;
    if (isnan(humidity)) humidity = 50.0;
    if (isnan(pressure)) pressure = 1013.25;
  } else {
    // Wartości domyślne
    temperature = 22.0;
    humidity = 50.0;
    pressure = 1013.25;
  }
}

void sendData() {
  Serial.print(millis());
  Serial.print(",");
  Serial.print(soilMoisture, 1);
  Serial.print(",");
  Serial.print(temperature, 1);
  Serial.print(",");
  Serial.print(humidity, 1);
  Serial.print(",");
  Serial.print(lightLevel, 1);
  Serial.print(",");
  Serial.print(waterLevel, 1);
  Serial.print(",");
  Serial.print(pumpOn ? "true" : "false");
  Serial.print(",");
  Serial.println(ledOn ? "true" : "false");
}
