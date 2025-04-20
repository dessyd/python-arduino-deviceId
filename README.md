# Arduino IoT Device ID Manager

Ce projet fournit un système léger pour l'attribution automatique d'identifiants uniques aux appareils IoT Arduino sur un réseau local, ainsi que la distribution de l'adresse IP du broker MQTT.

## Fonctionnalités

- Attribution d'un ID unique (1 octet) à chaque appareil Arduino
- Distribution automatique de l'adresse IP du broker MQTT
- Communication sécurisée grâce à un mécanisme de challenge-réponse avec token
- Stockage persistant des associations adresses MAC ↔ IDs
- Réessais automatiques en cas d'échec
- Gestion des reconnexions WiFi

## Architecture

Le système se compose de deux parties principales :

1. **Serveur Python** : Attribue les IDs et conserve les associations
2. **Client Arduino** : Demande et stocke son ID unique et l'adresse du broker MQTT

## Serveur Python

Le serveur utilise un socket UDP pour recevoir les demandes des appareils Arduino et leur attribuer un identifiant unique d'un octet.

### Dépendances

- Python 3.6+
- Bibliothèque standard Python (socket, pickle, os)

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-nom/arduino-id-manager.git
cd arduino-id-manager

# Exécuter le serveur
python server.py
```

### Configuration

Modifiez les variables suivantes dans `server.py` :

```python
# Adresse IP du broker MQTT (la même pour tous les appareils)
MQTT_BROKER_IP = "192.168.1.200"  # Remplacer par l'adresse de votre broker

# Port sur lequel le serveur écoute
SERVER_PORT = 5000
```

## Client Arduino

Le client Arduino se connecte au WiFi, obtient son adresse MAC, et demande un ID unique au serveur. Il stocke également l'adresse du broker MQTT reçue.

### Dépendances

- Arduino MKR WiFi 1010 ou compatible
- Bibliothèques Arduino :
  - WiFiNINA
  - ArduinoECCX08

### Installation

1. Ouvrez le fichier `.ino` dans l'IDE Arduino
2. Modifiez les constantes SSID et mot de passe WiFi
3. Configurez l'adresse IP du serveur
4. Téléversez le programme sur votre Arduino

### Configuration

Modifiez les variables suivantes dans le code Arduino :

```cpp
const char* ssid = "votre_ssid";
const char* password = "votre_mot_de_passe";
const char* server_ip = "192.168.1.100";  // Adresse IP de votre serveur Python
const int server_port = 5000;             // Port du serveur
```

## Protocole de communication

### Demande (Arduino → Serveur)
Format : `[MAC:17bytes][Separator:1byte][Token:4bytes]`
- MAC : Adresse MAC de l'appareil au format XX:XX:XX:XX:XX:XX
- Separator : Caractère ':'
- Token : 4 octets aléatoires générés par la puce cryptographique ECCX08

### Réponse (Serveur → Arduino)
Format : `[ID:1byte][Token:4bytes][MQTT_IP:variable]`
- ID : Identifiant unique d'un octet (1-255)
- Token : Les mêmes 4 octets reçus dans la demande (pour vérification)
- MQTT_IP : Adresse IP du broker MQTT sous forme de chaîne ASCII

## Sécurité

Le système utilise un mécanisme simple de challenge-réponse avec token pour garantir que :
1. L'appareil reçoit bien son propre ID et non celui d'un autre
2. La réponse provient effectivement du serveur légitime

La puce cryptographique ECCX08 du MKR WiFi 1010 est utilisée pour générer des tokens véritablement aléatoires.

## Fonctionnalités futures

- [ ] Authentification basée sur certificats
- [ ] Support pour configuration via portail captif
- [ ] Interface web d'administration
- [ ] Journalisation des connexions et des attributions d'ID

## Licence

Ce projet est sous licence MIT.

## Auteur

Votre Nom - [Dominique Dessy](mailto:reprendre.mezzo_0j@icloud.com)