# cliente/game_client.py
import socket
import threading
import json
import time
import pygame
import sys
import os

# Agregar el directorio padre al path para importar módulos del juego
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constantes import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, UP, DOWN, LEFT, RIGHT, STAY,
    MENU_MUSIC_PATH, AMBIENT_LEVEL_MUSIC_PATH, GENERAL_TANK_MOVING_SOUND_PATH,
    PLAYER_SHOOT_SOUND_PATH, PLAYER_FINAL_DESTRUCTION_SOUND_PATH,
    GAME_OVER_SCREEN_MUSIC_PATH, LEVEL_COMPLETE_MUSIC_PATH, FINAL_VICTORY_MUSIC_PATH
)
from frontend.vista import VistaJuego

class GameClient:
    def __init__(self):
        # Configuración de red
        self.socket = None
        self.connected = False
        self.server_host = "localhost"
        self.server_port = 8888
        
        # Estado del cliente
        self.client_id = None
        self.player_id = None
        self.username = "Jugador"
        self.ready = False
        
        # Estado del juego
        self.game_state = None
        self.lobby_state = None
        self.chat_messages = []
        
        # Pygame
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        
        # Cargar sonidos
        self._load_sounds()
        
        # Vista
        self.vista = VistaJuego()
        self.clock = pygame.time.Clock()
        
        # Control de entrada
        self.keys_pressed = set()
        self.last_input_sent = 0
        self.input_rate_limit = 1.0 / 30  # 30 FPS para entrada
        
        # Estado del cliente
        self.client_state = "MENU"  # MENU, CONNECTING, LOBBY, PLAYING, DISCONNECTED
        
        # Threads
        self.network_thread = None
        self.running = False
        
    def _load_sounds(self):
        """Carga los sonidos del juego"""
        self.sounds = {}
        
        if pygame.mixer.get_init():
            sound_files = {
                'menu': MENU_MUSIC_PATH,
                'ambient': AMBIENT_LEVEL_MUSIC_PATH,
                'tank_moving': GENERAL_TANK_MOVING_SOUND_PATH,
                'player_shoot': PLAYER_SHOOT_SOUND_PATH,
                'player_death': PLAYER_FINAL_DESTRUCTION_SOUND_PATH,
                'game_over': GAME_OVER_SCREEN_MUSIC_PATH,
                'level_complete': LEVEL_COMPLETE_MUSIC_PATH,
                'victory': FINAL_VICTORY_MUSIC_PATH
            }
            
            for name, path in sound_files.items():
                try:
                    if name in ['menu', 'ambient', 'game_over', 'level_complete', 'victory']:
                        # Estos son música de fondo, se cargarán cuando sea necesario
                        self.sounds[name] = path
                    else:
                        # Estos son efectos de sonido
                        sound = pygame.mixer.Sound(path)
                        if name == 'player_shoot':
                            sound.set_volume(0.6)
                        elif name == 'player_death':
                            sound.set_volume(0.8)
                        self.sounds[name] = sound
                except pygame.error as e:
                    print(f"⚠️ No se pudo cargar sonido {name}: {e}")
    
    def start(self):
        """Inicia el cliente"""
        self.running = True
        
        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n🛑 Cliente interrumpido por el usuario")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el cliente"""
        self.running = False
        
        if self.connected:
            self.disconnect()
        
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        
        pygame.quit()
        print("✅ Cliente cerrado")
    
    def connect(self, host: str, port: int, username: str):
        """Conecta al servidor"""
        try:
            self.server_host = host
            self.server_port = port
            self.username = username
            
            print(f"🔗 Conectando a {host}:{port}...")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            
            # Iniciar thread de red
            self.network_thread = threading.Thread(target=self._network_loop, daemon=True)
            self.network_thread.start()
            
            # Solicitar unirse al juego
            self._send_message({
                'type': 'join_game',
                'username': username
            })
            
            self.client_state = "CONNECTING"
            return True
            
        except Exception as e:
            print(f"❌ Error conectando al servidor: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta del servidor"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.connected = False
        self.client_state = "DISCONNECTED"
        print("👋 Desconectado del servidor")
    
    def _network_loop(self):
        """Loop de red para recibir mensajes del servidor"""
        while self.running and self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self._process_server_message(message)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Error decodificando mensaje del servidor: {e}")
                
            except Exception as e:
                if self.running:
                    print(f"❌ Error en loop de red: {e}")
                break
        
        self.connected = False
        self.client_state = "DISCONNECTED"
    
    def _process_server_message(self, message: dict):
        """Procesa un mensaje recibido del servidor"""
        msg_type = message.get('type')
        
        if msg_type == 'connection_accepted':
            self.client_id = message.get('client_id')
            print(f"✅ Conectado al servidor (ID: {self.client_id})")
            
        elif msg_type == 'connection_rejected':
            reason = message.get('reason', 'Desconocido')
            print(f"❌ Conexión rechazada: {reason}")
            self.disconnect()
            
        elif msg_type == 'join_accepted':
            self.player_id = message.get('player_id')
            self.username = message.get('username')
            self.client_state = "LOBBY"
            print(f"🎮 Te uniste como {self.username} (Jugador {self.player_id})")
            
        elif msg_type == 'join_rejected':
            reason = message.get('reason', 'Desconocido')
            print(f"❌ No se pudo unir al juego: {reason}")
            
        elif msg_type == 'lobby_state':
            self.lobby_state = message
            
        elif msg_type == 'game_start':
            self.client_state = "PLAYING"
            level = message.get('level', 1)
            print(f"🎯 ¡Juego iniciado! Nivel {level}")
            self._play_music('ambient')
            
        elif msg_type == 'game_state':
            self.game_state = message.get('state')
            
        elif msg_type == 'game_over':
            reason = message.get('reason', '')
            print(f"💀 Game Over: {reason}")
            self._play_music('game_over')
            
        elif msg_type == 'level_completed':
            next_level = message.get('next_level')
            print(f"🎉 ¡Nivel completado! Siguiente: {next_level}")
            self._play_sound('level_complete')
            
        elif msg_type == 'victory':
            msg = message.get('message', '¡Victoria!')
            print(f"🏆 {msg}")
            self._play_music('victory')
            
        elif msg_type == 'return_to_lobby':
            self.client_state = "LOBBY"
            self.ready = False
            print("🏠 Regresando al lobby...")
            self._play_music('menu')
            
        elif msg_type == 'chat':
            username = message.get('username', 'Anónimo')
            msg = message.get('message', '')
            timestamp = message.get('timestamp', time.time())
            self.chat_messages.append({
                'username': username,
                'message': msg,
                'timestamp': timestamp
            })
            # Mantener solo los últimos 10 mensajes
            if len(self.chat_messages) > 10:
                self.chat_messages.pop(0)
            print(f"💬 {username}: {msg}")
            
        elif msg_type == 'ping':
            self._send_message({'type': 'pong'})
            
        elif msg_type == 'pong':
            pass  # Respuesta a nuestro ping
    
    def _send_message(self, message: dict):
        """Envía un mensaje al servidor"""
        if not self.connected or not self.socket:
            return False
        
        try:
            data = json.dumps(message).encode('utf-8')
            self.socket.send(data)
            return True
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
    
    def _play_music(self, music_name: str):
        """Reproduce música de fondo"""
        if not pygame.mixer.get_init() or music_name not in self.sounds:
            return
        
        try:
            music_path = self.sounds[music_name]
            if isinstance(music_path, str):  # Es una ruta de archivo
                pygame.mixer.music.load(music_path)
                volume = 0.5 if music_name == 'menu' else 0.4
                pygame.mixer.music.set_volume(volume)
                loops = -1 if music_name != 'level_complete' else 0
                pygame.mixer.music.play(loops=loops)
        except pygame.error as e:
            print(f"⚠️ Error reproduciendo música {music_name}: {e}")
    
    def _play_sound(self, sound_name: str):
        """Reproduce un efecto de sonido"""
        if not pygame.mixer.get_init() or sound_name not in self.sounds:
            return
        
        try:
            sound = self.sounds[sound_name]
            if hasattr(sound, 'play'):  # Es un objeto Sound
                sound.play()
        except pygame.error as e:
            print(f"⚠️ Error reproduciendo sonido {sound_name}: {e}")
    
    def _main_loop(self):
        """Loop principal del cliente"""
        self._play_music('menu')
        
        while self.running:
            current_time = time.time()
            
            # Procesar eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                
                self._handle_event(event)
            
            # Enviar entrada del jugador si está jugando
            if (self.client_state == "PLAYING" and 
                current_time - self.last_input_sent > self.input_rate_limit):
                self._send_player_input()
                self.last_input_sent = current_time
            
            # Dibujar
            self._render()
            
            # Control de framerate
            self.clock.tick(60)
    
    def _handle_event(self, event):
        """Maneja eventos de pygame"""
        if event.type == pygame.KEYDOWN:
            if self.client_state == "MENU":
                if event.key == pygame.K_RETURN:
                    # Conectar al servidor
                    host = input("Dirección del servidor (localhost): ").strip() or "localhost"
                    try:
                        port = int(input("Puerto (8888): ").strip() or "8888")
                    except ValueError:
                        port = 8888
                    username = input("Tu nombre de usuario: ").strip() or f"Jugador{int(time.time() % 1000)}"
                    
                    if self.connect(host, port, username):
                        print("🔄 Conectando...")
                    else:
                        print("❌ No se pudo conectar")
                        
            elif self.client_state == "LOBBY":
                if event.key == pygame.K_r:
                    # Alternar estado ready
                    self.ready = not self.ready
                    self._send_message({
                        'type': 'ready',
                        'ready': self.ready
                    })
                elif event.key == pygame.K_t:
                    # Abrir chat (simplificado)
                    message = input("Mensaje: ").strip()
                    if message:
                        self._send_message({
                            'type': 'chat',
                            'message': message
                        })
                        
            elif self.client_state == "PLAYING":
                # Manejar entrada del juego
                self.keys_pressed.add(event.key)
                
        elif event.type == pygame.KEYUP:
            if self.client_state == "PLAYING":
                self.keys_pressed.discard(event.key)
    
    def _send_player_input(self):
        """Envía la entrada del jugador al servidor"""
        if not self.connected:
            return
        
        inputs = {}
        
        # Detectar movimiento
        if pygame.K_w in self.keys_pressed or pygame.K_UP in self.keys_pressed:
            inputs['move'] = 'up'
        elif pygame.K_s in self.keys_pressed or pygame.K_DOWN in self.keys_pressed:
            inputs['move'] = 'down'
        elif pygame.K_a in self.keys_pressed or pygame.K_LEFT in self.keys_pressed:
            inputs['move'] = 'left'
        elif pygame.K_d in self.keys_pressed or pygame.K_RIGHT in self.keys_pressed:
            inputs['move'] = 'right'
        
        # Detectar disparo
        if pygame.K_SPACE in self.keys_pressed:
            inputs['shoot'] = True
        
        # Detectar parada
        if pygame.K_x in self.keys_pressed:
            inputs['stop'] = True
        
        # Enviar solo si hay entrada
        if inputs:
            self._send_message({
                'type': 'player_input',
                'inputs': inputs
            })
    
    def _render(self):
        """Renderiza la pantalla"""
        self.vista.screen.fill((0, 0, 0))
        
        if self.client_state == "MENU":
            self._render_menu()
        elif self.client_state == "CONNECTING":
            self._render_connecting()
        elif self.client_state == "LOBBY":
            self._render_lobby()
        elif self.client_state == "PLAYING":
            self._render_game()
        elif self.client_state == "DISCONNECTED":
            self._render_disconnected()
        
        pygame.display.flip()
    
    def _render_menu(self):
        """Renderiza el menú principal"""
        title = self.vista.fuente_mensajes.render("Tank Attack - Cliente", True, (0, 255, 0))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        self.vista.screen.blit(title, title_rect)
        
        instruction = self.vista.fuente_hud.render("Presiona ENTER para conectar", True, (255, 255, 255))
        instruction_rect = instruction.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.vista.screen.blit(instruction, instruction_rect)
    
    def _render_connecting(self):
        """Renderiza pantalla de conexión"""
        text = self.vista.fuente_mensajes.render("Conectando...", True, (255, 255, 0))
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.vista.screen.blit(text, text_rect)
    
    def _render_lobby(self):
        """Renderiza el lobby"""
        # Título
        title = self.vista.fuente_mensajes.render("Lobby Multijugador", True, (255, 215, 0))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 80))
        self.vista.screen.blit(title, title_rect)
        
        # Información del jugador
        player_info = f"Eres: {self.username} (Jugador {self.player_id})"
        player_text = self.vista.fuente_hud.render(player_info, True, (255, 255, 255))
        self.vista.screen.blit(player_text, (50, 150))
        
        # Estado ready
        ready_text = f"Estado: {'LISTO' if self.ready else 'NO LISTO'}"
        ready_color = (0, 255, 0) if self.ready else (255, 0, 0)
        ready_surf = self.vista.fuente_hud.render(ready_text, True, ready_color)
        self.vista.screen.blit(ready_surf, (50, 180))
        
        # Lista de jugadores
        if self.lobby_state:
            players = self.lobby_state.get('players', [])
            y_offset = 220
            
            players_title = self.vista.fuente_hud.render("Jugadores en el lobby:", True, (255, 255, 255))
            self.vista.screen.blit(players_title, (50, y_offset))
            y_offset += 30
            
            for player in players:
                status = "LISTO" if player['ready'] else "NO LISTO"
                color = (0, 255, 0) if player['ready'] else (255, 255, 255)
                player_text = f"Jugador {player['player_id']}: {player['username']} - {status}"
                player_surf = self.vista.fuente_editor_info.render(player_text, True, color)
                self.vista.screen.blit(player_surf, (70, y_offset))
                y_offset += 25
        
        # Controles
        controls = [
            "R - Alternar listo/no listo",
            "T - Abrir chat",
            "El juego inicia cuando todos estén listos (mín. 2 jugadores)"
        ]
        
        y_offset = SCREEN_HEIGHT - 100
        for control in controls:
            control_surf = self.vista.fuente_editor_info.render(control, True, (200, 200, 200))
            self.vista.screen.blit(control_surf, (50, y_offset))
            y_offset += 20
    
    def _render_game(self):
        """Renderiza el juego"""
        if self.game_state:
            # Dibujar grid
            for x in range(0, SCREEN_WIDTH, TILE_SIZE):
                pygame.draw.line(self.vista.screen, (128, 128, 128), (x, 0), (x, SCREEN_HEIGHT))
            for y in range(0, SCREEN_HEIGHT, TILE_SIZE):
                pygame.draw.line(self.vista.screen, (128, 128, 128), (0, y), (SCREEN_WIDTH, y))
            
            # Actualizar objetos visuales
            self.vista.actualizar_objetos_visuales(self.game_state)
            self.vista.sprites_visuales.draw(self.vista.screen)
            
            # Dibujar HUD
            self.vista._dibujar_hud(self.game_state)
            
            # Dibujar explosiones de enemigos
            if "enemigos_destruyendose" in self.game_state:
                img_explosion = self.vista.assets.get('frontend/assets/explosion_enemigo.png')
                if img_explosion:
                    for destruccion_info in self.game_state["enemigos_destruyendose"]:
                        x_pos = destruccion_info["x_tile"] * TILE_SIZE
                        y_pos = destruccion_info["y_tile"] * TILE_SIZE
                        self.vista.screen.blit(img_explosion, (x_pos, y_pos))
        
        # Controles
        controls_text = "WASD/Flechas: Mover | Espacio: Disparar | X: Parar"
        controls_surf = pygame.font.Font(None, 24).render(controls_text, True, (255, 255, 255))
        self.vista.screen.blit(controls_surf, (10, SCREEN_HEIGHT - 30))
    
    def _render_disconnected(self):
        """Renderiza pantalla de desconexión"""
        text = self.vista.fuente_mensajes.render("Desconectado", True, (255, 0, 0))
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.vista.screen.blit(text, text_rect)
        
        instruction = self.vista.fuente_hud.render("Cierra la ventana para salir", True, (255, 255, 255))
        instruction_rect = instruction.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.vista.screen.blit(instruction, instruction_rect)

if __name__ == "__main__":
    client = GameClient()
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n🛑 Cliente interrumpido por el usuario")
    finally:
        client.stop()