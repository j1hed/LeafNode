#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>

// ===== AJOUT AGENT : WiFi + HTTP pour interroger le backend =====
#include <WiFi.h>
#include <HTTPClient.h>
// ==================================================================

// =====================================================
// LEAFNODE - ESP32 #2
// BLE + DECISION LOCALE + ACTIONNEURS + AGENT DE RECOMMANDATION
//
// Actionneurs :
// 1. Pompe immergée
// 2. Peltier
// 3. Ventilateur
//
// ESP32 #2 garde sa logique de décision locale par seuils EXACTEMENT
// comme avant (sécurité autonome, fonctionne même si le WiFi ou le
// backend FastAPI est injoignable). En plus de ça, ESP32 #2 interroge
// maintenant périodiquement le backend (agent de recommandation
// FarmWise) pour savoir si une action a été approuvée par
// l'utilisateur. Une commande reçue du backend agit comme une
// SURCHARGE TEMPORAIRE sur l'actionneur concerné, pendant la durée
// indiquée (duration_minutes) ; après quoi, la décision locale par
// seuils reprend la main automatiquement. La sécurité (safetyCheck,
// perte de données BLE) reste toujours prioritaire et annule toute
// surcharge en cours.
// =====================================================


// =====================================================
// BLE UUID
// IDENTIQUES A ESP32 #1
// =====================================================

#define SERVICE_UUID \
  "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"

#define CHARACTERISTIC_UUID_TX \
  "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


// =====================================================
// GPIO ACTIONNEURS
// =====================================================

// Pompe immergée
#define PUMP_PIN 26

// Peltier
#define PELTIER_PIN 25

// Ventilateur
#define FAN_PIN 33


// =====================================================
// RELAIS
// =====================================================
//
// Pour un relais ACTIVE LOW :
//
// LOW  = ON
// HIGH = OFF
//
// Si ton relais est ACTIVE HIGH,
// inverse ces deux valeurs.
// =====================================================

#define ACTUATOR_ON  LOW
#define ACTUATOR_OFF HIGH


// ===== AJOUT AGENT : WiFi + backend FastAPI =====
// Mêmes identifiants / même réseau que ESP32 #1 (elles doivent être
// sur le même LAN/hotspot pour que 172.20.10.6 soit joignable).
// =====================================================

#include "leafnode_esp32_actuators_secrets.h"

const char* PC_IP =
  "172.20.10.6";

const int PC_PORT =
  8000;

String API_URL_COMMANDS_PENDING;
String API_URL_COMMANDS_ACK_PREFIX;

const unsigned long COMMAND_POLL_INTERVAL =
  3000;

unsigned long previousCommandPollTime =
  0;

// ==================================================================


// =====================================================
// SEUILS DE DECISION
// =====================================================

// Sol trop sec
const int SOIL_DRY_THRESHOLD = 30;

// Température élevée
const float HIGH_TEMP_THRESHOLD = 30.0;

// Température très élevée
const float VERY_HIGH_TEMP_THRESHOLD = 35.0;


// =====================================================
// DONNEES RECUES
// =====================================================

float temperature = 0.0;
float humidity = 0.0;
float pressure = 0.0;
float gasResistance = 0.0;

int lightPercent = 0;
int soilPercent = 0;

float ph = 7.0;


// ===== AJOUT AGENT : ETAT DE SURCHARGE PAR ACTIONNEUR =====
// Quand une commande arrive du backend, elle force l'état de
// l'actionneur jusqu'à overrideUntil (millis()), pendant ce temps
// makeDecision() n'y touche plus pour ce device. Duration_minutes
// absente ou nulle => pas d'expiration automatique tant qu'aucune
// autre commande n'arrive (overrideUntil = 0 = indéfini, mais
// safetyCheck() l'annule toujours si les données BLE s'arrêtent).
// =====================================================

bool pumpOverrideActive = false;
unsigned long pumpOverrideUntil = 0;

bool peltierOverrideActive = false;
unsigned long peltierOverrideUntil = 0;

bool fanOverrideActive = false;
unsigned long fanOverrideUntil = 0;

// ==================================================================


// =====================================================
// BLE
// =====================================================

BLEAdvertisedDevice* sensorDevice = nullptr;

BLEClient* client = nullptr;

BLERemoteCharacteristic* txCharacteristic = nullptr;

bool deviceConnected = false;


// =====================================================
// BUFFER DE RECEPTION
// =====================================================
//
// ESP32 #1 envoie :
//
// temperature,humidity,pressure,gas,light,soil,ph\n
//
// Exemple :
//
// 25.40,60.20,1012.30,15.20,45,28,7.00
// =====================================================

String receivedBuffer = "";


// =====================================================
// SECURITE
// =====================================================

unsigned long lastDataTime = 0;

const unsigned long SENSOR_TIMEOUT = 10000;


// =====================================================
// CALLBACK BLE
// =====================================================

void notificationCallback(
  BLERemoteCharacteristic* characteristic,
  uint8_t* data,
  size_t length,
  bool isNotify
)
{
  for (
    size_t i = 0;
    i < length;
    i++
  )
  {
    char c = (char)data[i];

    receivedBuffer += c;


    // Fin de trame
    if (c == '\n')
    {
      Serial.println();
      Serial.println(
        "========== NOUVELLE TRAME =========="
      );

      Serial.print(
        receivedBuffer
      );


      // Parser les données
      parseSensorData(
        receivedBuffer
      );


      // Vider le buffer
      receivedBuffer = "";
    }
  }
}


// =====================================================
// DETECTION ESP32 #1
// =====================================================

class MyAdvertisedDeviceCallbacks :
  public BLEAdvertisedDeviceCallbacks
{
  void onResult(
    BLEAdvertisedDevice advertisedDevice
  )
  {
    if (
      advertisedDevice.haveServiceUUID() &&
      advertisedDevice.isAdvertisingService(
        BLEUUID(SERVICE_UUID)
      )
    )
    {
      Serial.println();
      Serial.println(
        "ESP32 #1 DETECTE"
      );


      sensorDevice =
        new BLEAdvertisedDevice(
          advertisedDevice
        );


      BLEDevice::getScan()->stop();
    }
  }
};


// =====================================================
// SCAN BLE
// =====================================================

void scanForSensor()
{
  Serial.println();
  Serial.println(
    "Recherche de ESP32 #1..."
  );


  BLEScan* scan =
    BLEDevice::getScan();


  scan->setAdvertisedDeviceCallbacks(
    new MyAdvertisedDeviceCallbacks()
  );


  scan->setActiveScan(
    true
  );


  scan->start(
    5,
    false
  );
}


// =====================================================
// CONNEXION BLE
// =====================================================

bool connectToSensorESP32()
{
  if (
    sensorDevice == nullptr
  )
  {
    return false;
  }


  Serial.println();
  Serial.println(
    "Connexion a ESP32 #1..."
  );


  client =
    BLEDevice::createClient();


  if (
    !client->connect(
      sensorDevice
    )
  )
  {
    Serial.println(
      "ERREUR : connexion BLE"
    );

    return false;
  }


  Serial.println(
    "BLE CONNECTE"
  );


  // ---------------------------------------------------
  // SERVICE
  // ---------------------------------------------------

  BLERemoteService* remoteService =
    client->getService(
      BLEUUID(SERVICE_UUID)
    );


  if (
    remoteService == nullptr
  )
  {
    Serial.println(
      "Service BLE introuvable"
    );

    client->disconnect();

    return false;
  }


  // ---------------------------------------------------
  // CHARACTERISTIC
  // ---------------------------------------------------

  txCharacteristic =
    remoteService->getCharacteristic(
      BLEUUID(CHARACTERISTIC_UUID_TX)
    );


  if (
    txCharacteristic == nullptr
  )
  {
    Serial.println(
      "Characteristic BLE introuvable"
    );

    client->disconnect();

    return false;
  }


  // ---------------------------------------------------
  // NOTIFICATION
  // ---------------------------------------------------

  if (
    txCharacteristic->canNotify()
  )
  {
    txCharacteristic->registerForNotify(
      notificationCallback
    );
  }


  deviceConnected = true;


  Serial.println(
    "ESP32 #1 CONNECTE AVEC SUCCES"
  );


  return true;
}


// =====================================================
// PARSING DES DONNEES
// =====================================================

void parseSensorData(
  String data
)
{
  data.trim();


  if (
    data.length() == 0
  )
  {
    return;
  }


  // ---------------------------------------------------
  // Recherche des virgules
  // ---------------------------------------------------

  int index1 =
    data.indexOf(',');

  int index2 =
    data.indexOf(
      ',',
      index1 + 1
    );

  int index3 =
    data.indexOf(
      ',',
      index2 + 1
    );

  int index4 =
    data.indexOf(
      ',',
      index3 + 1
    );

  int index5 =
    data.indexOf(
      ',',
      index4 + 1
    );

  int index6 =
    data.indexOf(
      ',',
      index5 + 1
    );


  // ---------------------------------------------------
  // Vérification
  // ---------------------------------------------------

  if (
    index1 < 0 ||
    index2 < 0 ||
    index3 < 0 ||
    index4 < 0 ||
    index5 < 0 ||
    index6 < 0
  )
  {
    Serial.println(
      "ERREUR : trame invalide"
    );

    return;
  }


  // ---------------------------------------------------
  // Extraction
  // ---------------------------------------------------

  temperature =
    data.substring(
      0,
      index1
    ).toFloat();


  humidity =
    data.substring(
      index1 + 1,
      index2
    ).toFloat();


  pressure =
    data.substring(
      index2 + 1,
      index3
    ).toFloat();


  gasResistance =
    data.substring(
      index3 + 1,
      index4
    ).toFloat();


  lightPercent =
    data.substring(
      index4 + 1,
      index5
    ).toInt();


  soilPercent =
    data.substring(
      index5 + 1,
      index6
    ).toInt();


  ph =
    data.substring(
      index6 + 1
    ).toFloat();


  // ---------------------------------------------------
  // Mise à jour du timeout
  // ---------------------------------------------------

  lastDataTime =
    millis();


  // ---------------------------------------------------
  // Affichage
  // ---------------------------------------------------

  printSensorData();


  // ---------------------------------------------------
  // DECISION
  // ---------------------------------------------------

  makeDecision();
}


// =====================================================
// AFFICHAGE
// =====================================================

void printSensorData()
{
  Serial.println();
  Serial.println(
    "--------------------------------"
  );

  Serial.println(
    "DONNEES RECUES PAR ESP32 #2"
  );

  Serial.println(
    "--------------------------------"
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
    "Humidite : "
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
    lightPercent
  );

  Serial.println(
    " %"
  );


  Serial.print(
    "Humidite du sol : "
  );

  Serial.print(
    soilPercent
  );

  Serial.println(
    " %"
  );


  Serial.print(
    "pH : "
  );

  Serial.println(
    ph,
    2
  );
}


// =====================================================
// DECISION
// =====================================================

void makeDecision()
{
  Serial.println();
  Serial.println(
    "========== DECISION =========="
  );

  // ===== AJOUT AGENT : purge des surcharges expirées d'abord =====
  expireOverrides();
  // ==================================================================


  // ===================================================
  // IRRIGATION
  // ===================================================

  // ===== AJOUT AGENT : si le backend a une commande active sur la
  // pompe, on ne touche pas à son état ici =====
  if (pumpOverrideActive)
  {
    Serial.println(
      "Pompe : sous controle de l'agent (surcharge active)"
    );
  }
  else if (
    soilPercent <
    SOIL_DRY_THRESHOLD
  )
  {
    Serial.println(
      "Sol sec -> DEMARRAGE POMPE"
    );


    startPump();
  }

  else
  {
    Serial.println(
      "Sol suffisamment humide -> ARRET POMPE"
    );


    stopPump();
  }


  // ===================================================
  // REFROIDISSEMENT
  // ===================================================

  // ===== AJOUT AGENT : si le backend a une commande active sur le
  // peltier ET/OU le ventilateur, on saute la logique par seuils
  // pour le(s) device(s) concerné(s) =====
  if (peltierOverrideActive && fanOverrideActive)
  {
    Serial.println(
      "Peltier + ventilateur : sous controle de l'agent (surcharge active)"
    );
  }
  else if (
    temperature >=
    VERY_HIGH_TEMP_THRESHOLD
  )
  {
    Serial.println(
      "Temperature tres elevee"
    );

    Serial.println(
      "Peltier + ventilateur -> ON"
    );


    if (!peltierOverrideActive) startPeltier();

    if (!fanOverrideActive) startFan();
  }


  else if (
    temperature >=
    HIGH_TEMP_THRESHOLD
  )
  {
    Serial.println(
      "Temperature elevee"
    );

    Serial.println(
      "Ventilateur -> ON"
    );


    if (!peltierOverrideActive) stopPeltier();

    if (!fanOverrideActive) startFan();
  }


  else
  {
    Serial.println(
      "Temperature normale"
    );


    if (!peltierOverrideActive) stopPeltier();

    if (!fanOverrideActive) stopFan();
  }
}


// =====================================================
// POMPE
// =====================================================

void startPump()
{
  digitalWrite(
    PUMP_PIN,
    ACTUATOR_ON
  );


  Serial.println(
    "POMPE : ON"
  );
}


void stopPump()
{
  digitalWrite(
    PUMP_PIN,
    ACTUATOR_OFF
  );


  Serial.println(
    "POMPE : OFF"
  );
}


// =====================================================
// PELTIER
// =====================================================

void startPeltier()
{
  digitalWrite(
    PELTIER_PIN,
    ACTUATOR_ON
  );


  Serial.println(
    "PELTIER : ON"
  );
}


void stopPeltier()
{
  digitalWrite(
    PELTIER_PIN,
    ACTUATOR_OFF
  );


  Serial.println(
    "PELTIER : OFF"
  );
}


// =====================================================
// VENTILATEUR
// =====================================================

void startFan()
{
  digitalWrite(
    FAN_PIN,
    ACTUATOR_ON
  );


  Serial.println(
    "VENTILATEUR : ON"
  );
}


void stopFan()
{
  digitalWrite(
    FAN_PIN,
    ACTUATOR_OFF
  );


  Serial.println(
    "VENTILATEUR : OFF"
  );
}


// ===== AJOUT AGENT : WiFi =====
// Meme logique que ESP32 #1 (connectWiFi / checkWiFi)
// =====================================================

void connectWiFi()
{
  Serial.println();
  Serial.println(
    "Connexion WiFi (ESP32 #2)..."
  );

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - start < 20000
  )
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("WiFi CONNECTE (ESP32 #2)");
    Serial.print("IP ESP32 #2 : ");
    Serial.println(WiFi.localIP());

    API_URL_COMMANDS_PENDING =
      String("http://") + PC_IP + ":" + PC_PORT + "/api/commands/pending";

    API_URL_COMMANDS_ACK_PREFIX =
      String("http://") + PC_IP + ":" + PC_PORT + "/api/commands/";

    Serial.print("Commands endpoint : ");
    Serial.println(API_URL_COMMANDS_PENDING);
  }
  else
  {
    Serial.println("ERREUR connexion WiFi (ESP32 #2)");
    Serial.println("L'agent sera indisponible, la decision locale par seuils continue normalement.");
  }
}


void checkWiFi()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
}


// ===== AJOUT AGENT : commandes du backend (pompe/peltier/ventilateur) =====
// GET  /api/commands/pending  -> liste des commandes en attente
// POST /api/commands/{id}/ack -> confirme l'execution
// Une commande recue applique une SURCHARGE TEMPORAIRE sur
// makeDecision() pour ce device, voir expireOverrides().
// =====================================================

void applyOverride(
  String device,
  String action,
  float durationMinutes
)
{
  bool turnOn = (action == "ON");

  unsigned long until =
    (durationMinutes > 0)
      ? millis() + (unsigned long)(durationMinutes * 60000UL)
      : 0; // 0 = pas d'expiration automatique (jusqu'a la prochaine commande ou perte de securite)

  if (device == "pump")
  {
    turnOn ? startPump() : stopPump();
    pumpOverrideActive = true;
    pumpOverrideUntil = until;
  }
  else if (device == "peltier")
  {
    turnOn ? startPeltier() : stopPeltier();
    peltierOverrideActive = true;
    peltierOverrideUntil = until;
  }
  else if (device == "fan")
  {
    turnOn ? startFan() : stopFan();
    fanOverrideActive = true;
    fanOverrideUntil = until;
  }
  else
  {
    Serial.print("Commande agent : device inconnu ignore -> ");
    Serial.println(device);
  }
}


void expireOverrides()
{
  unsigned long now = millis();

  if (pumpOverrideActive && pumpOverrideUntil != 0 && now >= pumpOverrideUntil)
  {
    pumpOverrideActive = false;
    Serial.println("Surcharge agent expiree : pompe -> retour au controle local");
  }

  if (peltierOverrideActive && peltierOverrideUntil != 0 && now >= peltierOverrideUntil)
  {
    peltierOverrideActive = false;
    Serial.println("Surcharge agent expiree : peltier -> retour au controle local");
  }

  if (fanOverrideActive && fanOverrideUntil != 0 && now >= fanOverrideUntil)
  {
    fanOverrideActive = false;
    Serial.println("Surcharge agent expiree : ventilateur -> retour au controle local");
  }
}


void ackCommand(int commandId, bool success)
{
  HTTPClient http;

  String url = API_URL_COMMANDS_ACK_PREFIX + String(commandId) + "/ack";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String body = success
    ? "{\"success\": true}"
    : "{\"success\": false}";

  int code = http.POST(body);

  if (code != 200)
  {
    Serial.print("Ack commande #");
    Serial.print(commandId);
    Serial.print(" -> HTTP ");
    Serial.println(code);
  }

  http.end();
}


void pollCommands()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    return;
  }

  if (API_URL_COMMANDS_PENDING.length() == 0)
  {
    return; // WiFi jamais connecte -> URL jamais construite
  }

  HTTPClient http;
  http.begin(API_URL_COMMANDS_PENDING);
  int code = http.GET();

  if (code != 200)
  {
    if (code > 0)
    {
      Serial.print("Poll commandes -> HTTP ");
      Serial.println(code);
    }
    http.end();
    return;
  }

  String payload = http.getString();
  http.end();

  // Parsing JSON minimal, sans dependance externe (ArduinoJson non
  // requis ici) : on cherche chaque commande "id", "device",
  // "action", "duration_minutes" par recherche de sous-chaines.
  // Pour un parsing plus robuste avec plusieurs commandes d'un coup,
  // installer ArduinoJson et remplacer cette fonction - voir
  // esp32/leafnode_esp32_sensors.ino pour un exemple d'utilisation
  // similaire cote ESP32 #1 si vous l'ajoutez la-bas aussi.

  int searchPos = 0;

  while (true)
  {
    int idPos = payload.indexOf("\"id\":", searchPos);
    if (idPos < 0) break;

    int idStart = idPos + 5;
    int idEnd = payload.indexOf(",", idStart);
    int commandId = payload.substring(idStart, idEnd).toInt();

    int devicePos = payload.indexOf("\"device\":\"", idEnd);
    int deviceStart = devicePos + 10;
    int deviceEnd = payload.indexOf("\"", deviceStart);
    String device = payload.substring(deviceStart, deviceEnd);

    int actionPos = payload.indexOf("\"action\":\"", deviceEnd);
    int actionStart = actionPos + 10;
    int actionEnd = payload.indexOf("\"", actionStart);
    String action = payload.substring(actionStart, actionEnd);

    float durationMinutes = 0;
    int durPos = payload.indexOf("\"duration_minutes\":", actionEnd);
    if (durPos >= 0)
    {
      int durStart = durPos + 19;
      int durEnd = payload.indexOf(",", durStart);
      int durEndBrace = payload.indexOf("}", durStart);
      if (durEndBrace >= 0 && (durEnd < 0 || durEndBrace < durEnd)) durEnd = durEndBrace;

      String durStr = payload.substring(durStart, durEnd);
      durStr.trim();
      if (durStr != "null")
      {
        durationMinutes = durStr.toFloat();
      }
    }

    Serial.println();
    Serial.print("Commande agent recue #");
    Serial.print(commandId);
    Serial.print(" : ");
    Serial.print(device);
    Serial.print(" -> ");
    Serial.print(action);
    Serial.print(" (");
    Serial.print(durationMinutes);
    Serial.println(" min)");

    applyOverride(device, action, durationMinutes);
    ackCommand(commandId, true);

    searchPos = idEnd;
  }
}

// ==================================================================


// =====================================================
// SECURITE
// =====================================================
//
// Si aucune donnée n'arrive depuis ESP32 #1,
// on arrête les actionneurs.
// =====================================================

void safetyCheck()
{
  if (
    lastDataTime == 0
  )
  {
    return;
  }


  if (
    millis() - lastDataTime >
    SENSOR_TIMEOUT
  )
  {
    Serial.println();
    Serial.println(
      "!!! SECURITE !!!"
    );

    Serial.println(
      "Aucune donnee recue depuis ESP32 #1"
    );

    Serial.println(
      "Arret des actionneurs"
    );


    stopPump();

    stopPeltier();

    stopFan();

    // ===== AJOUT AGENT : la securite annule toute surcharge en cours =====
    pumpOverrideActive = false;
    peltierOverrideActive = false;
    fanOverrideActive = false;
    // ==================================================================


    lastDataTime =
      millis();
  }
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
    "===================================="
  );

  Serial.println(
    "       LEAFNODE - ESP32 #2"
  );

  Serial.println(
    " BLE + POMPE + PELTIER + VENTILATEUR"
  );

  Serial.println(
    "===================================="
  );


  // ===================================================
  // GPIO
  // ===================================================

  pinMode(
    PUMP_PIN,
    OUTPUT
  );


  pinMode(
    PELTIER_PIN,
    OUTPUT
  );


  pinMode(
    FAN_PIN,
    OUTPUT
  );


  // ===================================================
  // SECURITE AU DEMARRAGE
  // ===================================================

  stopPump();

  stopPeltier();

  stopFan();


  // ===================================================
  // INITIALISATION BLE
  // ===================================================

  BLEDevice::init(
    "LeafNode-Actuators"
  );


  Serial.println(
    "BLE initialise"
  );


  // ===== AJOUT AGENT : WiFi (independant du BLE, pour parler au backend) =====
  connectWiFi();
  // ==================================================================


  // ===================================================
  // SCAN
  // ===================================================

  scanForSensor();


  // ===================================================
  // CONNEXION
  // ===================================================

  if (
    sensorDevice != nullptr
  )
  {
    connectToSensorESP32();
  }


  Serial.println();
  Serial.println(
    "ESP32 #2 PRET"
  );
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
  // ---------------------------------------------------
  // Reconnexion BLE
  // ---------------------------------------------------

  if (
    !deviceConnected
  )
  {
    static unsigned long lastScan =
      0;


    if (
      millis() - lastScan >
      5000
    )
    {
      lastScan =
        millis();


      scanForSensor();


      if (
        sensorDevice != nullptr
      )
      {
        connectToSensorESP32();
      }
    }
  }


  // ---------------------------------------------------
  // Sécurité
  // ---------------------------------------------------

  safetyCheck();


  // ===== AJOUT AGENT : WiFi + poll des commandes du backend =====
  checkWiFi();

  if (
    millis() - previousCommandPollTime >=
    COMMAND_POLL_INTERVAL
  )
  {
    previousCommandPollTime = millis();
    pollCommands();
  }
  // ==================================================================


  delay(
    10
  );
}