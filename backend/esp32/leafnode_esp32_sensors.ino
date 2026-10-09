#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>

#include <WiFi.h>
#include <HTTPClient.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// =====================================================
// LEAFNODE - ESP32 #1
// CAPTEURS + BLE + FASTAPI
// =====================================================


// =====================================================
// WIFI / FASTAPI
// =====================================================

#include "leafnode_esp32_sensors_secrets.h"

const char* FASTAPI_URL =
  "http://172.20.10.6:8000/api/sensors";


// =====================================================
// BME680
// =====================================================

#define SDA_PIN 21
#define SCL_PIN 22

Adafruit_BME680 bme;

bool bmeAvailable = false;


// =====================================================
// LDR
// =====================================================

#define LDR_ANALOG_PIN 34
#define LDR_DIGITAL_PIN 25


// =====================================================
// SOIL
// =====================================================

#define SOIL_PIN 35


// =====================================================
// PH SIMULE
// =====================================================

const float PH_VALUE = 7.0;


// =====================================================
// CALIBRATION
// A adapter plus tard
// =====================================================

const int SOIL_RAW_DRY = 3300;
const int SOIL_RAW_WET = 1300;

const int LDR_RAW_DARK = 3500;
const int LDR_RAW_BRIGHT = 300;


// =====================================================
// BLE UUID
// Les memes UUID doivent etre sur ESP32 #2
// =====================================================

#define SERVICE_UUID \
  "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"

#define CHARACTERISTIC_UUID_TX \
  "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


// =====================================================
// BLE
// =====================================================

BLECharacteristic* txCharacteristic;

bool deviceConnected = false;


// =====================================================
// DONNEES CAPTEURS
// =====================================================

float temperature = 0.0;
float humidity = 0.0;
float pressure = 0.0;
float gasResistance = 0.0;

int lightPercentValue = 0;
int soilPercentValue = 0;


// =====================================================
// TIMING
// =====================================================

unsigned long previousSensorTime = 0;

const unsigned long SENSOR_INTERVAL =
  3000;


// =====================================================
// BLE CALLBACK
// =====================================================

class ServerCallbacks : public BLEServerCallbacks
{
  void onConnect(BLEServer* server)
  {
    deviceConnected = true;

    Serial.println();
    Serial.println(
      "ESP32 #2 CONNECTE EN BLE"
    );
  }


  void onDisconnect(BLEServer* server)
  {
    deviceConnected = false;

    Serial.println();
    Serial.println(
      "ESP32 #2 DECONNECTE"
    );

    delay(300);

    BLEDevice::startAdvertising();

    Serial.println(
      "Advertising BLE relance"
    );
  }
};


// =====================================================
// LECTURE ANALOGIQUE MOYENNE
// =====================================================

int readAverage(
  uint8_t pin,
  int samples = 10
)
{
  long total = 0;

  for (int i = 0; i < samples; i++)
  {
    total += analogRead(pin);

    delay(3);
  }

  return total / samples;
}


// =====================================================
// CONVERSION SOIL -> %
// =====================================================

int convertSoilToPercent(int raw)
{
  int value = map(
    raw,
    SOIL_RAW_DRY,
    SOIL_RAW_WET,
    0,
    100
  );

  return constrain(
    value,
    0,
    100
  );
}


// =====================================================
// CONVERSION LDR -> %
// =====================================================

int convertLightToPercent(int raw)
{
  int value = map(
    raw,
    LDR_RAW_DARK,
    LDR_RAW_BRIGHT,
    0,
    100
  );

  return constrain(
    value,
    0,
    100
  );
}


// =====================================================
// INITIALISATION BME680
// =====================================================

bool initBME()
{
  if (bme.begin(0x76))
  {
    Serial.println(
      "BME680 trouve a 0x76"
    );

    return true;
  }


  if (bme.begin(0x77))
  {
    Serial.println(
      "BME680 trouve a 0x77"
    );

    return true;
  }


  Serial.println(
    "ERREUR : BME680 non detecte"
  );

  return false;
}


// =====================================================
// CONFIGURATION BME680
// =====================================================

void configureBME()
{
  bme.setTemperatureOversampling(
    BME680_OS_8X
  );

  bme.setHumidityOversampling(
    BME680_OS_2X
  );

  bme.setPressureOversampling(
    BME680_OS_4X
  );

  bme.setIIRFilterSize(
    BME680_FILTER_SIZE_3
  );

  bme.setGasHeater(
    320,
    150
  );
}


// =====================================================
// CONNEXION WIFI
// =====================================================

void connectWiFi()
{
  Serial.println();
  Serial.println(
    "Connexion WiFi..."
  );

  WiFi.mode(
    WIFI_STA
  );

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );


  unsigned long start =
    millis();


  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - start < 20000
  )
  {
    delay(500);

    Serial.print(".");
  }


  Serial.println();


  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    Serial.println(
      "WiFi CONNECTE"
    );

    Serial.print(
      "IP ESP32 #1 : "
    );

    Serial.println(
      WiFi.localIP()
    );

    Serial.print(
      "FastAPI : "
    );

    Serial.println(
      FASTAPI_URL
    );
  }

  else
  {
    Serial.println(
      "ERREUR connexion WiFi"
    );
  }
}


// =====================================================
// RECONNEXION WIFI
// =====================================================

void checkWiFi()
{
  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    Serial.println(
      "WiFi perdu - reconnexion..."
    );

    WiFi.disconnect();

    WiFi.begin(
      WIFI_SSID,
      WIFI_PASSWORD
    );
  }
}


// =====================================================
// LECTURE CAPTEURS
// =====================================================

void readSensors()
{
  // ==========================
  // BME680
  // ==========================

  if (bmeAvailable)
  {
    if (
      bme.performReading()
    )
    {
      temperature =
        bme.temperature;

      humidity =
        bme.humidity;

      pressure =
        bme.pressure / 100.0;

      gasResistance =
        bme.gas_resistance / 1000.0;
    }

    else
    {
      Serial.println(
        "Erreur lecture BME680"
      );
    }
  }


  // ==========================
  // LDR
  // ==========================

  int ldrRaw =
    readAverage(
      LDR_ANALOG_PIN
    );

  lightPercentValue =
    convertLightToPercent(
      ldrRaw
    );


  // ==========================
  // SOIL
  // ==========================

  int soilRaw =
    readAverage(
      SOIL_PIN
    );

  soilPercentValue =
    convertSoilToPercent(
      soilRaw
    );
}


// =====================================================
// AFFICHAGE
// =====================================================

void printSensorData()
{
  Serial.println();
  Serial.println(
    "=============================="
  );

  Serial.println(
    "LEAFNODE - CAPTEURS"
  );

  Serial.println(
    "=============================="
  );


  Serial.print(
    "Temperature : "
  );

  Serial.print(
    temperature,
    2
  );

  Serial.println(
    " C"
  );


  Serial.print(
    "Humidite air : "
  );

  Serial.print(
    humidity,
    2
  );

  Serial.println(
    " %"
  );


  Serial.print(
    "Pression : "
  );

  Serial.print(
    pressure,
    2
  );

  Serial.println(
    " hPa"
  );


  Serial.print(
    "Gaz : "
  );

  Serial.print(
    gasResistance,
    2
  );

  Serial.println(
    " kOhm"
  );


  Serial.print(
    "Luminosite : "
  );

  Serial.print(
    lightPercentValue
  );

  Serial.println(
    " %"
  );


  Serial.print(
    "Humidite sol : "
  );

  Serial.print(
    soilPercentValue
  );

  Serial.println(
    " %"
  );


  Serial.print(
    "pH : "
  );

  Serial.println(
    PH_VALUE,
    2
  );
}


// =====================================================
// BLE
// Envoi fragmente + \n
// =====================================================

void sendBLE()
{
  char fullFrame[120];


  snprintf(
    fullFrame,
    sizeof(fullFrame),

    "%.2f,%.2f,%.2f,%.2f,%d,%d,%.2f\n",

    temperature,
    humidity,
    pressure,
    gasResistance,
    lightPercentValue,
    soilPercentValue,
    PH_VALUE
  );


  Serial.println();
  Serial.print(
    "BLE TX : "
  );

  Serial.print(
    fullFrame
  );


  if (!deviceConnected)
  {
    Serial.println(
      "ESP32 #2 non connecte"
    );

    return;
  }


  String message =
    String(fullFrame);


  // Petits paquets pour eviter
  // les problemes de MTU BLE
  const int PACKET_SIZE = 18;


  for (
    int i = 0;
    i < message.length();
    i += PACKET_SIZE
  )
  {
    String packet =
      message.substring(
        i,
        min(
          i + PACKET_SIZE,
          (int)message.length()
        )
      );


    txCharacteristic->setValue(
      packet.c_str()
    );


    txCharacteristic->notify();


    delay(30);
  }
}


// =====================================================
// ENVOI FASTAPI
// =====================================================

void sendToFastAPI()
{
  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    Serial.println(
      "FASTAPI : WiFi non connecte"
    );

    return;
  }


  HTTPClient http;


  http.setTimeout(
    5000
  );


  http.begin(
    FASTAPI_URL
  );


  http.addHeader(
    "Content-Type",
    "application/json"
  );


  // ==========================
  // JSON
  // ==========================

  String json = "{";


  json +=
    "\"temperature\":" +
    String(
      temperature,
      2
    );


  json +=
    ",\"humidity\":" +
    String(
      humidity,
      2
    );


  json +=
    ",\"pressure\":" +
    String(
      pressure,
      2
    );


  json +=
    ",\"gas\":" +
    String(
      gasResistance,
      2
    );


  json +=
    ",\"light\":" +
    String(
      lightPercentValue
    );


  json +=
    ",\"soil\":" +
    String(
      soilPercentValue
    );


  json +=
    ",\"ph\":" +
    String(
      PH_VALUE,
      2
    );


  json += "}";


  Serial.println();
  Serial.println(
    "===== FASTAPI ====="
  );

  Serial.println(
    json
  );


  // ==========================
  // POST
  // ==========================

  int httpCode =
    http.POST(
      json
    );


  Serial.print(
    "HTTP CODE : "
  );

  Serial.println(
    httpCode
  );


  if (httpCode > 0)
  {
    String response =
      http.getString();


    Serial.print(
      "Reponse : "
    );

    Serial.println(
      response
    );
  }

  else
  {
    Serial.print(
      "Erreur HTTP : "
    );

    Serial.println(
      http.errorToString(
        httpCode
      )
    );
  }


  http.end();
}


// =====================================================
// INITIALISATION BLE
// =====================================================

void initBLE()
{
  BLEDevice::init(
    "LeafNode-Sensors"
  );


  BLEServer* server =
    BLEDevice::createServer();


  server->setCallbacks(
    new ServerCallbacks()
  );


  BLEService* service =
    server->createService(
      SERVICE_UUID
    );


  txCharacteristic =
    service->createCharacteristic(
      CHARACTERISTIC_UUID_TX,

      BLECharacteristic::PROPERTY_READ |
      BLECharacteristic::PROPERTY_NOTIFY
    );


  txCharacteristic->addDescriptor(
    new BLE2902()
  );


  service->start();


  BLEAdvertising* advertising =
    BLEDevice::getAdvertising();


  advertising->addServiceUUID(
    SERVICE_UUID
  );


  advertising->setScanResponse(
    true
  );


  BLEDevice::startAdvertising();


  Serial.println();
  Serial.println(
    "BLE ACTIVE"
  );

  Serial.println(
    "Nom : LeafNode-Sensors"
  );
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
  Serial.begin(
    115200
  );


  delay(
    1000
  );


  Serial.println();
  Serial.println(
    "================================"
  );

  Serial.println(
    "LEAFNODE ESP32 #1"
  );

  Serial.println(
    "BLE + WiFi + FastAPI"
  );

  Serial.println(
    "================================"
  );


  // ==========================
  // ADC
  // ==========================

  analogReadResolution(
    12
  );


  pinMode(
    LDR_ANALOG_PIN,
    INPUT
  );


  pinMode(
    LDR_DIGITAL_PIN,
    INPUT
  );


  pinMode(
    SOIL_PIN,
    INPUT
  );


  // ==========================
  // I2C
  // ==========================

  Wire.begin(
    SDA_PIN,
    SCL_PIN
  );


  // ==========================
  // BME680
  // ==========================

  bmeAvailable =
    initBME();


  if (bmeAvailable)
  {
    configureBME();
  }


  // ==========================
  // WIFI
  // ==========================

  connectWiFi();


  // ==========================
  // BLE
  // ==========================

  initBLE();


  Serial.println();
  Serial.println(
    "SYSTEME PRET"
  );
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  checkWiFi();


  if (
    millis() - previousSensorTime
    >= SENSOR_INTERVAL
  )
  {
    previousSensorTime =
      millis();


    // 1. Lire capteurs
    readSensors();


    // 2. Afficher
    printSensorData();


    // 3. ESP32 #1 -> ESP32 #2
    sendBLE();


    // 4. ESP32 #1 -> FastAPI
    sendToFastAPI();
  }


  delay(
    10
  );
}