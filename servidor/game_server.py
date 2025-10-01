# servidor/game_server.py
import socket
import threading
import json
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional
import sys
import os

# Agregar el directorio padre al path para importar módulos del juego
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constantes import (
    JUGANDO, GAME_OVER, NIVEL_COMPLETADO, VICTORIA_FINAL,
    TIPO_JUGADOR_1, TIPO_JUGADOR_2, TIPO_JUGADOR_3, TIPO_JUGADOR_4,
    UP, DOWN, LEFT, RIGHT, STAY
)
from multiplayer.motor_multijugador import MotorMultijugador
from multiplayer.player_manager import PlayerManager

@dataclass
class ConnectedClient:
    """Información de un cliente conectado"""
    socket: socket.socket
    address: str
    player_id: Optional[int] = None
    username: str = "Jugador"
    ready: bool = False
    last_ping: float = 0

class GameServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        
        # Gestión de clientes
        self.clients: Dict[str, ConnectedClient] = {}  # client_id -> ConnectedClient
        self.client_lock = threading.Lock()
        
        # Gestión del juego
        self.player_manager = PlayerManager()
        self.motor = MotorMultijugador(self.player_manager)
        self.game_state = "LOBBY"  # LOBBY, PLAYING, FINISHED
        self.current_level = 1
        self.max_players = 4
        
        # Configuración de red
        self.tick_rate = 30  # Actualizaciones por segundo
        self.ping_interval = 5  # Segundos entre pings
        
    def start(self):
        """Inicia el servidor"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"🎮 Servidor de Tank Attack iniciado en {self.host}:{self.port}")
            print(f"📡 Esperando conexiones... (máximo {self.max_players} jugadores)")
            
            # Iniciar threads del servidor
            threading.Thread(target=self._accept_connections, daemon=True).start()
            threading.Thread(target=self._game_loop, daemon=True).start()
            threading.Thread(target=self._ping_clients, daemon=True).start()
            
            # Mantener el servidor vivo
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Cerrando servidor...")
                
        except Exception as e:
            print(f"❌ Error al iniciar servidor: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el servidor"""
        self.running = False
        
        # Cerrar todas las conexiones de clientes
        with self.client_lock:
            for client in self.clients.values():
                try:
                    client.socket.close()
                except:
                    pass
            self.clients.clear()
        
        # Cerrar socket del servidor
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        print("✅ Servidor cerrado")
    
    def _accept_connections(self):
        """Acepta nuevas conexiones de clientes"""
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                client_id = str(uuid.uuid4())
                
                print(f"🔗 Nueva conexión desde {address}")
                
                # Verificar si hay espacio
                with self.client_lock:
                    if len(self.clients) >= self.max_players:
                        self._send_to_client(client_socket, {
                            'type': 'connection_rejected',
                            'reason': 'Servidor lleno'
                        })
                        client_socket.close()
                        continue
                    
                    # Agregar cliente
                    client = ConnectedClient(
                        socket=client_socket,
                        address=f"{address[0]}:{address[1]}",
                        last_ping=time.time()
                    )
                    self.clients[client_id] = client
                
                # Enviar confirmación de conexión
                self._send_to_client(client_socket, {
                    'type': 'connection_accepted',
                    'client_id': client_id,
                    'server_info': {
                        'version': '1.0',
                        'max_players': self.max_players,
                        'current_players': len(self.clients)
                    }
                })
                
                # Iniciar thread para manejar este cliente
                threading.Thread(target=self._handle_client, args=(client_id,), daemon=True).start()
                
            except Exception as e:
                if self.running:
                    print(f"❌ Error aceptando conexión: {e}")
    
    def _handle_client(self, client_id: str):
        """Maneja los mensajes de un cliente específico"""
        with self.client_lock:
            client = self.clients.get(client_id)
        
        if not client:
            return
        
        try:
            while self.running and client_id in self.clients:
                # Recibir datos del cliente
                data = client.socket.recv(1024)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self._process_client_message(client_id, message)
                except json.JSONDecodeError:
                    print(f"⚠️ Mensaje inválido de {client.address}")
                
        except Exception as e:
            print(f"❌ Error manejando cliente {client.address}: {e}")
        finally:
            self._disconnect_client(client_id)
    
    def _process_client_message(self, client_id: str, message: dict):
        """Procesa un mensaje recibido de un cliente"""
        with self.client_lock:
            client = self.clients.get(client_id)
        
        if not client:
            return
        
        msg_type = message.get('type')
        
        if msg_type == 'join_game':
            self._handle_join_game(client_id, message)
        elif msg_type == 'player_input':
            self._handle_player_input(client_id, message)
        elif msg_type == 'ready':
            self._handle_player_ready(client_id, message)
        elif msg_type == 'ping':
            client.last_ping = time.time()
            self._send_to_client(client.socket, {'type': 'pong'})
        elif msg_type == 'chat':
            self._handle_chat_message(client_id, message)
        else:
            print(f"⚠️ Tipo de mensaje desconocido: {msg_type}")
    
    def _handle_join_game(self, client_id: str, message: dict):
        """Maneja la solicitud de un cliente para unirse al juego"""
        with self.client_lock:
            client = self.clients.get(client_id)
        
        if not client:
            return
        
        username = message.get('username', f'Jugador{len(self.clients)}')
        client.username = username
        
        # Asignar ID de jugador
        assigned_players = [c.player_id for c in self.clients.values() if c.player_id is not None]
        for player_id in range(1, 5):
            if player_id not in assigned_players:
                client.player_id = player_id
                break
        
        if client.player_id is None:
            self._send_to_client(client.socket, {
                'type': 'join_rejected',
                'reason': 'No hay slots disponibles'
            })
            return
        
        # Agregar jugador al manager
        self.player_manager.add_player(client.player_id, username)
        
        # Confirmar unión
        self._send_to_client(client.socket, {
            'type': 'join_accepted',
            'player_id': client.player_id,
            'username': username
        })
        
        # Notificar a todos los clientes sobre el nuevo jugador
        self._broadcast_lobby_state()
        
        print(f"👤 {username} se unió como Jugador {client.player_id}")
    
    def _handle_player_input(self, client_id: str, message: dict):
        """Maneja la entrada de un jugador durante el juego"""
        with self.client_lock:
            client = self.clients.get(client_id)
        
        if not client or client.player_id is None or self.game_state != "PLAYING":
            return
        
        # Procesar entrada del jugador
        inputs = message.get('inputs', {})
        
        # Convertir entrada a formato del motor de juego
        actions = {}
        if inputs.get('move'):
            direction_map = {
                'up': UP, 'down': DOWN, 'left': LEFT, 'right': RIGHT
            }
            if inputs['move'] in direction_map:
                actions['mover'] = direction_map[inputs['move']]
        
        if inputs.get('shoot'):
            actions['disparar'] = True
            
        if inputs.get('stop'):
            actions['detenerse'] = True
        
        # Almacenar acciones para el próximo tick del juego
        if not hasattr(self, '_pending_actions'):
            self._pending_actions = {}
        self._pending_actions[client.player_id] = actions
    
    def _handle_player_ready(self, client_id: str, message: dict):
        """Maneja cuando un jugador indica que está listo"""
        with self.client_lock:
            client = self.clients.get(client_id)
        
        if not client:
            return
        
        client.ready = message.get('ready', False)
        
        # Verificar si todos los jugadores están listos
        all_ready = True
        active_players = 0
        
        for c in self.clients.values():
            if c.player_id is not None:
                active_players += 1
                if not c.ready:
                    all_ready = False
        
        if all_ready and active_players >= 2 and self.game_state == "LOBBY":
            self._start_game()
        
        self._broadcast_lobby_state()
    
    def _handle_chat_message(self, client_id: str, message: dict):
        """Maneja mensajes de chat"""
        with self.client_lock:
            client = self.clients.get(client_id)
        
        if not client:
            return
        
        chat_message = {
            'type': 'chat',
            'username': client.username,
            'message': message.get('message', ''),
            'timestamp': time.time()
        }
        
        self._broadcast_message(chat_message)
    
    def _start_game(self):
        """Inicia una nueva partida"""
        self.game_state = "PLAYING"
        self.current_level = 1
        
        # Cargar nivel en el motor
        success = self.motor.cargar_nivel(self.current_level)
        if not success:
            print("❌ Error cargando nivel")
            self.game_state = "LOBBY"
            return
        
        print(f"🎯 Iniciando partida con {len([c for c in self.clients.values() if c.player_id is not None])} jugadores")
        
        # Notificar a todos los clientes
        self._broadcast_message({
            'type': 'game_start',
            'level': self.current_level
        })
    
    def _game_loop(self):
        """Loop principal del juego"""
        last_update = time.time()
        
        while self.running:
            current_time = time.time()
            delta_time = (current_time - last_update) * 1000  # Convertir a ms
            
            if self.game_state == "PLAYING":
                # Obtener acciones pendientes
                actions = getattr(self, '_pending_actions', {})
                self._pending_actions = {}
                
                # Actualizar estado del juego
                result = self.motor.actualizar_estado(actions, delta_time)
                
                # Verificar estado del juego
                if result == GAME_OVER:
                    self._handle_game_over()
                elif result == NIVEL_COMPLETADO:
                    self._handle_level_completed()
                elif result == VICTORIA_FINAL:
                    self._handle_victory()
                
                # Enviar estado actualizado a todos los clientes
                game_state = self.motor.get_estado_para_vista()
                self._broadcast_game_state(game_state)
            
            last_update = current_time
            
            # Controlar framerate
            sleep_time = (1.0 / self.tick_rate) - (time.time() - current_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _handle_game_over(self):
        """Maneja el fin del juego"""
        self.game_state = "FINISHED"
        
        self._broadcast_message({
            'type': 'game_over',
            'reason': 'Todos los jugadores fueron derrotados'
        })
        
        # Volver al lobby después de unos segundos
        threading.Timer(5.0, self._return_to_lobby).start()
    
    def _handle_level_completed(self):
        """Maneja la compleción de un nivel"""
        self.current_level += 1
        
        self._broadcast_message({
            'type': 'level_completed',
            'next_level': self.current_level
        })
        
        # Cargar siguiente nivel
        success = self.motor.cargar_nivel(self.current_level)
        if not success:
            self._handle_victory()
    
    def _handle_victory(self):
        """Maneja la victoria final"""
        self.game_state = "FINISHED"
        
        self._broadcast_message({
            'type': 'victory',
            'message': '¡Felicidades! Han completado todos los niveles'
        })
        
        # Volver al lobby
        threading.Timer(5.0, self._return_to_lobby).start()
    
    def _return_to_lobby(self):
        """Regresa al lobby"""
        self.game_state = "LOBBY"
        
        # Resetear estado de jugadores
        with self.client_lock:
            for client in self.clients.values():
                client.ready = False
        
        self.player_manager.reset_all_players()
        
        self._broadcast_message({
            'type': 'return_to_lobby'
        })
        
        self._broadcast_lobby_state()
    
    def _ping_clients(self):
        """Envía pings periódicos a los clientes"""
        while self.running:
            current_time = time.time()
            disconnected_clients = []
            
            with self.client_lock:
                for client_id, client in self.clients.items():
                    # Verificar timeout
                    if current_time - client.last_ping > 30:  # 30 segundos timeout
                        disconnected_clients.append(client_id)
                    else:
                        # Enviar ping
                        try:
                            self._send_to_client(client.socket, {'type': 'ping'})
                        except:
                            disconnected_clients.append(client_id)
            
            # Desconectar clientes que no responden
            for client_id in disconnected_clients:
                self._disconnect_client(client_id)
            
            time.sleep(self.ping_interval)
    
    def _disconnect_client(self, client_id: str):
        """Desconecta un cliente"""
        with self.client_lock:
            client = self.clients.pop(client_id, None)
        
        if not client:
            return
        
        print(f"👋 {client.username} ({client.address}) se desconectó")
        
        # Remover del manager de jugadores
        if client.player_id is not None:
            self.player_manager.remove_player(client.player_id)
        
        # Cerrar socket
        try:
            client.socket.close()
        except:
            pass
        
        # Si no quedan jugadores suficientes y está jugando, terminar partida
        active_players = len([c for c in self.clients.values() if c.player_id is not None])
        if active_players < 2 and self.game_state == "PLAYING":
            self._handle_game_over()
        
        # Actualizar lobby
        self._broadcast_lobby_state()
    
    def _send_to_client(self, client_socket: socket.socket, message: dict):
        """Envía un mensaje a un cliente específico"""
        try:
            data = json.dumps(message).encode('utf-8')
            client_socket.send(data)
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
    
    def _broadcast_message(self, message: dict):
        """Envía un mensaje a todos los clientes conectados"""
        with self.client_lock:
            for client in list(self.clients.values()):
                try:
                    self._send_to_client(client.socket, message)
                except:
                    pass
    
    def _broadcast_lobby_state(self):
        """Envía el estado actual del lobby a todos los clientes"""
        players = []
        
        with self.client_lock:
            for client in self.clients.values():
                if client.player_id is not None:
                    players.append({
                        'player_id': client.player_id,
                        'username': client.username,
                        'ready': client.ready
                    })
        
        message = {
            'type': 'lobby_state',
            'players': players,
            'game_state': self.game_state,
            'can_start': len(players) >= 2 and all(p['ready'] for p in players)
        }
        
        self._broadcast_message(message)
    
    def _broadcast_game_state(self, game_state: dict):
        """Envía el estado del juego a todos los clientes"""
        message = {
            'type': 'game_state',
            'state': game_state
        }
        
        self._broadcast_message(message)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Servidor de Tank Attack Multijugador')
    parser.add_argument('--host', default='0.0.0.0', help='Dirección IP del servidor')
    parser.add_argument('--port', type=int, default=8888, help='Puerto del servidor')
    parser.add_argument('--max-players', type=int, default=4, help='Máximo número de jugadores')
    
    args = parser.parse_args()
    
    server = GameServer(host=args.host, port=args.port)
    server.max_players = args.max_players
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrumpido por el usuario")
    finally:
        server.stop()