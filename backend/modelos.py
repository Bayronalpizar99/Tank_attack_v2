# backend/modelos.py
import uuid
import random
import pygame # Necesario para pygame.time.get_ticks()
import math
from constantes import (
    TIPO_BALA, TIPO_JUGADOR, TIPO_ENEMIGO_NORMAL, TIPO_ENEMIGO_RAPIDO, TIPO_ENEMIGO_FUERTE, TIPO_MURO,
    VIDAS_INICIALES_JUGADOR, CADENCIA_DISPARO_JUGADOR, RIGHT, STAY, TILE_SIZE,
    DIRECTIONS, VELOCIDAD_JUGADOR_PX_S, VELOCIDAD_ENEMIGO_NORMAL_PX_S,
    VELOCIDAD_ENEMIGO_RAPIDO_PX_S, VELOCIDAD_ENEMIGO_FUERTE_PX_S
)

class GameObjectModel:
    def __init__(self, x_tile, y_tile, tipo_objeto, id_obj=None):
        self.id = id_obj if id_obj else uuid.uuid4()
        self.tipo_objeto = tipo_objeto
        self.activo = True
        
        # Coordenadas lógicas (en la cuadrícula)
        self.x_tile = x_tile
        self.y_tile = y_tile
        
        # Coordenadas visuales (en píxeles) para movimiento fluido
        self.pixel_x = float(x_tile * TILE_SIZE)
        self.pixel_y = float(y_tile * TILE_SIZE)

    def __repr__(self):
        return f"<{self.tipo_objeto} ({self.id}) en ({self.x_tile},{self.y_tile})>"

class TanqueModel(GameObjectModel): 
    def __init__(self, x_tile, y_tile, tipo_tanque, vidas_iniciales, velocidad_px_s, cadencia_disparo):
        super().__init__(x_tile, y_tile, tipo_tanque)
        self.vidas = vidas_iniciales
        self.velocidad_px_s = velocidad_px_s
        self.cadencia_disparo = cadencia_disparo
        self.tiempo_ultimo_disparo = 0
        self.direccion_actual = RIGHT 
        self.accion_actual = STAY 
        
        # Estado de movimiento
        self.is_moving = False
        self.target_pixel_x = self.pixel_x
        self.target_pixel_y = self.pixel_y

    def intentar_mover(self, direccion_vector_tile):
        if self.is_moving: # No se puede iniciar un nuevo movimiento hasta que termine el actual
            return

        self.accion_actual = direccion_vector_tile 
        if direccion_vector_tile != STAY: 
            self.direccion_actual = direccion_vector_tile 

    def iniciar_movimiento_a_casilla(self, target_x_tile, target_y_tile):
        self.is_moving = True
        self.target_pixel_x = float(target_x_tile * TILE_SIZE)
        self.target_pixel_y = float(target_y_tile * TILE_SIZE)
        
    def update_posicion_pixel(self, tiempo_delta_s):
        if not self.is_moving:
            return

        distancia_movimiento = self.velocidad_px_s * tiempo_delta_s
        
        dx = self.target_pixel_x - self.pixel_x
        dy = self.target_pixel_y - self.pixel_y
        
        distancia_al_objetivo = math.sqrt(dx*dx + dy*dy)

        if distancia_al_objetivo <= distancia_movimiento:
            # Llegó al destino
            self.pixel_x = self.target_pixel_x
            self.pixel_y = self.target_pixel_y
            self.x_tile = int(self.target_pixel_x // TILE_SIZE)
            self.y_tile = int(self.target_pixel_y // TILE_SIZE)
            self.is_moving = False
        else:
            # Moverse hacia el destino
            self.pixel_x += (dx / distancia_al_objetivo) * distancia_movimiento
            self.pixel_y += (dy / distancia_al_objetivo) * distancia_movimiento

    def puede_disparar(self, tiempo_actual_ms):
        return (tiempo_actual_ms - self.tiempo_ultimo_disparo) >= self.cadencia_disparo 

    def registrar_disparo(self, tiempo_actual_ms):
        self.tiempo_ultimo_disparo = tiempo_actual_ms 

    def recibir_impacto(self):
        if self.activo: 
            self.vidas -= 1
            if self.vidas <= 0:
                self.activo = False 
                print(f"{self.tipo_objeto} {self.id} destruido (vidas <= 0).")
                return True 
            print(f"{self.tipo_objeto} {self.id} golpeado. Vidas: {self.vidas}")
        return False 

class TanqueJugadorModel(TanqueModel):
    def __init__(self, x_tile, y_tile):
        super().__init__(
            x_tile,
            y_tile,
            TIPO_JUGADOR, 
            VIDAS_INICIALES_JUGADOR, 
            velocidad_px_s=VELOCIDAD_JUGADOR_PX_S,
            cadencia_disparo=CADENCIA_DISPARO_JUGADOR 
        )
        self.vidas_por_nivel = VIDAS_INICIALES_JUGADOR 
        self.detenido_por_usuario = False
        self.last_known_tile_pos = (x_tile, y_tile)

    def reset_para_nuevo_nivel(self, x_tile, y_tile): 
        self.x_tile = x_tile 
        self.y_tile = y_tile 
        self.pixel_x = float(x_tile * TILE_SIZE)
        self.pixel_y = float(y_tile * TILE_SIZE)
        self.target_pixel_x = self.pixel_x
        self.target_pixel_y = self.pixel_y
        self.is_moving = False
        
        self.vidas = self.vidas_por_nivel 
        self.activo = True 
        self.direccion_actual = RIGHT 
        self.accion_actual = STAY 
        self.detenido_por_usuario = False
        self.last_known_tile_pos = (x_tile, y_tile)

    def actualizar_contador_movimiento_jugador(self): 
        if self.last_known_tile_pos != (self.x_tile, self.y_tile): 
            self.last_known_tile_pos = (self.x_tile, self.y_tile)

class TanqueEnemigoModel(TanqueModel):
    TIPOS_CONFIG = {
        TIPO_ENEMIGO_NORMAL: {"vidas": 2, "velocidad_px_s": VELOCIDAD_ENEMIGO_NORMAL_PX_S, "cadencia": 1200, "rango_vision": 7, "rango_disparo": 5, "recalc_path_interval": 55}, 
        TIPO_ENEMIGO_RAPIDO: {"vidas": 3, "velocidad_px_s": VELOCIDAD_ENEMIGO_RAPIDO_PX_S, "cadencia": 800, "rango_vision": 9, "rango_disparo": 6, "recalc_path_interval": 85}, 
        TIPO_ENEMIGO_FUERTE: {"vidas": 5, "velocidad_px_s": VELOCIDAD_ENEMIGO_FUERTE_PX_S, "cadencia": 1500, "rango_vision": 6, "rango_disparo": 4, "recalc_path_interval": 70}, 
    }
    RECALC_INTERVAL_JITTER = 5
    MIN_RECALC_INTERVAL = 20

    def __init__(self, x_tile, y_tile, tipo_enemigo, objetivo_primario_id_asignado=None):
        config = self.TIPOS_CONFIG[tipo_enemigo]
        super().__init__(x_tile, y_tile, tipo_enemigo,
                         config["vidas"], config["velocidad_px_s"], config["cadencia"])
        self.objetivo_primario_id_asignado = objetivo_primario_id_asignado 
        self.rango_vision = config["rango_vision"]
        self.rango_disparo = config["rango_disparo"] 
        self.ruta_actual_tiles = [] 

        self.frecuencia_decision_patrulla = random.randint(45, 90)
        self.ticks_para_nueva_decision_patrulla = random.randint(0, self.frecuencia_decision_patrulla // 2)
        self.direccion_patrulla_actual = STAY 

        self.fue_destruido_visual = False 
        self.tiempo_destruccion_visual = 0 
        self.duracion_explosion_visual = 300 

        self.base_recalc_interval = config["recalc_path_interval"] 
        
        initial_interval_with_jitter = self.base_recalc_interval + random.randint(-self.RECALC_INTERVAL_JITTER, self.RECALC_INTERVAL_JITTER)
        initial_interval_with_jitter = max(self.MIN_RECALC_INTERVAL, initial_interval_with_jitter)

        if initial_interval_with_jitter > 0:
            self.ticks_para_recalcular_ruta = random.randint(1, initial_interval_with_jitter)
        else: 
            self.ticks_para_recalcular_ruta = 0
            
        self.ultima_pos_jugador_vista_para_ruta = None 

    def debe_recalcular_ruta(self, pos_jugador_actual_tile, jugador_se_movio_desde_ultima_ruta):
        # No hay ruta actual, necesita calcular una
        if not self.ruta_actual_tiles: 
            return True
        # Timer expiró, recalcular periódicamente
        if self.ticks_para_recalcular_ruta <= 0: 
            return True
        # MODIFICADO: Siempre perseguir al jugador cuando se mueve, sin importar la distancia
        if jugador_se_movio_desde_ultima_ruta: 
            return True
        return False

    def reset_timer_recalcular_ruta(self):
        next_interval = self.base_recalc_interval + random.randint(-self.RECALC_INTERVAL_JITTER, self.RECALC_INTERVAL_JITTER)
        self.ticks_para_recalcular_ruta = max(self.MIN_RECALC_INTERVAL, next_interval)
    def pos_distancia_sq(self, otra_pos_tile): 
        return (self.x_tile - otra_pos_tile[0])**2 + (self.y_tile - otra_pos_tile[1])**2

    def recibir_impacto(self):
        if not self.activo: 
            return False 

        self.vidas -= 1
        if self.vidas <= 0:
            if self.activo: 
                print(f"{self.tipo_objeto} {self.id} destruido (vidas <= 0).")
                self.activo = False 
                self.fue_destruido_visual = True 
                self.tiempo_destruccion_visual = pygame.time.get_ticks() 
            return True 

        print(f"{self.tipo_objeto} {self.id} golpeado. Vidas: {self.vidas}")
        return False 

class BalaModel(GameObjectModel):
    def __init__(self, start_pixel_x, start_pixel_y, direccion_vector, propietario_id, tipo_propietario):
        # La bala se crea en una posición de píxeles, no de tile
        start_tile_x = int(start_pixel_x / TILE_SIZE)
        start_tile_y = int(start_pixel_y / TILE_SIZE)
        
        super().__init__(start_tile_x, start_tile_y, TIPO_BALA) 
        
        self.pixel_x = start_pixel_x
        self.pixel_y = start_pixel_y
        self.direccion_vector = direccion_vector
        self.propietario_id = propietario_id
        self.tipo_propietario = tipo_propietario

class MuroModel(GameObjectModel):
    def __init__(self, x_tile, y_tile):
        super().__init__(x_tile, y_tile, TIPO_MURO) 

class ObjetivoPrimarioModel(GameObjectModel):
    def __init__(self, x_tile, y_tile, tipo_objetivo):
        super().__init__(x_tile, y_tile, tipo_objetivo)

    def ser_destruido(self): 
        if self.activo: 
            print(f"Objetivo {self.tipo_objeto} {self.id} en ({self.x_tile},{self.y_tile}) destruido!") 
            self.activo = False 
            return True
        return False