#!/usr/bin/env python3
"""
Script para iniciar el servidor de Tank Attack Multijugador
"""

import sys
import os

# Agregar el directorio del proyecto al path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from servidor.game_server import GameServer

def main():
    print("🎮 Tank Attack - Servidor Multijugador")
    print("=" * 40)
    
    # Configuración del servidor
    host = input("Dirección IP del servidor (0.0.0.0 para todas las interfaces): ").strip() or "0.0.0.0"
    
    try:
        port = int(input("Puerto del servidor (8888): ").strip() or "8888")
    except ValueError:
        port = 8888
    
    try:
        max_players = int(input("Máximo número de jugadores (4): ").strip() or "4")
    except ValueError:
        max_players = 4
    
    print(f"\n🚀 Iniciando servidor en {host}:{port}")
    print(f"👥 Máximo {max_players} jugadores")
    print(f"🌐 Los clientes pueden conectarse a:")
    
    if host == "0.0.0.0":
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"   - localhost:{port} (desde esta máquina)")
        print(f"   - {local_ip}:{port} (desde otras máquinas en la red)")
    else:
        print(f"   - {host}:{port}")
    
    print("\n🛑 Presiona Ctrl+C para detener el servidor")
    print("=" * 40)
    
    # Crear y iniciar servidor
    server = GameServer(host=host, port=port)
    server.max_players = max_players
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
    finally:
        server.stop()

if __name__ == "__main__":
    main()