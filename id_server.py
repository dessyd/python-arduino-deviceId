#!/usr/bin/env python3
"""
Service d'attribution d'ID pour appareils IoT Arduino
Distribue des identifiants uniques et l'adresse du broker MQTT
"""

import os
import pickle
import socket
import logging
from typing import Dict, Optional, Tuple, Final
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class ServerConfig:
    """Configuration du serveur d'attribution d'ID"""

    host: str
    port: int
    mqtt_broker_ip: str
    map_file: Path


def setup_logging() -> None:
    """Configure le système de journalisation"""
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def load_config() -> ServerConfig:
    """Charge la configuration depuis les variables d'environnement"""
    load_dotenv()

    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "5000"))
    mqtt_broker_ip = os.getenv("MQTT_BROKER_IP", "192.168.1.15")
    map_file = Path(os.getenv("MAP_FILE", "device_map.pickle"))

    return ServerConfig(host, port, mqtt_broker_ip, map_file)


def load_device_map(map_file: Path) -> Tuple[Dict[str, int], int]:
    """Charge la carte des appareils existants ou en crée une nouvelle"""
    device_map: Dict[str, int] = {}
    next_id = 1

    if map_file.exists():
        try:
            with open(map_file, "rb") as f:
                device_map = pickle.load(f)
            logging.debug(f"Loaded map from: {map_file}")

            if device_map:
                next_id = max(device_map.values()) % 255 + 1
        except (pickle.PickleError, EOFError, IOError) as e:
            logging.error(f"Error loading device map: {e}")
            # Continuer avec une carte vide
    else:
        logging.debug(f"Creating new map file: {map_file}")

    return device_map, next_id


def save_device_map(device_map: Dict[str, int], map_file: Path) -> bool:
    """Sauvegarde la carte des appareils"""
    try:
        with open(map_file, "wb") as f:
            pickle.dump(device_map, f)
        logging.debug(f"Saved map to: {map_file}")
        return True
    except (IOError, OSError) as e:
        logging.error(f"Error saving device map: {e}")
        return False


def process_request(
    payload: bytes,
    client_address: Tuple[str, int],
    device_map: Dict[str, int],
    next_id: int,
    mqtt_broker_ip: str,
    map_file: Path,
) -> Tuple[Optional[bytearray], int]:
    """Traite une demande d'ID et prépare la réponse"""
    # Format attendu: MAC (17 octets) + ':' (1 octet) + token (4 octets)
    if len(payload) != 22:
        logging.warning(
            f"Invalid request format from {client_address}: {len(payload)} bytes"
        )
        return None, next_id

    mac_address = payload[:17].decode("ascii")
    token = payload[18:22]  # 4 octets bruts du token

    # Vérifier si cet appareil a déjà un ID
    if mac_address in device_map:
        assigned_id = device_map[mac_address]
        logging.info(f"Existing device {mac_address}, ID: {assigned_id}")
    else:
        # Attribuer un nouvel ID
        assigned_id = next_id
        device_map[mac_address] = assigned_id
        next_id = (next_id % 255) + 1

        # Sauvegarder la carte
        save_device_map(device_map, map_file)
        logging.info(f"New device {mac_address}, assigned ID: {assigned_id}")

    # Préparer la réponse: [ID:1byte][TOKEN:4bytes][MQTT_IP:variable]
    response = bytearray([assigned_id])
    response.extend(token)  # Renvoyer le même token
    response.extend(
        mqtt_broker_ip.encode("ascii")
    )  # Ajouter l'adresse IP du broker

    return response, next_id


def run_server(config: ServerConfig) -> None:
    """Exécute le serveur UDP d'attribution d'ID"""
    # Charger la carte des appareils
    device_map, next_id = load_device_map(config.map_file)

    # Créer et configurer le socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((config.host, config.port))
        logging.info(f"UDP Server listening on {config.host}:{config.port}")
        logging.info(f"MQTT broker configured at: {config.mqtt_broker_ip}")

        try:
            while True:
                payload, client_address = server.recvfrom(1024)

                response, next_id = process_request(
                    payload,
                    client_address,
                    device_map,
                    next_id,
                    config.mqtt_broker_ip,
                    config.map_file,
                )

                if response:
                    server.sendto(response, client_address)

        except KeyboardInterrupt:
            logging.info("Server shutting down...")
            save_device_map(device_map, config.map_file)
            logging.info("Final device map saved")


def main() -> None:
    """Point d'entrée principal du programme"""
    setup_logging()
    config = load_config()
    run_server(config)


if __name__ == "__main__":
    main()
