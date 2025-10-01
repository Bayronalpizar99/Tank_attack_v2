#!/usr/bin/env python3
"""
Script para iniciar el cliente de Tank Attack Multijugador
"""

import sys
import os

# Agregar el directorio del proyecto al path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from cliente.game_client import GameClient

def main():
    print("🎮 Tank Attack - Cliente Multijugador")
    print("=" * 40)
    print("Controles del juego:")
    print("  WASD o Flechas - Mover tanque")
    print("  Espacio - Disparar")
    print("  X - Parar")
    print()
    print("Controles del lobby:")
    print("  R - Alternar listo/no listo")
    print("  T - Enviar mensaje de chat")
    print()
    print("🌐 Asegúrate de que el servidor esté ejecutándose")
    print("=" * 40)
    
    # Crear y iniciar cliente
    client = GameClient()
    
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n🛑 Cerrando cliente...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()