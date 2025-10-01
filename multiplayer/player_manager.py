# multiplayer/player_manager.py
from constantes import (
    TIPO_JUGADOR, UP, DOWN, LEFT, RIGHT, STAY,
    GRID_WIDTH, GRID_HEIGHT
)
from backend.modelos import TanqueJugadorModel

class Player:
    def __init__(self, player_id, name, color, controls):
        self.player_id = player_id
        self.name = name
        self.color = color  # Color del tanque del jugador
        self.controls = controls  # Diccionario con las teclas de control
        self.tank_id = None  # ID del tanque en el motor de juego
        self.score = 0
        self.is_active = True
        
class PlayerManager:
    def __init__(self):
        self.players = {}
        self.max_players = 4
        
        # Configuraciones predefinidas de controles para cada jugador
        self.default_controls = {
            1: {
                'up': 'w', 'down': 's', 'left': 'a', 'right': 'd', 
                'shoot': 'space', 'stop': 'x'
            },
            2: {
                'up': 'i', 'down': 'k', 'left': 'j', 'right': 'l',
                'shoot': 'rshift', 'stop': 'rctrl'
            },
            3: {
                'up': 't', 'down': 'g', 'left': 'f', 'right': 'h',
                'shoot': 'r', 'stop': 'y'
            },
            4: {
                'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
                'shoot': 'return', 'stop': 'ralt'
            }
        }
        
        # Colores para cada jugador
        self.player_colors = {
            1: (0, 255, 0),    # Verde
            2: (0, 0, 255),    # Azul  
            3: (255, 255, 0),  # Amarillo
            4: (255, 0, 255)   # Magenta
        }
        
        # Posiciones de spawn para cada jugador
        self.spawn_positions = {
            1: (1, 1),
            2: (GRID_WIDTH - 2, 1),
            3: (1, GRID_HEIGHT - 2),
            4: (GRID_WIDTH - 2, GRID_HEIGHT - 2)
        }
    
    def add_player(self, player_id, name=None):
        """Añade un nuevo jugador si hay espacio"""
        if len(self.players) >= self.max_players:
            return False
            
        if player_id in self.players:
            return False
            
        if name is None:
            name = f"Jugador {player_id}"
            
        controls = self.default_controls.get(player_id, self.default_controls[1])
        color = self.player_colors.get(player_id, (255, 255, 255))
        
        player = Player(player_id, name, color, controls)
        self.players[player_id] = player
        return True
    
    def remove_player(self, player_id):
        """Elimina un jugador"""
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False
    
    def get_player(self, player_id):
        """Obtiene un jugador por ID"""
        return self.players.get(player_id)
    
    def get_all_players(self):
        """Obtiene todos los jugadores"""
        return list(self.players.values())
    
    def get_active_players(self):
        """Obtiene solo los jugadores activos"""
        return [p for p in self.players.values() if p.is_active]
    
    def get_spawn_position(self, player_id):
        """Obtiene la posición de spawn para un jugador"""
        return self.spawn_positions.get(player_id, (1, 1))
    
    def process_input(self, keys_pressed, player_id):
        """Procesa la entrada de un jugador específico y devuelve las acciones"""
        player = self.get_player(player_id)
        if not player or not player.is_active:
            return {}
            
        actions = {}
        controls = player.controls
        
        # Mapeo de teclas a códigos pygame
        key_map = {
            'w': 119, 's': 115, 'a': 97, 'd': 100,
            'i': 105, 'k': 107, 'j': 106, 'l': 108,
            't': 116, 'g': 103, 'f': 102, 'h': 104,
            'r': 114, 'y': 121,
            'up': 273, 'down': 274, 'left': 276, 'right': 275,
            'space': 32, 'rshift': 303, 'return': 13,
            'x': 120, 'rctrl': 305, 'ralt': 307
        }
        
        # Comprobar movimiento
        direction = None
        if keys_pressed[key_map.get(controls['up'], 0)]:
            direction = UP
        elif keys_pressed[key_map.get(controls['down'], 0)]:
            direction = DOWN
        elif keys_pressed[key_map.get(controls['left'], 0)]:
            direction = LEFT
        elif keys_pressed[key_map.get(controls['right'], 0)]:
            direction = RIGHT
            
        if direction:
            actions['mover'] = direction
            
        # Comprobar disparo
        if keys_pressed[key_map.get(controls['shoot'], 0)]:
            actions['disparar'] = True
            
        # Comprobar parada
        if keys_pressed[key_map.get(controls['stop'], 0)]:
            actions['detenerse'] = True
            
        return actions
    
    def reset_all_players(self):
        """Resetea el estado de todos los jugadores"""
        for player in self.players.values():
            player.tank_id = None
            player.is_active = True
            player.score = 0