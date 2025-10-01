# multiplayer/motor_multijugador.py
import random
import pygame
import os
import math
import copy

from constantes import (
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, MAX_NIVELES,
    TIPO_JUGADOR, TIPO_JUGADOR_1, TIPO_JUGADOR_2, TIPO_JUGADOR_3, TIPO_JUGADOR_4,
    TIPO_ENEMIGO_NORMAL, TIPO_ENEMIGO_RAPIDO, TIPO_ENEMIGO_FUERTE,
    TIPO_BALA, TIPO_MURO,
    DIRECTIONS, RIGHT, LEFT, UP, DOWN,
    VELOCIDAD_BALA, STAY,
    TIPO_OBJETIVO1, TIPO_OBJETIVO2,
    GAME_OVER, VICTORIA_FINAL, NIVEL_COMPLETADO, JUGANDO,
    EDITOR_CHAR_TO_TYPE, EDITOR_CHAR_JUGADOR, EDITOR_NIVELES_PATH, EDITOR_CHAR_VACIO,
    DFS_ACTIVATION_RANGE_SQ, OBJECTIVE_PATROL_MAX_DISTANCE_SQ, OBJECTIVE_PATROL_MIN_DISTANCE_SQ
)

from backend.modelos import (
    TanqueModel, TanqueJugadorModel, TanqueEnemigoModel,
    BalaModel, MuroModel, ObjetivoPrimarioModel
)

from backend.motor_juego import MotorJuego

class MotorMultijugador(MotorJuego):
    def __init__(self, player_manager, player_shoot_sound=None, player_final_destruction_sound=None):
        super().__init__(player_shoot_sound, player_final_destruction_sound)
        self.player_manager = player_manager
        self.jugadores_ids = {}  # {player_id: tank_object_id}
        self.jugadores_activos = set()
        self.modo_cooperativo = True  # True = coop vs IA, False = PvP
        
    def _limpiar_estado_nivel(self):
        super()._limpiar_estado_nivel()
        self.jugadores_ids = {}
        self.jugadores_activos = set()
        self.last_player_tile_pos_for_enemy_logic = None
        
    def _cargar_nivel_procedural_multijugador(self, numero_nivel_int):
        """Versión multijugador de la carga procedural"""
        print(f"Motor Multijugador: Cargando nivel procedural {numero_nivel_int}")
        self.es_nivel_editado_actualmente = False
        
        # Crear jugadores para todos los jugadores activos
        players = self.player_manager.get_active_players()
        if not players:
            print("Error: No hay jugadores activos")
            return False
            
        posiciones_ocupadas_temp = []
        
        # Crear tanques para cada jugador
        for player in players:
            spawn_x, spawn_y = self.player_manager.get_spawn_position(player.player_id)
            
            # Verificar que la posición de spawn esté libre
            if (spawn_x, spawn_y) in posiciones_ocupadas_temp:
                # Buscar posición alternativa cerca
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        new_x, new_y = spawn_x + dx, spawn_y + dy
                        if (0 < new_x < GRID_WIDTH - 1 and 0 < new_y < GRID_HEIGHT - 1 and 
                            (new_x, new_y) not in posiciones_ocupadas_temp):
                            spawn_x, spawn_y = new_x, new_y
                            break
                    else:
                        continue
                    break
                        
            jugador = TanqueJugadorModel(spawn_x, spawn_y, player.player_id)
            self._agregar_objeto(jugador)
            self.jugadores_ids[player.player_id] = jugador.id
            self.jugadores_activos.add(player.player_id)
            player.tank_id = jugador.id
            player.is_active = True
            posiciones_ocupadas_temp.append((spawn_x, spawn_y))
            
        # Usar la posición del primer jugador para la lógica de enemigos
        if self.jugadores_activos:
            first_player_id = next(iter(self.jugadores_activos))
            first_tank_id = self.jugadores_ids[first_player_id]
            first_tank = self.objetos_del_juego[first_tank_id]
            self.last_player_tile_pos_for_enemy_logic = (first_tank.x_tile, first_tank.y_tile)
        
        # Crear bordes (muros)
        for x_borde in range(GRID_WIDTH):
            if (x_borde, 0) not in posiciones_ocupadas_temp: 
                self._agregar_objeto(MuroModel(x_borde, 0))
                posiciones_ocupadas_temp.append((x_borde, 0))
            if (x_borde, GRID_HEIGHT - 1) not in posiciones_ocupadas_temp: 
                self._agregar_objeto(MuroModel(x_borde, GRID_HEIGHT - 1))
                posiciones_ocupadas_temp.append((x_borde, GRID_HEIGHT - 1))
                
        for y_borde in range(1, GRID_HEIGHT - 1):
            if (0, y_borde) not in posiciones_ocupadas_temp: 
                self._agregar_objeto(MuroModel(0, y_borde))
                posiciones_ocupadas_temp.append((0, y_borde))
            if (GRID_WIDTH - 1, y_borde) not in posiciones_ocupadas_temp: 
                self._agregar_objeto(MuroModel(GRID_WIDTH - 1, y_borde))
                posiciones_ocupadas_temp.append((GRID_WIDTH - 1, y_borde))
        
        # Muros internos (ajustados para más jugadores)
        num_jugadores = len(players)
        base_muros = 15
        muros_adicionales = (num_jugadores - 1) * 5  # Más muros con más jugadores
        num_muros_internos = random.randint(base_muros, base_muros + muros_adicionales)
        
        for _ in range(num_muros_internos):
            intentos_muro = 0
            while intentos_muro < 50:
                x, y = random.randint(1, GRID_WIDTH - 2), random.randint(1, GRID_HEIGHT - 2)
                if (x, y) not in posiciones_ocupadas_temp:
                    self._agregar_objeto(MuroModel(x, y))
                    posiciones_ocupadas_temp.append((x, y))
                    break
                intentos_muro += 1
        
        # Crear objetivos (más objetivos con más jugadores)
        config_nivel_obj = self.config_objetivos_por_nivel.get(numero_nivel_int, {"cantidad": 1, "tipos": [TIPO_OBJETIVO1]})
        objetivos_base = config_nivel_obj["cantidad"]
        objetivos_adicionales = (num_jugadores - 1) * 1  # Un objetivo extra por jugador adicional
        total_objetivos = objetivos_base + objetivos_adicionales
        
        ids_objetivos_creados = []
        for _ in range(total_objetivos):
            intentos_pos = 0
            while intentos_pos < 100:
                x, y = random.randint(1, GRID_WIDTH - 2), random.randint(1, GRID_HEIGHT - 2)
                if (x, y) not in posiciones_ocupadas_temp:
                    tipo_obj_azar = random.choice(config_nivel_obj["tipos"])
                    objetivo = ObjetivoPrimarioModel(x, y, tipo_obj_azar)
                    self._agregar_objeto(objetivo)
                    ids_objetivos_creados.append(objetivo.id)
                    posiciones_ocupadas_temp.append((x, y))
                    break
                intentos_pos += 1
        
        # Crear enemigos (más enemigos con más jugadores)
        tipos_enemigos_disp = [TIPO_ENEMIGO_NORMAL, TIPO_ENEMIGO_RAPIDO, TIPO_ENEMIGO_FUERTE]
        enemigos_por_objetivo = self.config_enemigos_por_objetivo + (num_jugadores - 1) // 2
        
        for obj_id_objetivo in ids_objetivos_creados:
            objetivo_a_defender = self.objetos_del_juego.get(obj_id_objetivo)
            if not objetivo_a_defender: 
                continue
                
            for _ in range(enemigos_por_objetivo):
                intentos_pos = 0
                while intentos_pos < 100:
                    ox, oy = objetivo_a_defender.x_tile, objetivo_a_defender.y_tile
                    dist_spawn = random.randint(1, 3)
                    angle_spawn = random.uniform(0, 2 * math.pi)
                    dx = int(round(dist_spawn * math.cos(angle_spawn)))
                    dy = int(round(dist_spawn * math.sin(angle_spawn)))
                    x, y = ox + dx, oy + dy
                    
                    if (0 < x < GRID_WIDTH - 1 and 0 < y < GRID_HEIGHT - 1 and 
                        (x, y) not in posiciones_ocupadas_temp):
                        tipo_enemigo_azar = random.choice(tipos_enemigos_disp)
                        enemigo = TanqueEnemigoModel(x, y, tipo_enemigo_azar, obj_id_objetivo)
                        self._agregar_objeto(enemigo)
                        posiciones_ocupadas_temp.append((x, y))
                        break
                    intentos_pos += 1
        
        return True
    
    def cargar_nivel(self, nivel_id_o_ruta):
        """Override para manejar multijugador"""
        self._limpiar_estado_nivel()
        self.nivel_actual_numero = nivel_id_o_ruta
        
        exito_carga = False
        if isinstance(nivel_id_o_ruta, int):
            if nivel_id_o_ruta == 0:
                return False
            exito_carga = self._cargar_nivel_procedural_multijugador(nivel_id_o_ruta)
        elif isinstance(nivel_id_o_ruta, str):
            # Para niveles editados, usar la lógica original pero con múltiples jugadores
            if not os.path.isabs(nivel_id_o_ruta) and not nivel_id_o_ruta.startswith(EDITOR_NIVELES_PATH):
                if not nivel_id_o_ruta.endswith(".txt"): 
                    nivel_id_o_ruta += ".txt"
                nivel_id_o_ruta = os.path.join(EDITOR_NIVELES_PATH, nivel_id_o_ruta)
            
            exito_carga = self._cargar_nivel_desde_archivo_multijugador(nivel_id_o_ruta)
            if exito_carga: 
                self.nivel_actual_numero = nivel_id_o_ruta
        else:
            print(f"Error: Identificador de nivel desconocido: {nivel_id_o_ruta}")
            return False

        if exito_carga:
            # Actualizar posición para lógica de enemigos
            if self.jugadores_activos:
                first_player_id = next(iter(self.jugadores_activos))
                if first_player_id in self.jugadores_ids:
                    tank_id = self.jugadores_ids[first_player_id]
                    tank = self.objetos_del_juego.get(tank_id)
                    if tank:
                        self.last_player_tile_pos_for_enemy_logic = (tank.x_tile, tank.y_tile)
            return True
        return False
    
    def _cargar_nivel_desde_archivo_multijugador(self, ruta_archivo):
        """Versión multijugador de carga desde archivo"""
        print(f"Motor Multijugador: Cargando nivel desde archivo {ruta_archivo}")
        self.es_nivel_editado_actualmente = True
        
        try:
            if not os.path.exists(ruta_archivo):
                print(f"Error: Archivo de nivel no encontrado en {ruta_archivo}")
                return False

            with open(ruta_archivo, 'r') as f:
                lines = f.readlines()
            
            # Solo usar la primera posición de jugador encontrada en el archivo
            posicion_jugador_archivo = None
            objetos_para_agregar_temp = []
            enemigos_temp_con_objetivo = []

            for r, line in enumerate(lines):
                if r >= GRID_HEIGHT: 
                    continue
                for c, char_tile in enumerate(line.strip()):
                    if c >= GRID_WIDTH: 
                        continue
                    
                    tipo_objeto_modelo = EDITOR_CHAR_TO_TYPE.get(char_tile)
                    if tipo_objeto_modelo is None and char_tile != EDITOR_CHAR_VACIO:
                        continue
                    
                    if tipo_objeto_modelo == TIPO_JUGADOR:
                        if not posicion_jugador_archivo:
                            posicion_jugador_archivo = (c, r)
                    elif tipo_objeto_modelo == TIPO_MURO:
                        objetos_para_agregar_temp.append(MuroModel(c, r))
                    elif tipo_objeto_modelo == TIPO_ENEMIGO_NORMAL:
                        enemigos_temp_con_objetivo.append((TanqueEnemigoModel(c, r, TIPO_ENEMIGO_NORMAL), None))
                    elif tipo_objeto_modelo == TIPO_ENEMIGO_RAPIDO:
                        enemigos_temp_con_objetivo.append((TanqueEnemigoModel(c, r, TIPO_ENEMIGO_RAPIDO), None))
                    elif tipo_objeto_modelo == TIPO_ENEMIGO_FUERTE:
                        enemigos_temp_con_objetivo.append((TanqueEnemigoModel(c, r, TIPO_ENEMIGO_FUERTE), None))
                    elif tipo_objeto_modelo == TIPO_OBJETIVO1:
                        objetos_para_agregar_temp.append(ObjetivoPrimarioModel(c, r, TIPO_OBJETIVO1))
                    elif tipo_objeto_modelo == TIPO_OBJETIVO2:
                        objetos_para_agregar_temp.append(ObjetivoPrimarioModel(c, r, TIPO_OBJETIVO2))
            
            # Crear jugadores
            players = self.player_manager.get_active_players()
            if not players:
                return False
                
            for i, player in enumerate(players):
                if i == 0 and posicion_jugador_archivo:
                    # Primer jugador usa la posición del archivo
                    spawn_x, spawn_y = posicion_jugador_archivo
                else:
                    # Otros jugadores usan posiciones predefinidas
                    spawn_x, spawn_y = self.player_manager.get_spawn_position(player.player_id)
                
                jugador = TanqueJugadorModel(spawn_x, spawn_y, player.player_id)
                self._agregar_objeto(jugador)
                self.jugadores_ids[player.player_id] = jugador.id
                self.jugadores_activos.add(player.player_id)
                player.tank_id = jugador.id
                player.is_active = True
            
            # Agregar otros objetos
            for obj_modelo in objetos_para_agregar_temp:
                self._agregar_objeto(obj_modelo)
            
            # Asignar objetivos a enemigos
            objetivos_en_mapa = [obj for obj in self.objetos_del_juego.values() if isinstance(obj, ObjetivoPrimarioModel)]
            
            for enemigo_model, _ in enemigos_temp_con_objetivo:
                if objetivos_en_mapa:
                    enemigo_model.objetivo_primario_id_asignado = random.choice(objetivos_en_mapa).id
                self._agregar_objeto(enemigo_model)
            
            return True

        except Exception as e:
            print(f"Error al cargar nivel desde archivo {ruta_archivo}: {e}")
            return False
    
    def actualizar_estado(self, acciones_todos_jugadores, tiempo_delta_ms):
        """
        Actualiza el estado del juego con acciones de múltiples jugadores
        acciones_todos_jugadores: {player_id: acciones_dict}
        """
        self.tiempo_ms_juego += tiempo_delta_ms
        self.ticks_logicos_actuales += 1
        
        # Limpiar objetos inactivos
        ids_a_quitar_definitivamente = []
        for obj_id, obj in list(self.objetos_del_juego.items()):
            if isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual:
                if pygame.time.get_ticks() - obj.tiempo_destruccion_visual > obj.duracion_explosion_visual:
                    ids_a_quitar_definitivamente.append(obj_id)
            elif not obj.activo and obj_id not in self.jugadores_ids.values():
                ids_a_quitar_definitivamente.append(obj_id)

        for obj_id in ids_a_quitar_definitivamente:
            self._quitar_objeto(obj_id)

        # Procesar cada jugador activo
        jugadores_vivos = set()
        
        for player_id in list(self.jugadores_activos):
            tank_id = self.jugadores_ids.get(player_id)
            if not tank_id:
                continue
                
            jugador = self.objetos_del_juego.get(tank_id)
            if not jugador or not jugador.activo:
                # Jugador ha muerto
                self.jugadores_activos.discard(player_id)
                player = self.player_manager.get_player(player_id)
                if player:
                    player.is_active = False
                continue
                
            jugadores_vivos.add(player_id)
            
            # Obtener acciones para este jugador
            acciones_jugador = acciones_todos_jugadores.get(player_id, {})
            
            # Procesar movimiento y acciones del jugador
            self._procesar_jugador(jugador, acciones_jugador)
        
        # Si no hay jugadores vivos, es game over
        if not jugadores_vivos:
            return GAME_OVER
            
        # Actualizar posición de referencia para enemigos (usar primer jugador vivo)
        if jugadores_vivos:
            ref_player_id = next(iter(jugadores_vivos))
            ref_tank_id = self.jugadores_ids[ref_player_id]
            ref_tank = self.objetos_del_juego[ref_tank_id]
            self.last_player_tile_pos_for_enemy_logic = (ref_tank.x_tile, ref_tank.y_tile)
        
        # Procesar enemigos (lógica similar al original)
        self._procesar_enemigos()
        
        # Procesar balas
        self._procesar_balas()
        
        # Verificar condiciones de victoria
        if self._todos_objetivos_destruidos():
            if self.es_nivel_editado_actualmente:
                return VICTORIA_FINAL
            elif isinstance(self.nivel_actual_numero, int) and self.nivel_actual_numero < MAX_NIVELES:
                return NIVEL_COMPLETADO
            else:
                return VICTORIA_FINAL
        
        return JUGANDO
    
    def _procesar_jugador(self, jugador, acciones_jugador):
        """Procesa las acciones de un jugador individual"""
        jugador.actualizar_contador_movimiento_jugador()
        jugador_puede_actuar_este_tick = jugador.puede_moverse_este_tick_jugador()

        # Procesar movimiento
        nueva_intencion_movimiento = None
        if acciones_jugador.get("detenerse"):
            jugador.detenido_por_usuario = True
            nueva_intencion_movimiento = STAY
        elif acciones_jugador.get("mover"):
            jugador.detenido_por_usuario = False
            nueva_intencion_movimiento = acciones_jugador["mover"]
        elif jugador.detenido_por_usuario:
            nueva_intencion_movimiento = STAY
        else:
            nueva_intencion_movimiento = jugador.direccion_actual
            
        jugador.intentar_mover(nueva_intencion_movimiento)

        # Procesar disparo
        if acciones_jugador.get("disparar") and jugador.puede_disparar(self.tiempo_ms_juego):
            jugador.registrar_disparo(self.tiempo_ms_juego)
            bala_x = jugador.x_tile + jugador.direccion_actual[0]
            bala_y = jugador.y_tile + jugador.direccion_actual[1]
            
            if 0 <= bala_x < GRID_WIDTH and 0 <= bala_y < GRID_HEIGHT:
                bala = BalaModel(bala_x, bala_y, jugador.direccion_actual, jugador.id, jugador.tipo_objeto)
                self._agregar_objeto(bala)
                self._resolver_colision_inmediata_bala(bala)
                
                if self.player_shoot_sound and pygame.mixer.get_init():
                    try:
                        self.player_shoot_sound.play()
                    except pygame.error as e:
                        print(f"Error al reproducir sonido de disparo: {e}")
        
        # Ejecutar movimiento si es posible
        jugador.moviendose_este_tick = False
        if jugador.accion_actual != STAY and not jugador.detenido_por_usuario:
            if jugador_puede_actuar_este_tick:
                nueva_x_j = jugador.x_tile + jugador.accion_actual[0]
                nueva_y_j = jugador.y_tile + jugador.accion_actual[1]
                
                if self._es_posicion_valida_y_libre(nueva_x_j, nueva_y_j, para_objeto_id=jugador.id):
                    self._actualizar_mapa_colisiones_objeto(jugador, agregar=False)
                    jugador.x_tile = nueva_x_j
                    jugador.y_tile = nueva_y_j
                    jugador.moviendose_este_tick = True
                    self._actualizar_mapa_colisiones_objeto(jugador, agregar=True)
                    jugador.registrar_movimiento_exitoso_jugador()
    
    def _procesar_enemigos(self):
        """Procesa la IA de los enemigos (lógica similar al motor original)"""
        tanques_enemigos_ids = [obj_id for obj_id, obj in self.objetos_del_juego.items() 
                               if isinstance(obj, TanqueEnemigoModel) and obj.activo]
        
        # Usar lógica similar al motor original
        pos_j_actual_para_enemigo = self.last_player_tile_pos_for_enemy_logic
        if not pos_j_actual_para_enemigo:
            return
            
        for tanque_id in tanques_enemigos_ids:
            tanque = self.objetos_del_juego.get(tanque_id)
            if not tanque or not tanque.activo:
                continue
            
            # Buscar el jugador más cercano para apuntar
            jugador_mas_cercano = None
            distancia_minima = float('inf')
            
            for player_id in self.jugadores_activos:
                tank_id = self.jugadores_ids.get(player_id)
                if tank_id:
                    jugador_tank = self.objetos_del_juego.get(tank_id)
                    if jugador_tank and jugador_tank.activo:
                        dist = tanque.pos_distancia_sq((jugador_tank.x_tile, jugador_tank.y_tile))
                        if dist < distancia_minima:
                            distancia_minima = dist
                            jugador_mas_cercano = jugador_tank
            
            if not jugador_mas_cercano:
                continue
                
            # Usar la lógica del motor original para movimiento y disparo
            # pero apuntando al jugador más cercano
            self._procesar_enemigo_individual(tanque, jugador_mas_cercano, pos_j_actual_para_enemigo)
    
    def _procesar_enemigo_individual(self, tanque, jugador_objetivo, pos_ref_para_ia):
        """Procesa un enemigo individual (adaptado del motor original)"""
        tanque.moviendose_este_tick = False
        accion_movimiento_definida = STAY
        usar_dfs_para_jugador = False

        distancia_al_jugador_sq = tanque.pos_distancia_sq((jugador_objetivo.x_tile, jugador_objetivo.y_tile))
        
        # Lógica de pathfinding (simplificada del original)
        if distancia_al_jugador_sq <= DFS_ACTIVATION_RANGE_SQ:
            pos_objetivo = (jugador_objetivo.x_tile, jugador_objetivo.y_tile)
            jugador_se_movio = tanque.ultima_pos_jugador_vista_para_ruta != pos_objetivo
            
            if tanque.debe_recalcular_ruta(pos_objetivo, jugador_se_movio):
                pos_e_actual = (tanque.x_tile, tanque.y_tile)
                nueva_ruta = self._encontrar_ruta_a_estrella(pos_e_actual, pos_objetivo)
                if nueva_ruta:
                    nueva_ruta.pop(0)  # Quitar posición actual
                tanque.ruta_actual_tiles = nueva_ruta if nueva_ruta else []
                tanque.reset_timer_recalcular_ruta()
                tanque.ultima_pos_jugador_vista_para_ruta = pos_objetivo

        # Seguir ruta si existe
        if tanque.ruta_actual_tiles:
            siguiente_paso_tile = tanque.ruta_actual_tiles[0]
            if (isinstance(siguiente_paso_tile, tuple) and len(siguiente_paso_tile) == 2 and
                self._es_posicion_valida_y_libre(siguiente_paso_tile[0], siguiente_paso_tile[1], 
                                               para_objeto_id=tanque.id, considerar_tanques=True)):
                usar_dfs_para_jugador = True
                dx_tile = siguiente_paso_tile[0] - tanque.x_tile
                dy_tile = siguiente_paso_tile[1] - tanque.y_tile
                
                if dx_tile > 0: accion_movimiento_definida = RIGHT
                elif dx_tile < 0: accion_movimiento_definida = LEFT
                elif dy_tile > 0: accion_movimiento_definida = DOWN
                elif dy_tile < 0: accion_movimiento_definida = UP
            else:
                tanque.ruta_actual_tiles = []

        # Lógica de patrulla si no está siguiendo al jugador
        if not usar_dfs_para_jugador:
            tanque.ticks_para_nueva_decision_patrulla -= 1
            
            if tanque.ticks_para_nueva_decision_patrulla <= 0:
                # Lógica de patrulla (simplificada)
                direcciones_validas = []
                for dir_intento in DIRECTIONS:
                    pos_intento_x = tanque.x_tile + dir_intento[0]
                    pos_intento_y = tanque.y_tile + dir_intento[1]
                    if self._es_posicion_valida_y_libre(pos_intento_x, pos_intento_y, 
                                                      para_objeto_id=tanque.id, considerar_tanques=True):
                        direcciones_validas.append(dir_intento)
                
                if direcciones_validas:
                    tanque.direccion_patrulla_actual = random.choice(direcciones_validas)
                else:
                    tanque.direccion_patrulla_actual = STAY
                    
                tanque.ticks_para_nueva_decision_patrulla = tanque.frecuencia_decision_patrulla
            
            accion_movimiento_definida = tanque.direccion_patrulla_actual

        tanque.intentar_mover(accion_movimiento_definida)

        # Lógica de disparo
        if jugador_objetivo and jugador_objetivo.activo:
            dist_sq_disp = distancia_al_jugador_sq
            if dist_sq_disp <= (tanque.rango_disparo ** 2):
                if self._linea_de_vision_libre(tanque, jugador_objetivo):
                    dist_x_abs = jugador_objetivo.x_tile - tanque.x_tile
                    dist_y_abs = jugador_objetivo.y_tile - tanque.y_tile
                    
                    if abs(dist_x_abs) > abs(dist_y_abs):
                        tanque.direccion_actual = RIGHT if dist_x_abs > 0 else LEFT
                    elif abs(dist_y_abs) > 0:
                        tanque.direccion_actual = DOWN if dist_y_abs > 0 else UP
                    
                    if tanque.puede_disparar(self.tiempo_ms_juego):
                        tanque.registrar_disparo(self.tiempo_ms_juego)
                        bala_x = tanque.x_tile + tanque.direccion_actual[0]
                        bala_y = tanque.y_tile + tanque.direccion_actual[1]
                        
                        if 0 <= bala_x < GRID_WIDTH and 0 <= bala_y < GRID_HEIGHT:
                            bala = BalaModel(bala_x, bala_y, tanque.direccion_actual, tanque.id, tanque.tipo_objeto)
                            self._agregar_objeto(bala)
                            self._resolver_colision_inmediata_bala(bala)

        # Ejecutar movimiento
        tanque.actualizar_contador_movimiento()
        if tanque.accion_actual != STAY:
            if tanque.puede_moverse_este_tick():
                nueva_x_tile = tanque.x_tile + tanque.accion_actual[0]
                nueva_y_tile = tanque.y_tile + tanque.accion_actual[1]
                
                if self._es_posicion_valida_y_libre(nueva_x_tile, nueva_y_tile, 
                                                  para_objeto_id=tanque.id, considerar_tanques=True):
                    self._actualizar_mapa_colisiones_objeto(tanque, agregar=False)
                    tanque.x_tile = nueva_x_tile
                    tanque.y_tile = nueva_y_tile
                    tanque.moviendose_este_tick = True
                    self._actualizar_mapa_colisiones_objeto(tanque, agregar=True)
                    tanque.registrar_movimiento_exitoso()
                    
                    # Actualizar ruta si se siguió correctamente
                    if (usar_dfs_para_jugador and tanque.ruta_actual_tiles and 
                        len(tanque.ruta_actual_tiles) > 0 and
                        isinstance(tanque.ruta_actual_tiles[0], tuple) and 
                        len(tanque.ruta_actual_tiles[0]) == 2 and
                        tanque.x_tile == tanque.ruta_actual_tiles[0][0] and 
                        tanque.y_tile == tanque.ruta_actual_tiles[0][1]):
                        tanque.ruta_actual_tiles.pop(0)
        
        tanque.accion_actual = STAY
    
    def _procesar_balas(self):
        """Procesa el movimiento y colisiones de todas las balas"""
        balas_a_quitar_ids = []
        
        for obj_id, obj in list(self.objetos_del_juego.items()):
            if isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual:
                continue
            if not obj.activo:
                continue
            if isinstance(obj, BalaModel):
                bala = obj
                if not bala.activo:
                    if bala.id not in balas_a_quitar_ids:
                        balas_a_quitar_ids.append(bala.id)
                    continue
                
                # Lógica de movimiento de bala (del motor original)
                bala.distancia_recorrida_tick += VELOCIDAD_BALA
                movimientos_de_bala_este_tick = 0
                
                while bala.distancia_recorrida_tick >= 1.0 and bala.activo:
                    bala.distancia_recorrida_tick -= 1.0
                    movimientos_de_bala_este_tick += 1
                    
                    if movimientos_de_bala_este_tick > max(GRID_WIDTH, GRID_HEIGHT) * 2:
                        bala.activo = False
                        break
                    
                    nueva_bala_x = bala.x_tile + bala.direccion_vector[0]
                    nueva_bala_y = bala.y_tile + bala.direccion_vector[1]
                    
                    if not (0 <= nueva_bala_x < GRID_WIDTH and 0 <= nueva_bala_y < GRID_HEIGHT):
                        bala.activo = False
                        break
                    
                    # Verificar colisiones
                    ids_objetos_en_destino = list(self.mapa_colisiones.get((nueva_bala_x, nueva_bala_y), []))
                    colision_encontrada = False
                    
                    for id_obj_col_destino in ids_objetos_en_destino:
                        obj_col_destino = self.objetos_del_juego.get(id_obj_col_destino)
                        if not obj_col_destino or not obj_col_destino.activo:
                            continue
                        if isinstance(obj_col_destino, TanqueEnemigoModel) and obj_col_destino.fue_destruido_visual:
                            continue

                        if isinstance(obj_col_destino, MuroModel):
                            bala.activo = False
                            colision_encontrada = True
                            break
                        elif isinstance(obj_col_destino, TanqueModel) and obj_col_destino.id != bala.propietario_id:
                            bala.activo = False
                            colision_encontrada = True
                            estaba_activo_antes_del_golpe = obj_col_destino.activo

                            # Verificar si es jugador impactado por enemigo fuerte
                            es_jugador_impactado = obj_col_destino.id in self.jugadores_ids.values()
                            propietario_es_enemigo_fuerte = (bala.tipo_propietario == TIPO_ENEMIGO_FUERTE)

                            if es_jugador_impactado and propietario_es_enemigo_fuerte:
                                obj_col_destino.vidas = 0

                            if obj_col_destino.recibir_impacto():
                                if (obj_col_destino.id in self.jugadores_ids.values() and 
                                    estaba_activo_antes_del_golpe):
                                    if self.player_final_destruction_sound and pygame.mixer.get_init():
                                        try:
                                            self.player_final_destruction_sound.play()
                                        except pygame.error as e:
                                            print(f"Error al reproducir sonido de explosión final: {e}")
                            break
                        elif (isinstance(obj_col_destino, ObjetivoPrimarioModel) and 
                              bala.tipo_propietario in [TIPO_JUGADOR, TIPO_JUGADOR_1, TIPO_JUGADOR_2, TIPO_JUGADOR_3, TIPO_JUGADOR_4]):
                            bala.activo = False
                            colision_encontrada = True
                            obj_col_destino.ser_destruido()
                            break
                    
                    if not colision_encontrada:
                        bala.x_tile = nueva_bala_x
                        bala.y_tile = nueva_bala_y
                    else:
                        break
                
                if not bala.activo:
                    if bala.id not in balas_a_quitar_ids:
                        balas_a_quitar_ids.append(bala.id)
        
        for bala_id in balas_a_quitar_ids:
            self._quitar_objeto(bala_id)
    
    def get_estado_para_vista(self):
        """Override para incluir información de múltiples jugadores"""
        estado_base = super().get_estado_para_vista()
        
        # Agregar información de jugadores
        jugadores_info = {}
        for player_id in self.jugadores_activos:
            tank_id = self.jugadores_ids.get(player_id)
            if tank_id:
                tank = self.objetos_del_juego.get(tank_id)
                player = self.player_manager.get_player(player_id)
                if tank and player:
                    jugadores_info[player_id] = {
                        'name': player.name,
                        'vidas': tank.vidas,
                        'score': player.score,
                        'color': player.color,
                        'active': tank.activo
                    }
        
        estado_base['jugadores'] = jugadores_info
        estado_base['modo_multijugador'] = True
        
        return estado_base