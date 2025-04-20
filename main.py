import socket
import pickle
import os

# Fichier pour stocker la correspondance MAC <-> ID
MAP_FILE = "device_map.pickle"

# Configuration du broker MQTT (la même pour tous les appareils)
MQTT_BROKER_IP = (
    "192.168.1.15"  # Remplacer par l'adresse IP réelle du broker MQTT
)

# Chargement de la carte existante ou création d'une nouvelle
if os.path.exists(MAP_FILE):
    with open(MAP_FILE, "rb") as f:
        device_map = pickle.load(f)
else:
    device_map = {}

next_id = 1
if device_map:
    next_id = max(device_map.values()) % 255 + 1


def start_server(host="0.0.0.0", port=5000):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"UDP Server listening on {host}:{port}")
    print(f"MQTT broker configured at: {MQTT_BROKER_IP}")

    global next_id
    try:
        while True:
            data, client_address = server.recvfrom(1024)

            # Format attendu: MAC (17 octets) + ':' (1 octet) + token (4 octets)
            if len(data) == 22:
                mac_address = data[:17].decode("ascii")
                token = data[18:22]  # 4 octets bruts du token

                # Vérifier si cet appareil a déjà un ID
                if mac_address in device_map:
                    assigned_id = device_map[mac_address]
                else:
                    # Attribuer un nouvel ID
                    assigned_id = next_id
                    device_map[mac_address] = assigned_id
                    next_id = (next_id % 255) + 1

                    # Sauvegarder la carte
                    with open(MAP_FILE, "wb") as f:
                        pickle.dump(device_map, f)

                # Envoyer l'ID, le token pour authentification et l'adresse IP du broker MQTT
                response = bytearray([assigned_id])
                response.extend(token)  # Renvoyer le même token
                response.extend(
                    MQTT_BROKER_IP.encode("ascii")
                )  # Ajouter l'adresse IP du broker

                server.sendto(response, client_address)
                print(
                    f"Assigned ID {assigned_id} to device with MAC {mac_address}"
                )
            else:
                print(
                    f"Invalid request format from {client_address}: {len(data)} bytes"
                )

    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
