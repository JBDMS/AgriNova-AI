#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define SOIL_PIN 34
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define DS18B20_PIN 25

DHT dht(DHT_PIN, DHT_TYPE);
BH1750 luxSensor;
OneWire oneWire(DS18B20_PIN);
DallasTemperature soilTemp(&oneWire);

bool lightReady = false;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);  dht.begin();

  Wire.begin(21, 22);
  lightReady = luxSensor.begin(
    BH1750::CONTINUOUS_HIGH_RES_MODE
  );

  soilTemp.begin();
  delay(1000);

  // Header for Python
  Serial.println(
    "soil_raw,air_temp_c,humidity_pct,light_lux,soil_temp_c"
  );
}

void loop() {
  int moisture = analogRead(SOIL_PIN);
  float airTemp = dht.readTemperature();
  float humidity = dht.readHumidity();

  soilTemp.requestTemperatures();
  float groundTemp = soilTemp.getTempCByIndex(0);

  float light = -1;
  if (lightReady) {
    light = luxSensor.readLightLevel();
  }

  // Output one machine-readable row
  Serial.print(moisture);
  Serial.print(",");

  if (isnan(airTemp)) Serial.print("nan");
  else Serial.print(airTemp, 1);
  Serial.print(",");

  if (isnan(humidity)) Serial.print("nan");
  else Serial.print(humidity, 1);
  Serial.print(",");

  Serial.print(light, 1);
  Serial.print(",");

  if (groundTemp == DEVICE_DISCONNECTED_C) {
    Serial.println("nan");
  } else {
    Serial.println(groundTemp, 2);
  }

  delay(2000);
}