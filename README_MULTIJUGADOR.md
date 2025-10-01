# Tank Attack - Modo Multijugador

¡Ahora puedes jugar Tank Attack con amigos desde diferentes computadoras!

## 🎮 Características

- **Multijugador en red**: Hasta 4 jugadores desde diferentes máquinas
- **Servidor dedicado**: Una máquina actúa como servidor
- **Cooperativo**: Trabajen juntos para completar los niveles
- **Lobby con chat**: Esperen a que todos estén listos antes de empezar
- **Sincronización en tiempo real**: Todos ven lo mismo al mismo tiempo

## 🚀 Cómo Jugar

### 1. Configurar el Servidor

En la computadora que actuará como servidor:

```bash
python iniciar_servidor.py
```

El script te pedirá:
- **Dirección IP**: Usa `0.0.0.0` para permitir conexiones desde cualquier máquina en la red
- **Puerto**: Por defecto 8888 (asegúrate de que esté abierto en el firewall)
- **Máximo jugadores**: Entre 2 y 4 jugadores

### 2. Conectar Clientes

En cada computadora de los jugadores:

```bash
python iniciar_cliente.py
```

En el menú del cliente:
1. Presiona **ENTER** para conectar
2. Ingresa la **dirección IP** del servidor
3. Ingresa el **puerto** (por defecto 8888)
4. Ingresa tu **nombre de usuario**

### 3. En el Lobby

Una vez conectados al servidor:
- Presiona **R** para alternar entre "LISTO" y "NO LISTO"
- Presiona **T** para enviar mensajes de chat
- El juego inicia automáticamente cuando todos están listos (mínimo 2 jugadores)

### 4. Durante el Juego

**Controles:**
- **WASD** o **Flechas**: Mover tanque
- **Espacio**: Disparar
- **X**: Parar tanque

**Objetivo:**
- Trabajen juntos para destruir todos los objetivos del nivel
- Si todos los jugadores mueren, es Game Over
- Completen todos los niveles para ganar

## 🌐 Configuración de Red

### Para Jugar en la Misma Red Local

1. **Servidor**: Usa `0.0.0.0` como dirección IP
2. **Clientes**: Conecten a la IP local del servidor (ej: `192.168.1.100`)

### Para Jugar por Internet

1. **Configurar Router**: 
   - Abre el puerto 8888 (o el que elijas) en el router del servidor
   - Configura port forwarding hacia la IP del servidor
2. **Servidor**: Puede usar `0.0.0.0` o su IP local
3. **Clientes**: Conecten a la IP pública del servidor

### Encontrar la IP del Servidor

En Windows:
```cmd
ipconfig
```

En Mac/Linux:
```bash
ifconfig
ip addr show
```

Busca la dirección que comience con `192.168.x.x` o `10.x.x.x`

## 🎯 Tipos de Jugadores

- **Jugador 1** (Verde): WASD + Espacio + X
- **Jugador 2** (Azul): IJKL + Shift Derecho + Ctrl Derecho  
- **Jugador 3** (Amarillo): TFGH + R + Y
- **Jugador 4** (Magenta): Flechas + Enter + Alt Derecho

*Nota: En el modo en red, todos usan WASD + Espacio + X*

## 🛠️ Solución de Problemas

### "No se puede conectar al servidor"
- Verifica que el servidor esté ejecutándose
- Comprueba la dirección IP y puerto
- Revisa el firewall (debe permitir el puerto del juego)

### "Servidor lleno"
- El servidor ya tiene el máximo de jugadores
- Espera a que alguien se desconecte o aumenta el límite en el servidor

### Lag o desconexiones
- Verifica la conexión a internet
- Reduce la distancia entre servidor y clientes
- Cierra otros programas que usen internet

### El juego no inicia
- Asegúrate de que pygame esté instalado: `pip install pygame`
- Verifica que todos los archivos del juego estén presentes

## 📝 Comandos Adicionales

### Servidor con Opciones Específicas

```bash
python servidor/game_server.py --host 0.0.0.0 --port 8888 --max-players 4
```

### Cliente desde Línea de Comandos

```bash
python cliente/game_client.py
```

## 🎮 Modos de Juego

### Modo Individual
```bash
python main.py
```

### Modo Multijugador Local (Misma Máquina)
```bash
python main_multijugador.py
```

### Modo Multijugador en Red
```bash
# En el servidor:
python iniciar_servidor.py

# En cada cliente:
python iniciar_cliente.py
```

## 🔧 Requisitos

- Python 3.7+
- pygame
- Conexión de red (para multijugador en red)

## 🎊 ¡Diviértanse!

¡Tank Attack es más divertido con amigos! Trabajen en equipo, comuníquense y dominen el campo de batalla juntos.

¿Encontraste un bug o tienes una sugerencia? ¡Déjanos saber!