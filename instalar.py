#!/usr/bin/env python3
"""
Script de instalación para Tank Attack Multijugador
"""

import subprocess
import sys
import os

def install_requirements():
    """Instala las dependencias necesarias"""
    print("🔧 Instalando dependencias...")
    
    try:
        # Intentar instalar con pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error instalando dependencias")
        print("💡 Intenta manualmente:")
        print("   pip install pygame")
        return False

def test_installation():
    """Prueba que pygame funcione"""
    print("🧪 Probando instalación...")
    
    try:
        import pygame
        pygame.init()
        print("✅ pygame funciona correctamente")
        pygame.quit()
        return True
    except ImportError:
        print("❌ pygame no está instalado correctamente")
        return False

def main():
    print("🎮 Tank Attack - Instalador")
    print("=" * 30)
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("requirements.txt"):
        print("❌ Por favor ejecuta este script desde el directorio del juego")
        return
    
    # Instalar dependencias
    if not install_requirements():
        return
    
    # Probar instalación
    if not test_installation():
        return
    
    print("\n🎉 ¡Instalación completada!")
    print("\n📚 Próximos pasos:")
    print("1. Para servidor: python iniciar_servidor.py")
    print("2. Para cliente:  python iniciar_cliente.py")
    print("3. Lee README_MULTIJUGADOR.md para más información")

if __name__ == "__main__":
    main()