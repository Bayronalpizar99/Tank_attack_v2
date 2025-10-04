# backend/motor_juego.py
import random
import pygame
import os
import math
import heapq 

from constantes import (
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, MAX_NIVELES, SCREEN_WIDTH, SCREEN_HEIGHT,
    TIPO_JUGADOR,
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

class MotorJuego:
    def __init__(self, player_shoot_sound=None, player_final_destruction_sound=None):
        self.nivel_actual_numero = 0
        self.objetos_del_juego = {}
        self.jugador_id = None
        self.oponente_id = None
        self.mapa_colisiones = {}
        self.ticks_logicos_actuales = 0
        self.tiempo_ms_juego = 0

        self.player_shoot_sound = player_shoot_sound
        self.player_final_destruction_sound = player_final_destruction_sound

        self.puntos_spawn_jugador_por_nivel = {
            1: (1, GRID_HEIGHT // 2),
            2: (1, GRID_HEIGHT // 3),
            3: (1, GRID_HEIGHT // 2 + 1)
        }
        self.config_objetivos_por_nivel = {
            1: {"cantidad": 2, "tipos": [TIPO_OBJETIVO1, TIPO_OBJETIVO2]},
            2: {"cantidad": 3, "tipos": [TIPO_OBJETIVO1, TIPO_OBJETIVO2]},
            3: {"cantidad": 3, "tipos": [TIPO_OBJETIVO1, TIPO_OBJETIVO2]},
        }
        self.config_enemigos_por_objetivo = 1
        
        self.es_nivel_editado_actualmente = False
        self.last_player_tile_pos_for_enemy_logic = None

    def _limpiar_estado_nivel(self):
        self.objetos_del_juego = {}
        self.jugador_id = None
        self.oponente_id = None
        self.mapa_colisiones = {}
        for y_map in range(GRID_HEIGHT):
            for x_map in range(GRID_WIDTH):
                self.mapa_colisiones[(x_map,y_map)] = []
        self.es_nivel_editado_actualmente = False
        self.last_player_tile_pos_for_enemy_logic = None


    def _agregar_objeto(self, objeto_modelo):
        if not hasattr(objeto_modelo, 'id') or objeto_modelo.id is None:
            print(f"ERROR FATAL en _agregar_objeto: Objeto {objeto_modelo.tipo_objeto} en ({objeto_modelo.x_tile},{objeto_modelo.y_tile}) no tiene ID.")
            return
        self.objetos_del_juego[objeto_modelo.id] = objeto_modelo
        if isinstance(objeto_modelo, TanqueEnemigoModel) and objeto_modelo.fue_destruido_visual:
            return
        elif objeto_modelo.tipo_objeto != TIPO_BALA:
            self._actualizar_mapa_colisiones_objeto(objeto_modelo, agregar=True)

    def _quitar_objeto(self, objeto_id):
        if objeto_id in self.objetos_del_juego:
            obj = self.objetos_del_juego.pop(objeto_id)
            if not (isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual):
                if obj.tipo_objeto != TIPO_BALA:
                     self._actualizar_mapa_colisiones_objeto(obj, agregar=False)


    def _actualizar_mapa_colisiones_objeto(self, obj, agregar=True):
        if isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual:
            if not agregar:
                pos_actual_tile = (obj.x_tile, obj.y_tile)
                if 0 <= pos_actual_tile[0] < GRID_WIDTH and 0 <= pos_actual_tile[1] < GRID_HEIGHT:
                    if obj.id in self.mapa_colisiones.get(pos_actual_tile, []):
                        try: self.mapa_colisiones[pos_actual_tile].remove(obj.id)
                        except ValueError: pass
            return

        pos_actual_tile = (obj.x_tile, obj.y_tile)
        if 0 <= pos_actual_tile[0] < GRID_WIDTH and 0 <= pos_actual_tile[1] < GRID_HEIGHT:
            if agregar:
                if obj.id not in self.mapa_colisiones[pos_actual_tile]:
                    self.mapa_colisiones[pos_actual_tile].append(obj.id)
            else:
                if obj.id in self.mapa_colisiones.get(pos_actual_tile, []):
                    try: self.mapa_colisiones[pos_actual_tile].remove(obj.id)
                    except ValueError: pass

    def anadir_oponente(self, x, y):
        if self.oponente_id and self.oponente_id in self.objetos_del_juego:
            return

        oponente = TanqueJugadorModel(x, y)
        self.oponente_id = oponente.id
        self._agregar_objeto(oponente)
        print(f"Oponente añadido con ID: {self.oponente_id}")

    def actualizar_estado_remoto(self, datos_remotos):
        if not self.oponente_id:
            if datos_remotos.get('tipo') == TIPO_JUGADOR:
                self.anadir_oponente(datos_remotos['x_tile'], datos_remotos['y_tile'])

        oponente = self.objetos_del_juego.get(self.oponente_id)
        if oponente:
            oponente.pixel_x = datos_remotos['pixel_x']
            oponente.pixel_y = datos_remotos['pixel_y']
            oponente.x_tile = int(oponente.pixel_x / TILE_SIZE)
            oponente.y_tile = int(oponente.pixel_y / TILE_SIZE)
            oponente.direccion_actual = tuple(datos_remotos['direccion'])

            if datos_remotos.get('disparo'):
                start_pixel_x = oponente.pixel_x + TILE_SIZE / 2 + oponente.direccion_actual[0] * (TILE_SIZE / 2)
                start_pixel_y = oponente.pixel_y + TILE_SIZE / 2 + oponente.direccion_actual[1] * (TILE_SIZE / 2)
                bala = BalaModel(start_pixel_x, start_pixel_y, oponente.direccion_actual, self.oponente_id, TIPO_JUGADOR)
                self._agregar_objeto(bala)

    def _cargar_nivel_procedural(self, numero_nivel_int):
        print(f"Motor: Cargando nivel procedural {numero_nivel_int}")
        self.es_nivel_editado_actualmente = False
        spawn_x, spawn_y = self.puntos_spawn_jugador_por_nivel.get(numero_nivel_int, (1, GRID_HEIGHT // 2))
        
        jugador_obj_existente = self.objetos_del_juego.get(self.jugador_id) if self.jugador_id else None
        if jugador_obj_existente and isinstance(jugador_obj_existente, TanqueJugadorModel):
            self._actualizar_mapa_colisiones_objeto(jugador_obj_existente, agregar=False)
            jugador_obj_existente.reset_para_nuevo_nivel(spawn_x, spawn_y)
            self._agregar_objeto(jugador_obj_existente)
            self.last_player_tile_pos_for_enemy_logic = (jugador_obj_existente.x_tile, jugador_obj_existente.y_tile)
        else:
            jugador = TanqueJugadorModel(spawn_x, spawn_y)
            self._agregar_objeto(jugador)
            self.jugador_id = jugador.id
            self.last_player_tile_pos_for_enemy_logic = (jugador.x_tile, jugador.y_tile)
        
        posiciones_ocupadas_temp = [(spawn_x, spawn_y)]
        for x_borde in range(GRID_WIDTH):
            if (x_borde, 0) not in posiciones_ocupadas_temp: self._agregar_objeto(MuroModel(x_borde, 0)); posiciones_ocupadas_temp.append((x_borde,0))
            if (x_borde, GRID_HEIGHT - 1) not in posiciones_ocupadas_temp: self._agregar_objeto(MuroModel(x_borde, GRID_HEIGHT - 1)); posiciones_ocupadas_temp.append((x_borde, GRID_HEIGHT - 1))
        for y_borde in range(1, GRID_HEIGHT - 1):
            if (0, y_borde) not in posiciones_ocupadas_temp: self._agregar_objeto(MuroModel(0, y_borde)); posiciones_ocupadas_temp.append((0, y_borde))
            if (GRID_WIDTH - 1, y_borde) not in posiciones_ocupadas_temp: self._agregar_objeto(MuroModel(GRID_WIDTH - 1, y_borde)); posiciones_ocupadas_temp.append((GRID_WIDTH -1, y_borde))
        
        num_muros_internos = random.randint(15, (GRID_WIDTH * GRID_HEIGHT) // 12)
        for _ in range(num_muros_internos):
            intentos_muro = 0;
            while intentos_muro < 50:
                x, y = random.randint(1, GRID_WIDTH - 2), random.randint(1, GRID_HEIGHT - 2);
                if (x,y) not in posiciones_ocupadas_temp:
                    self._agregar_objeto(MuroModel(x, y)); posiciones_ocupadas_temp.append((x,y)); break
                intentos_muro +=1
        
        config_nivel_obj = self.config_objetivos_por_nivel.get(numero_nivel_int, {"cantidad": 1, "tipos": [TIPO_OBJETIVO1]})
        ids_objetivos_creados = []
        for _ in range(config_nivel_obj["cantidad"]):
            intentos_pos = 0
            while intentos_pos < 100:
                x, y = random.randint(1, GRID_WIDTH - 2), random.randint(1, GRID_HEIGHT - 2);
                if (x,y) not in posiciones_ocupadas_temp:
                    tipo_obj_azar = random.choice(config_nivel_obj["tipos"])
                    objetivo = ObjetivoPrimarioModel(x, y, tipo_obj_azar); self._agregar_objeto(objetivo)
                    ids_objetivos_creados.append(objetivo.id); posiciones_ocupadas_temp.append((x,y)); break
                intentos_pos +=1
        
        tipos_enemigos_disp = [TIPO_ENEMIGO_NORMAL, TIPO_ENEMIGO_RAPIDO, TIPO_ENEMIGO_FUERTE]
        for obj_id_objetivo in ids_objetivos_creados:
            objetivo_a_defender = self.objetos_del_juego.get(obj_id_objetivo)
            if not objetivo_a_defender: continue
            for _ in range(self.config_enemigos_por_objetivo):
                intentos_pos = 0
                while intentos_pos < 100:
                    ox, oy = objetivo_a_defender.x_tile, objetivo_a_defender.y_tile
                    dist_spawn = random.randint(1,3)
                    angle_spawn = random.uniform(0, 2 * math.pi)
                    dx = int(round(dist_spawn * math.cos(angle_spawn)))
                    dy = int(round(dist_spawn * math.sin(angle_spawn)))
                    x, y = ox + dx, oy + dy
                    if 0 < x < GRID_WIDTH -1 and 0 < y < GRID_HEIGHT -1 and (x,y) not in posiciones_ocupadas_temp:
                        tipo_enemigo_azar = random.choice(tipos_enemigos_disp)
                        enemigo = TanqueEnemigoModel(x, y, tipo_enemigo_azar, obj_id_objetivo); self._agregar_objeto(enemigo)
                        posiciones_ocupadas_temp.append((x,y)); break
                    intentos_pos +=1
        return True

    def _cargar_nivel_desde_archivo(self, ruta_archivo):
        print(f"Motor: Cargando nivel desde archivo {ruta_archivo}")
        self.es_nivel_editado_actualmente = True
        try:
            if not os.path.exists(ruta_archivo):
                print(f"Error: Archivo de nivel no encontrado en {ruta_archivo}")
                default_level_path = os.path.join(EDITOR_NIVELES_PATH, "nivel_defecto.txt")
                if os.path.exists(default_level_path):
                    print(f"Intentando cargar nivel por defecto: {default_level_path}")
                    ruta_archivo = default_level_path
                else:
                    print("Error: No se encontró ni el nivel solicitado ni un nivel por defecto.")
                    return False

            with open(ruta_archivo, 'r') as f:
                lines = f.readlines()
            
            posicion_jugador_encontrada = None
            objetos_para_agregar_temp = []
            enemigos_temp_con_objetivo = []

            for r, line in enumerate(lines):
                if r >= GRID_HEIGHT: continue
                for c, char_tile in enumerate(line.strip()):
                    if c >= GRID_WIDTH: continue
                    
                    tipo_objeto_modelo = EDITOR_CHAR_TO_TYPE.get(char_tile)
                    if tipo_objeto_modelo is None and char_tile != EDITOR_CHAR_VACIO:
                        print(f"Advertencia: Caracter '{char_tile}' desconocido en ({r},{c}) del archivo de nivel. Se ignora.")
                        continue
                    
                    if tipo_objeto_modelo == TIPO_JUGADOR:
                        if posicion_jugador_encontrada:
                            print("Advertencia: Múltiples jugadores definidos. Usando el primero.")
                        else:
                            posicion_jugador_encontrada = (c, r)
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
            
            if not posicion_jugador_encontrada:
                print("Error: No se encontró jugador. Colocando uno por defecto.")
                posicion_jugador_encontrada = (GRID_WIDTH // 2, GRID_HEIGHT // 2)
            
            spawn_x, spawn_y = posicion_jugador_encontrada
            jugador_obj_existente = self.objetos_del_juego.get(self.jugador_id) if self.jugador_id else None
            if jugador_obj_existente and isinstance(jugador_obj_existente, TanqueJugadorModel):
                self._actualizar_mapa_colisiones_objeto(jugador_obj_existente, agregar=False)
                jugador_obj_existente.reset_para_nuevo_nivel(spawn_x, spawn_y)
                self._agregar_objeto(jugador_obj_existente)
                self.last_player_tile_pos_for_enemy_logic = (jugador_obj_existente.x_tile, jugador_obj_existente.y_tile)
            else:
                jugador = TanqueJugadorModel(spawn_x, spawn_y)
                self._agregar_objeto(jugador)
                self.jugador_id = jugador.id
                self.last_player_tile_pos_for_enemy_logic = (jugador.x_tile, jugador.y_tile)
            
            for obj_modelo in objetos_para_agregar_temp:
                self._agregar_objeto(obj_modelo)
            
            objetivos_en_mapa = [obj for obj in self.objetos_del_juego.values() if isinstance(obj, ObjetivoPrimarioModel)]
            
            for enemigo_model, _ in enemigos_temp_con_objetivo:
                if objetivos_en_mapa:
                    enemigo_model.objetivo_primario_id_asignado = random.choice(objetivos_en_mapa).id
                self._agregar_objeto(enemigo_model)
            
            return True

        except FileNotFoundError:
            print(f"Error crítico: Archivo de nivel no encontrado en {ruta_archivo} después de la comprobación.")
            return False
        except Exception as e:
            print(f"Error al cargar nivel desde archivo {ruta_archivo}: {e}")
            return False

    def cargar_nivel(self, nivel_id_o_ruta):
        self._limpiar_estado_nivel()
        self.nivel_actual_numero = nivel_id_o_ruta
        
        exito_carga = False
        if isinstance(nivel_id_o_ruta, int):
            if nivel_id_o_ruta == 0:
                return False
            exito_carga = self._cargar_nivel_procedural(nivel_id_o_ruta)
        elif isinstance(nivel_id_o_ruta, str):
            if not os.path.isabs(nivel_id_o_ruta) and not nivel_id_o_ruta.startswith(EDITOR_NIVELES_PATH):
                 if not nivel_id_o_ruta.endswith(".txt"): nivel_id_o_ruta += ".txt"
                 nivel_id_o_ruta = os.path.join(EDITOR_NIVELES_PATH, nivel_id_o_ruta)
            
            exito_carga = self._cargar_nivel_desde_archivo(nivel_id_o_ruta)
            if exito_carga: self.nivel_actual_numero = nivel_id_o_ruta
        else:
            print(f"Error: Identificador de nivel desconocido: {nivel_id_o_ruta}")
            return False

        if exito_carga:
            jugador_obj = self.objetos_del_juego.get(self.jugador_id)
            if jugador_obj:
                self.last_player_tile_pos_for_enemy_logic = (jugador_obj.x_tile, jugador_obj.y_tile)
                if isinstance(jugador_obj, TanqueJugadorModel):
                    jugador_obj.last_known_tile_pos = (jugador_obj.x_tile, jugador_obj.y_tile)
            else:
                self.last_player_tile_pos_for_enemy_logic = None
            return True
        return False


    def _es_posicion_valida_y_libre(self, x_tile, y_tile, para_objeto_id=None, considerar_tanques=True):
        if not (0 <= x_tile < GRID_WIDTH and 0 <= y_tile < GRID_HEIGHT): return False
        objetos_ids_en_celda = self.mapa_colisiones.get((x_tile, y_tile), [])
        for obj_id_en_celda in objetos_ids_en_celda:
            if para_objeto_id and obj_id_en_celda == para_objeto_id: continue
            obj_colision = self.objetos_del_juego.get(obj_id_en_celda)
            if obj_colision:
                if isinstance(obj_colision, TanqueEnemigoModel) and obj_colision.fue_destruido_visual: continue
                if obj_colision.activo:
                    if obj_colision.tipo_objeto == TIPO_MURO: return False
                    if considerar_tanques and (obj_colision.tipo_objeto == TIPO_JUGADOR or obj_colision.tipo_objeto.startswith("enemigo_")): return False
        return True
        
    def actualizar_estado(self, acciones_jugador, tiempo_delta_ms):
        self.tiempo_ms_juego += tiempo_delta_ms
        self.ticks_logicos_actuales += 1
        tiempo_delta_s = tiempo_delta_ms / 1000.0

        for obj in list(self.objetos_del_juego.values()):
            if isinstance(obj, TanqueModel):
                obj.update_posicion_pixel(tiempo_delta_s)

        ids_a_quitar_definitivamente = []
        for obj_id, obj in list(self.objetos_del_juego.items()):
            if isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual:
                if pygame.time.get_ticks() - obj.tiempo_destruccion_visual > obj.duracion_explosion_visual:
                    ids_a_quitar_definitivamente.append(obj_id)
            elif not obj.activo and obj.tipo_objeto != TIPO_JUGADOR:
                ids_a_quitar_definitivamente.append(obj_id)
        for obj_id in ids_a_quitar_definitivamente:
            self._quitar_objeto(obj_id)

        jugador = self.objetos_del_juego.get(self.jugador_id)
        if not jugador or not jugador.activo: return GAME_OVER

        current_player_pos_tile_before_move = (jugador.x_tile, jugador.y_tile)
        
        # Lógica de movimiento del jugador
        # MEJORADO: Permitir iniciar nuevo movimiento si está cerca de completar el actual
        puede_iniciar_nuevo_movimiento = not jugador.is_moving
        
        # Si está moviéndose, verificar si ya llegó a la casilla destino
        if jugador.is_moving:
            # Si ya está en la casilla destino (x_tile, y_tile actualizados), permitir nuevo movimiento
            if jugador.x_tile * TILE_SIZE == jugador.pixel_x and jugador.y_tile * TILE_SIZE == jugador.pixel_y:
                puede_iniciar_nuevo_movimiento = True
        
        if puede_iniciar_nuevo_movimiento:
            nueva_intencion_movimiento = STAY
            if acciones_jugador.get("detenerse"):
                jugador.detenido_por_usuario = True
            elif acciones_jugador.get("mover"):
                jugador.detenido_por_usuario = False
                nueva_intencion_movimiento = acciones_jugador.get("mover")
            
            jugador.intentar_mover(nueva_intencion_movimiento)

            if jugador.accion_actual != STAY and not jugador.detenido_por_usuario:
                nueva_x_j = jugador.x_tile + jugador.accion_actual[0]
                nueva_y_j = jugador.y_tile + jugador.accion_actual[1]
                if self._es_posicion_valida_y_libre(nueva_x_j, nueva_y_j, para_objeto_id=jugador.id):
                    self._actualizar_mapa_colisiones_objeto(jugador, agregar=False)
                    jugador.iniciar_movimiento_a_casilla(nueva_x_j, nueva_y_j)
                    self._actualizar_mapa_colisiones_objeto(jugador, agregar=True)
        
        # Lógica de disparo del jugador
        if acciones_jugador.get("disparar") and jugador.puede_disparar(self.tiempo_ms_juego):
            jugador.registrar_disparo(self.tiempo_ms_juego)
            start_pixel_x = jugador.pixel_x + TILE_SIZE / 2 + jugador.direccion_actual[0] * (TILE_SIZE / 2)
            start_pixel_y = jugador.pixel_y + TILE_SIZE / 2 + jugador.direccion_actual[1] * (TILE_SIZE / 2)
            bala = BalaModel(start_pixel_x, start_pixel_y, jugador.direccion_actual, self.jugador_id, TIPO_JUGADOR)
            self._agregar_objeto(bala)
            if self.player_shoot_sound and pygame.mixer.get_init():
                try: self.player_shoot_sound.play()
                except pygame.error as e: print(f"Error al reproducir sonido de disparo del jugador: {e}")

        if (jugador.x_tile, jugador.y_tile) != current_player_pos_tile_before_move:
            self.last_player_tile_pos_for_enemy_logic = (jugador.x_tile, jugador.y_tile)

        # Lógica de IA de Enemigos
        tanques_enemigos_ids = [obj_id for obj_id, obj in self.objetos_del_juego.items() if isinstance(obj, TanqueEnemigoModel) and obj.activo]
        for tanque_id in tanques_enemigos_ids:
            tanque = self.objetos_del_juego.get(tanque_id)
            if not tanque or tanque.is_moving: continue

            pos_j_actual_para_enemigo = self.last_player_tile_pos_for_enemy_logic or (jugador.x_tile, jugador.y_tile)
            
            # --- JERARQUÍA DE DECISIONES DE LA IA ---
            
            # 1. PRIORIDAD MÁXIMA: ATACAR SI ES POSIBLE
            tiene_linea_de_vision = self._linea_de_vision_libre(tanque, jugador)
            if tiene_linea_de_vision and tanque.pos_distancia_sq(pos_j_actual_para_enemigo) <= tanque.rango_disparo ** 2:
                # Apuntar al jugador
                dist_x_abs = jugador.x_tile - tanque.x_tile
                dist_y_abs = jugador.y_tile - tanque.y_tile
                if abs(dist_x_abs) > abs(dist_y_abs):
                    tanque.direccion_actual = RIGHT if dist_x_abs > 0 else LEFT
                elif abs(dist_y_abs) > 0:
                    tanque.direccion_actual = DOWN if dist_y_abs > 0 else UP
                
                # Disparar si puede
                if tanque.puede_disparar(self.tiempo_ms_juego):
                    tanque.registrar_disparo(self.tiempo_ms_juego)
                    start_pixel_x = tanque.pixel_x + TILE_SIZE / 2 + tanque.direccion_actual[0] * (TILE_SIZE / 2)
                    start_pixel_y = tanque.pixel_y + TILE_SIZE / 2 + tanque.direccion_actual[1] * (TILE_SIZE / 2)
                    bala = BalaModel(start_pixel_x, start_pixel_y, tanque.direccion_actual, tanque.id, tanque.tipo_objeto)
                    self._agregar_objeto(bala)
                continue # Si puede atacar, no hace nada más este frame

            # 2. PRIORIDAD: PERSEGUIR AL JUGADOR
            jugador_se_movio = tanque.ultima_pos_jugador_vista_para_ruta != pos_j_actual_para_enemigo
            tanque.ticks_para_recalcular_ruta -= 1  # Decrementar el timer cada frame
            if tanque.debe_recalcular_ruta(pos_j_actual_para_enemigo, jugador_se_movio):
                pos_e_actual = (tanque.x_tile, tanque.y_tile)
                nueva_ruta = self._encontrar_ruta_a_estrella(pos_e_actual, pos_j_actual_para_enemigo)
                if nueva_ruta and len(nueva_ruta) > 1:
                    tanque.ruta_actual_tiles = nueva_ruta[1:]
                else:
                    tanque.ruta_actual_tiles = []
                tanque.reset_timer_recalcular_ruta()
                tanque.ultima_pos_jugador_vista_para_ruta = pos_j_actual_para_enemigo

            accion_movimiento_definida = STAY
            if tanque.ruta_actual_tiles:
                siguiente_paso = tanque.ruta_actual_tiles[0]
                if self._es_posicion_valida_y_libre(siguiente_paso[0], siguiente_paso[1], para_objeto_id=tanque.id):
                    dx, dy = siguiente_paso[0] - tanque.x_tile, siguiente_paso[1] - tanque.y_tile
                    if dx > 0: accion_movimiento_definida = RIGHT
                    elif dx < 0: accion_movimiento_definida = LEFT
                    elif dy > 0: accion_movimiento_definida = DOWN
                    elif dy < 0: accion_movimiento_definida = UP
                else:
                    tanque.ruta_actual_tiles = [] # Ruta bloqueada, forzar recálculo la próxima vez
            else:
                # NUEVO: Si no hay ruta, intentar moverse hacia la dirección general del jugador
                dx_general = pos_j_actual_para_enemigo[0] - tanque.x_tile
                dy_general = pos_j_actual_para_enemigo[1] - tanque.y_tile
                
                # Intentar moverse en la dirección con mayor diferencia
                direcciones_intentar = []
                if abs(dx_general) > abs(dy_general):
                    # Priorizar movimiento horizontal
                    if dx_general > 0:
                        direcciones_intentar = [RIGHT, DOWN if dy_general > 0 else UP, LEFT]
                    else:
                        direcciones_intentar = [LEFT, DOWN if dy_general > 0 else UP, RIGHT]
                else:
                    # Priorizar movimiento vertical
                    if dy_general > 0:
                        direcciones_intentar = [DOWN, RIGHT if dx_general > 0 else LEFT, UP]
                    else:
                        direcciones_intentar = [UP, RIGHT if dx_general > 0 else LEFT, DOWN]
                
                # Intentar cada dirección hasta encontrar una válida
                for dir_intento in direcciones_intentar:
                    nueva_x = tanque.x_tile + dir_intento[0]
                    nueva_y = tanque.y_tile + dir_intento[1]
                    if self._es_posicion_valida_y_libre(nueva_x, nueva_y, para_objeto_id=tanque.id):
                        accion_movimiento_definida = dir_intento
                        break
            
            # 3. PLAN B: PATRULLA ACTIVA SI NO HAY NADA MEJOR QUE HACER
            if accion_movimiento_definida == STAY:
                tanque.ticks_para_nueva_decision_patrulla -= 1
                if tanque.ticks_para_nueva_decision_patrulla <= 0:
                    direcciones_validas = []
                    for dir_intento in DIRECTIONS:
                        pos_intento_x = tanque.x_tile + dir_intento[0]
                        pos_intento_y = tanque.y_tile + dir_intento[1]
                        if self._es_posicion_valida_y_libre(pos_intento_x, pos_intento_y, para_objeto_id=tanque.id):
                            direcciones_validas.append(dir_intento)
                    if direcciones_validas:
                        tanque.direccion_patrulla_actual = random.choice(direcciones_validas)
                    else:
                        tanque.direccion_patrulla_actual = STAY
                    tanque.ticks_para_nueva_decision_patrulla = tanque.frecuencia_decision_patrulla
                accion_movimiento_definida = tanque.direccion_patrulla_actual
            
            # Ejecutar el movimiento decidido
            tanque.intentar_mover(accion_movimiento_definida)
            if tanque.accion_actual != STAY:
                nueva_x = tanque.x_tile + tanque.accion_actual[0]
                nueva_y = tanque.y_tile + tanque.accion_actual[1]
                if self._es_posicion_valida_y_libre(nueva_x, nueva_y, para_objeto_id=tanque.id):
                    self._actualizar_mapa_colisiones_objeto(tanque, agregar=False)
                    tanque.iniciar_movimiento_a_casilla(nueva_x, nueva_y)
                    self._actualizar_mapa_colisiones_objeto(tanque, agregar=True)
                    # Consumir el paso de la ruta si se movió exitosamente
                    if tanque.ruta_actual_tiles:
                        tanque.ruta_actual_tiles.pop(0)

        # Lógica de Balas
        balas_a_quitar_ids = []
        for bala in [obj for obj in self.objetos_del_juego.values() if isinstance(obj, BalaModel)]:
            if not bala.activo: continue

            distancia_a_mover = VELOCIDAD_BALA * TILE_SIZE * 30 * tiempo_delta_s
            bala.pixel_x += bala.direccion_vector[0] * distancia_a_mover
            bala.pixel_y += bala.direccion_vector[1] * distancia_a_mover
            
            nueva_tile_x = int(bala.pixel_x / TILE_SIZE)
            nueva_tile_y = int(bala.pixel_y / TILE_SIZE)

            if not (0 <= nueva_tile_x < GRID_WIDTH and 0 <= nueva_tile_y < GRID_HEIGHT):
                bala.activo = False
                balas_a_quitar_ids.append(bala.id)
                continue

            bala.x_tile = nueva_tile_x
            bala.y_tile = nueva_tile_y

            ids_en_casilla = self.mapa_colisiones.get((bala.x_tile, bala.y_tile), [])
            for obj_id in ids_en_casilla:
                if not bala.activo: break
                obj_colision = self.objetos_del_juego.get(obj_id)
                if obj_colision and obj_colision.id != bala.propietario_id and obj_colision.activo:
                    bala_rect = pygame.Rect(bala.pixel_x, bala.pixel_y, TILE_SIZE / 4, TILE_SIZE / 4)
                    obj_rect = pygame.Rect(obj_colision.pixel_x, obj_colision.pixel_y, TILE_SIZE, TILE_SIZE)

                    if bala_rect.colliderect(obj_rect):
                        bala.activo = False
                        balas_a_quitar_ids.append(bala.id)
                        if isinstance(obj_colision, TanqueModel):
                            obj_colision.recibir_impacto()
                        elif isinstance(obj_colision, ObjetivoPrimarioModel) and bala.tipo_propietario == TIPO_JUGADOR:
                            obj_colision.ser_destruido()
                        break
        
        for bala_id in balas_a_quitar_ids:
            self._quitar_objeto(bala_id)

        if not jugador.activo: return GAME_OVER
        if self._todos_objetivos_destruidos():
            if self.es_nivel_editado_actualmente: return VICTORIA_FINAL
            elif isinstance(self.nivel_actual_numero, int) and self.nivel_actual_numero < MAX_NIVELES: return NIVEL_COMPLETADO
            else: return VICTORIA_FINAL
        
        return JUGANDO

    def _linea_de_vision_libre(self, origen_obj, destino_obj):
        if not origen_obj or not destino_obj: return False
        x1, y1 = origen_obj.x_tile, origen_obj.y_tile; x2, y2 = destino_obj.x_tile, destino_obj.y_tile
        if x1 == x2:
            for y_intermedio in range(min(y1, y2) + 1, max(y1, y2)):
                ids_en_tile = self.mapa_colisiones.get((x1, y_intermedio), [])
                if any(isinstance(self.objetos_del_juego.get(oid), MuroModel) for oid in ids_en_tile if self.objetos_del_juego.get(oid) and self.objetos_del_juego.get(oid).activo): return False
            return True
        elif y1 == y2:
            for x_intermedio in range(min(x1, x2) + 1, max(x1, x2)):
                ids_en_tile = self.mapa_colisiones.get((x_intermedio, y1), [])
                if any(isinstance(self.objetos_del_juego.get(oid), MuroModel) for oid in ids_en_tile if self.objetos_del_juego.get(oid) and self.objetos_del_juego.get(oid).activo): return False
            return True
        return False

    def _encontrar_ruta_a_estrella(self, inicio, fin):
        frontera = [(0, 0, inicio, [])]
        visitados = set()
        visitados.add(inicio)

        while frontera:
            _, costo_actual, pos_actual, camino = heapq.heappop(frontera)

            if pos_actual == fin:
                return camino + [pos_actual]

            for direccion in DIRECTIONS:
                vecino = (pos_actual[0] + direccion[0], pos_actual[1] + direccion[1])

                if self._es_posicion_valida_y_libre(vecino[0], vecino[1], considerar_tanques=False) and vecino not in visitados:
                    visitados.add(vecino)
                    nuevo_costo = costo_actual + 1
                    
                    heuristica = abs(vecino[0] - fin[0]) + abs(vecino[1] - fin[1])
                    costo_total_estimado = nuevo_costo + heuristica
                    
                    heapq.heappush(frontera, (costo_total_estimado, nuevo_costo, vecino, camino + [pos_actual]))
        
        return None 


    def _todos_objetivos_destruidos(self):
        objetivos_totales_en_nivel = 0
        objetivos_activos = 0
        for obj in self.objetos_del_juego.values():
            if isinstance(obj, ObjetivoPrimarioModel):
                objetivos_totales_en_nivel +=1
                if obj.activo:
                    objetivos_activos +=1
        
        if objetivos_totales_en_nivel == 0:
            if (isinstance(self.nivel_actual_numero, int) and self.nivel_actual_numero == 0) or \
               (isinstance(self.nivel_actual_numero, str) and not self.es_nivel_editado_actualmente):
                return False

            print("Info: No hay objetivos definidos en este nivel. Considerado como completado.")
            return True

        return objetivos_activos == 0

    def get_estado_para_vista(self):
        vista_objetos = []
        enemigos_destruyendose_vista = []

        for obj_modelo in list(self.objetos_del_juego.values()):
            if isinstance(obj_modelo, TanqueEnemigoModel) and obj_modelo.fue_destruido_visual:
                if pygame.time.get_ticks() - obj_modelo.tiempo_destruccion_visual <= obj_modelo.duracion_explosion_visual:
                    enemigos_destruyendose_vista.append({
                        "id": obj_modelo.id,
                        "x_tile": obj_modelo.x_tile,
                        "y_tile": obj_modelo.y_tile,
                    })
                continue

            if obj_modelo.activo:
                obj_id = getattr(obj_modelo, 'id', None)
                if obj_id is None: continue
                
                pixel_x = getattr(obj_modelo, 'pixel_x', obj_modelo.x_tile * TILE_SIZE)
                pixel_y = getattr(obj_modelo, 'pixel_y', obj_modelo.y_tile * TILE_SIZE)

                vista_objetos.append({
                    "id": obj_id, "tipo": obj_modelo.tipo_objeto,
                    "x_tile": obj_modelo.x_tile, "y_tile": obj_modelo.y_tile,
                    "pixel_x": pixel_x, "pixel_y": pixel_y,
                    "direccion": getattr(obj_modelo, 'direccion_actual', None),
                    "is_moving": getattr(obj_modelo, 'is_moving', False)
                })
        
        jugador_modelo = self.objetos_del_juego.get(self.jugador_id)
        vidas_jugador = 0
        if jugador_modelo and hasattr(jugador_modelo, 'vidas'): vidas_jugador = jugador_modelo.vidas
        return {
            "objetos": vista_objetos,
            "nivel": self.nivel_actual_numero,
            "vidas_jugador": vidas_jugador,
            "enemigos_destruyendose": enemigos_destruyendose_vista
        }