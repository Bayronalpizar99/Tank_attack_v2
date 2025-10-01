# backend/modelos.py
import uuid
import random
import pygame
from constantes import (
    TIPO_BALA, TIPO_JUGADOR, TIPO_JUGADOR_1, TIPO_JUGADOR_2, TIPO_JUGADOR_3, TIPO_JUGADOR_4,
    TIPO_ENEMIGO_NORMAL, TIPO_ENEMIGO_RAPIDO, TIPO_ENEMIGO_FUERTE, TIPO_MURO,
    VIDAS_INICIALES_JUGADOR, CADENCIA_DISPARO_JUGADOR, RIGHT, STAY, TILE_SIZE,
    DIRECTIONS,
)


# Carga de sonidos globales para tanques (si se decide mantener aquí)
_tank_engine_idle_sound = None
_tank_engine_moving_sound = None

if pygame.mixer.get_init():
    try:
        pass 
    except pygame.error as e:
        pass


class GameObjectModel:
    def __init__(self, x_tile, y_tile, tipo_objeto, id_obj=None):
        self.id = id_obj if id_obj else uuid.uuid4()
        self.x_tile = x_tile
        self.y_tile = y_tile
        self.tipo_objeto = tipo_objeto
        self.activo = True

    def __repr__(self):
        return f"<{self.tipo_objeto} ({self.id}) en ({self.x_tile},{self.y_tile})>"

class TanqueModel(GameObjectModel): 
    def __init__(self, x_tile, y_tile, tipo_tanque, vidas_iniciales, velocidad_base_factor, cadencia_disparo):
        super().__init__(x_tile, y_tile, tipo_tanque)
        self.vidas = vidas_iniciales
        self.velocidad_base_factor = velocidad_base_factor
        self.cadencia_disparo = cadencia_disparo
        self.tiempo_ultimo_disparo = 0
        self.direccion_actual = RIGHT 
        self.accion_actual = STAY 
        self.moviendose_este_tick = False

    def intentar_mover(self, direccion_vector_tile):
        self.accion_actual = direccion_vector_tile 
        if direccion_vector_tile != STAY: 
            self.direccion_actual = direccion_vector_tile 

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
    def __init__(self, x_tile, y_tile, player_id=1):
        # Mapear player_id a tipo de jugador
        player_types = {
            1: TIPO_JUGADOR_1,
            2: TIPO_JUGADOR_2, 
            3: TIPO_JUGADOR_3,
            4: TIPO_JUGADOR_4
        }
        
        tipo_jugador = player_types.get(player_id, TIPO_JUGADOR)
        
        super().__init__(
            x_tile,
            y_tile,
            tipo_jugador, 
            VIDAS_INICIALES_JUGADOR, 
            velocidad_base_factor=0.1,
            cadencia_disparo=CADENCIA_DISPARO_JUGADOR 
        )
        self.player_id = player_id
        self.vidas_por_nivel = VIDAS_INICIALES_JUGADOR 

        self.ticks_por_movimiento_jugador = 10
        self._ticks_hasta_proximo_movimiento_jugador = 0
        self.detenido_por_usuario = False
        self.last_known_tile_pos = (x_tile, y_tile)


    def reset_para_nuevo_nivel(self, x_tile, y_tile): 
        self.x_tile = x_tile 
        self.y_tile = y_tile 
        self.vidas = self.vidas_por_nivel 
        self.activo = True 
        self.direccion_actual = RIGHT 
        self.accion_actual = STAY 
        self._ticks_hasta_proximo_movimiento_jugador = 0
        self.detenido_por_usuario = False
        self.last_known_tile_pos = (x_tile, y_tile)


    def puede_moverse_este_tick_jugador(self): 
        return self._ticks_hasta_proximo_movimiento_jugador <= 0

    def registrar_movimiento_exitoso_jugador(self): 
        self._ticks_hasta_proximo_movimiento_jugador = self.ticks_por_movimiento_jugador

    def actualizar_contador_movimiento_jugador(self): 
        if self._ticks_hasta_proximo_movimiento_jugador > 0:
            self._ticks_hasta_proximo_movimiento_jugador -= 1
        if self.last_known_tile_pos != (self.x_tile, self.y_tile): 
            self.last_known_tile_pos = (self.x_tile, self.y_tile)


class TanqueEnemigoModel(TanqueModel):
    TIPOS_CONFIG = {
        TIPO_ENEMIGO_NORMAL: {"vidas": 2, "velocidad_factor": 0.05, "cadencia": 1200, "rango_vision": 7, "rango_disparo": 5, "ticks_por_movimiento": 20, "recalc_path_interval": 55}, 
        TIPO_ENEMIGO_RAPIDO: {"vidas": 3, "velocidad_factor": 0.08, "cadencia": 800, "rango_vision": 9, "rango_disparo": 6, "ticks_por_movimiento": 12, "recalc_path_interval": 85}, 
        TIPO_ENEMIGO_FUERTE: {"vidas": 5, "velocidad_factor": 0.04, "cadencia": 1500, "rango_vision": 6, "rango_disparo": 4, "ticks_por_movimiento": 25, "recalc_path_interval": 70}, 
    }
    # Variación para el intervalo de recálculo, +/- este valor
    RECALC_INTERVAL_JITTER = 5 # Por ejemplo, 5 ticks de variación
    MIN_RECALC_INTERVAL = 20 # Mínimo intervalo de recálculo para evitar que sea demasiado frecuente

    def __init__(self, x_tile, y_tile, tipo_enemigo, objetivo_primario_id_asignado=None):
        config = self.TIPOS_CONFIG[tipo_enemigo]
        super().__init__(x_tile, y_tile, tipo_enemigo,
                         config["vidas"], config["velocidad_factor"], config["cadencia"])
        self.objetivo_primario_id_asignado = objetivo_primario_id_asignado 
        self.rango_vision = config["rango_vision"]
        self.rango_disparo = config["rango_disparo"] 
        self.ruta_actual_tiles = [] 

        self.ticks_para_mover_config = config["ticks_por_movimiento"] 
        self._ticks_hasta_proximo_movimiento = 0

        self.frecuencia_decision_patrulla = random.randint(45, 90)
        self.ticks_para_nueva_decision_patrulla = random.randint(0, self.frecuencia_decision_patrulla // 2)
        self.direccion_patrulla_actual = STAY 

        self.fue_destruido_visual = False 
        self.tiempo_destruccion_visual = 0 
        self.duracion_explosion_visual = 300 

        self.base_recalc_interval = config["recalc_path_interval"] 
        
        # Inicializar el contador con un valor aleatorio hasta el intervalo base para escalonar la primera vez
        # y aplicamos un pequeño jitter para la primera vez también.
        initial_interval_with_jitter = self.base_recalc_interval + random.randint(-self.RECALC_INTERVAL_JITTER, self.RECALC_INTERVAL_JITTER)
        initial_interval_with_jitter = max(self.MIN_RECALC_INTERVAL, initial_interval_with_jitter)

        if initial_interval_with_jitter > 0:
            self.ticks_para_recalcular_ruta = random.randint(1, initial_interval_with_jitter)
        else: 
            self.ticks_para_recalcular_ruta = 0 # Recalcular inmediatamente si el cálculo da <=0
            
        self.ultima_pos_jugador_vista_para_ruta = None 

    def debe_recalcular_ruta(self, pos_jugador_actual_tile, jugador_se_movio_desde_ultima_ruta):
        self.ticks_para_recalcular_ruta -= 1
        if not self.ruta_actual_tiles: 
            return True
        if self.ticks_para_recalcular_ruta <= 0: 
            return True
        if jugador_se_movio_desde_ultima_ruta and self.pos_distancia_sq(pos_jugador_actual_tile) <= self.rango_vision**2 : 
            return True
        return False

    def reset_timer_recalcular_ruta(self):
        # Al resetear, usar el intervalo base configurado MÁS un jitter aleatorio
        # para desincronizar tanques del mismo tipo a lo largo del tiempo.
        next_interval = self.base_recalc_interval + random.randint(-self.RECALC_INTERVAL_JITTER, self.RECALC_INTERVAL_JITTER)
        # Asegurarse de que el intervalo no sea demasiado corto
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


    def puede_moverse_este_tick(self): 
        return self._ticks_hasta_proximo_movimiento <= 0

    def registrar_movimiento_exitoso(self): 
        self._ticks_hasta_proximo_movimiento = self.ticks_para_mover_config

    def actualizar_contador_movimiento(self): 
        if self._ticks_hasta_proximo_movimiento > 0:
            self._ticks_hasta_proximo_movimiento -= 1

class BalaModel(GameObjectModel):
    def __init__(self, x_tile, y_tile, direccion_vector, propietario_id, tipo_propietario):
        super().__init__(x_tile, y_tile, TIPO_BALA) 
        self.direccion_vector = direccion_vector
        self.propietario_id = propietario_id
        self.tipo_propietario = tipo_propietario
        self.distancia_recorrida_tick = 0 

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