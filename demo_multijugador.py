#!/usr/bin/env python3
"""
Script de demostración rápida del multijugador
Este script inicia un servidor local y muestra cómo conectarse
"""

import threading
import time
import sys
import os

# Agregar el directorio del proyecto al path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def demo_server():
    """Inicia un servidor de demostración"""
    from servidor.game_server import GameServer
    
    print("🚀 Iniciando servidor de demostración en localhost:8888")
    
    server = GameServer(host='localhost', port=8888)
    server.max_players = 4
    
    try:
        server.start()
    except Exception as e:
        print(f"❌ Error en servidor de demo: {e}")

def main():
    print("🎮 Tank Attack - Demo Multijugador")
    print("=" * 40)
    print("Esta demostración:")
    print("1. Inicia un servidor local en puerto 8888")
    print("2. Te muestra cómo conectar clientes")
    print()
    
    respuesta = input("¿Iniciar servidor de demostración? (s/n): ").strip().lower()
    
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        # Iniciar servidor en thread separado
        server_thread = threading.Thread(target=demo_server, daemon=True)
        server_thread.start()
        
        # Esperar un poco para que el servidor inicie
        time.sleep(2)
        
        print("\n✅ Servidor iniciado!")
        print("\n📱 Para conectar clientes:")
        print("1. Abre otra terminal")
        print("2. Ejecuta: python iniciar_cliente.py")
        print("3. Usa 'localhost' como dirección del servidor")
        print("4. Usa '8888' como puerto")
        print("5. Repite para más jugadores")
        print()
        print("🛑 Presiona Ctrl+C para detener")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo demostración...")
    else:
        print("👋 ¡Hasta luego!")
        print("\n💡 Para uso normal:")
        print("- Servidor: python iniciar_servidor.py")
        print("- Cliente:  python iniciar_cliente.py")

if __name__ == "__main__":
    main()