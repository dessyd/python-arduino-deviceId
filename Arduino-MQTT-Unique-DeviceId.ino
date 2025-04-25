#include "arduino_secrets.h"
#include <WiFiNINA.h>
#include <WiFiUdp.h>
#include <ArduinoECCX08.h>

const char *ssid = SECRET_SSID;
const char *password = SECRET_PASSWORD;
const char *server_ip = SECRET_PROVISIONNING_IP; // Adresse IP du serveur UDP
const int server_port = 5000;

// Paramètres de réessai
const int MAX_RETRIES = 5;
const long RETRY_INTERVAL = 30000;
const int RETRY_TIMEOUT = 2000;
const long WIFI_CHECK_INTERVAL = 5000; // Vérification de la connexion WiFi toutes les 5 secondes

byte deviceID = 0;
char macAddress[18];  // XX:XX:XX:XX:XX:XX\0
char mqttBrokerIP[16] = "";
WiFiUDP udp;
unsigned long lastRetryTime = 0;
unsigned long lastWiFiCheckTime = 0;
bool idReceived = false;

// Fonction pour gérer la connexion WiFi
bool ensureWiFiConnection()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("Connexion WiFi perdue ou non établie. Tentative de connexion...");
    WiFi.begin(ssid, password);

    // Attendre la connexion avec timeout
    unsigned long startAttempt = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 10000)
    {
      delay(500);
      Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED)
    {
      Serial.println("\nConnecté au WiFi!");
      return true;
    }
    else
    {
      Serial.println("\nÉchec de connexion au WiFi!");
      return false;
    }
  }
  return true; // Déjà connecté
}

void setup()
{
  Serial.begin(9600);
  unsigned long startTime = millis();
  while (!Serial && millis() - startTime < 5000)
    ;

  // Initialiser la puce ECCX08
  if (!ECCX08.begin())
  {
    Serial.println("Échec d'initialisation de la puce ECCX08!");
    while (1)
      ;
  }

  // Première tentative de connexion WiFi
  Serial.print("Connexion au WiFi");
  if (ensureWiFiConnection())
  {
    // Initialiser UDP
    udp.begin(8888);

    // Obtenir l'adresse MAC formatée
    byte mac[6];
    WiFi.macAddress(mac);
    sprintf(macAddress, "%02X:%02X:%02X:%02X:%02X:%02X", 
          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // Première tentative d'obtention d'ID
    requestID();
  }
}

bool requestID() {
  for (int retry = 0; retry < MAX_RETRIES; retry++) {
    Serial.print("Tentative ");
    Serial.print(retry + 1);
    Serial.println(" d'obtention d'ID...");
    
    // Utiliser la puce ECCX08 pour générer un token aléatoire sécurisé (4 octets)
    byte randomToken[4];
    ECCX08.random(randomToken, sizeof(randomToken));
    
    // Préparer le message: MAC + token
    char message[22];  // 17 (MAC) + 1 (séparateur) + 4 (token binaire)
    memcpy(message, macAddress, 17);
    message[17] = ':';  // Séparateur
    memcpy(&message[18], randomToken, 4);
    
    // Envoyer la demande avec le token
    udp.beginPacket(server_ip, server_port);
    udp.write((uint8_t*)message, sizeof(message));
    udp.endPacket();
    
    // Attendre la réponse
    unsigned long startTime = millis();
    while (millis() - startTime < RETRY_TIMEOUT) {
      int packetSize = udp.parsePacket();
      IPAddress remoteIP = udp.remoteIP();
      char remoteIPStr[16]; // Assez grand pour une adresse IP au format xxx.xxx.xxx.xxx
      sprintf(remoteIPStr, "%d.%d.%d.%d", remoteIP[0], remoteIP[1], remoteIP[2], remoteIP[3]);

      if (packetSize > 0 && strcmp(remoteIPStr, server_ip) == 0) {
        // Format attendu: [ID:1byte][TOKEN:4bytes][MQTT_IP:variable]
        if (packetSize >= 5) { // Au minimum ID + TOKEN
          byte receivedID = udp.read();
          
          // Lire le token retourné (4 bytes)
          byte receivedToken[4];
          udp.read(receivedToken, 4);
          
          // Vérifier que le token correspond
          if (memcmp(receivedToken, randomToken, 4) == 0) {
            deviceID = receivedID;
            
            // Lire l'adresse IP du broker MQTT (reste du paquet)
            int ipLength = packetSize - 5; // Soustraire ID (1) et token (4)
            if (ipLength > 0 && ipLength < 16) { // Vérification de sécurité
              char ipBuffer[16] = {0}; // Assez grand pour "255.255.255.255\0"
              udp.read((uint8_t*)ipBuffer, ipLength);
              ipBuffer[ipLength] = '\0'; // S'assurer que c'est terminé par un null
              
              // Stocker l'IP du broker
              strcpy(mqttBrokerIP, ipBuffer);
              
              Serial.print("ID authentifié reçu: ");
              Serial.println(deviceID);
              Serial.print("Broker MQTT: ");
              Serial.println(mqttBrokerIP);
              return true;
            }
          } else {
            Serial.println("Token incorrect, réponse ignorée");
          }
        }
      }
      delay(10);
    }
    Serial.println("Timeout, nouvelle tentative...");
  }
  
  Serial.println("Échec de toutes les tentatives. Reprogrammation d'un essai ultérieur.");
  return false;
}

void loop()
{
  unsigned long currentTime = millis();

  // Vérifier périodiquement la connexion WiFi
  if (currentTime - lastWiFiCheckTime >= WIFI_CHECK_INTERVAL)
  {
    lastWiFiCheckTime = currentTime;

    // Si la connexion est perdue, tenter de reconnecter
    if (!ensureWiFiConnection())
    {
      idReceived = false; // Réinitialiser le statut d'ID si la connexion est perdue
      return;             // Sortir de loop() pour éviter d'exécuter le reste du code sans connexion
    }
  }

  // Si nous avons une connexion WiFi mais pas d'ID
  if (!idReceived)
  {
    // Vérifier si c'est le moment de réessayer
    if (currentTime - lastRetryTime >= RETRY_INTERVAL)
    {
      lastRetryTime = currentTime;
      Serial.println("Tentative périodique de récupération d'ID...");
      idReceived = requestID();
    }
  }
  else
  {
    // Votre code utilisant deviceID et mqttBrokerIP
    // Par exemple, se connecter au broker MQTT:
    //
    // if (strlen(mqttBrokerIP) > 0 && !mqttClient.connected()) {
    //   mqttClient.setServer(mqttBrokerIP, 1883);
    //   mqttClient.connect(...);
    // }
  }

  // Autres actions périodiques
  delay(100);
}