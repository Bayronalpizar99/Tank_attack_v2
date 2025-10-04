# backend/motor_juego.py
import random
import pygame
import os
import math
import heapq # Necesario para el algoritmo A*

from constantes import (
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, MAX_NIVELES,
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
        self.oponente_id = None # <-- NUEVO
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
        self.oponente_id = None # Limpiar también el oponente
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
            return # Ya existe un oponente

        oponente = TanqueJugadorModel(x, y) # Usamos el mismo modelo para simplicidad
        self.oponente_id = oponente.id
        self._agregar_objeto(oponente)
        print(f"Oponente añadido con ID: {self.oponente_id}")

    def actualizar_estado_remoto(self, datos_remotos):
        if not self.oponente_id:
            # Si recibimos datos de un jugador y no tenemos oponente, lo creamos
            if datos_remotos.get('tipo') == TIPO_JUGADOR:
                self.anadir_oponente(datos_remotos['x_tile'], datos_remotos['y_tile'])

        oponente = self.objetos_del_juego.get(self.oponente_id)
        if oponente:
            oponente.x_tile = datos_remotos['x_tile']
            oponente.y_tile = datos_remotos['y_tile']
            # Asegurarse que la dirección sea una tupla
            oponente.direccion_actual = tuple(datos_remotos['direccion']) 

            if datos_remotos.get('disparo'):
                bala_x = oponente.x_tile + oponente.direccion_actual[0]
                bala_y = oponente.y_tile + oponente.direccion_actual[1]
                if 0 <= bala_x < GRID_WIDTH and 0 <= bala_y < GRID_HEIGHT:
                    bala = BalaModel(bala_x, bala_y, oponente.direccion_actual, self.oponente_id, TIPO_JUGADOR)
                    self._agregar_objeto(bala)
                    self._resolver_colision_inmediata_bala(bala)

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

    def _resolver_colision_inmediata_bala(self, bala):
        if not bala.activo: return False
        ids_objetos_en_casilla_spawn = list(self.mapa_colisiones.get((bala.x_tile, bala.y_tile), []))
        for id_obj_col in ids_objetos_en_casilla_spawn:
            obj_col_destino = self.objetos_del_juego.get(id_obj_col)
            if not obj_col_destino or not obj_col_destino.activo : continue
            if isinstance(obj_col_destino, TanqueEnemigoModel) and obj_col_destino.fue_destruido_visual: continue
            if obj_col_destino.id == bala.id: continue
            if isinstance(obj_col_destino, MuroModel): bala.activo = False; return True
            elif isinstance(obj_col_destino, TanqueModel) and obj_col_destino.id != bala.propietario_id:
                bala.activo = False
                estaba_activo_antes_del_golpe = obj_col_destino.activo

                es_jugador_impactado = (obj_col_destino.id == self.jugador_id)
                propietario_es_enemigo_fuerte = (bala.tipo_propietario == TIPO_ENEMIGO_FUERTE)

                if es_jugador_impactado and propietario_es_enemigo_fuerte:
                    obj_col_destino.vidas = 0 

                if obj_col_destino.recibir_impacto():
                    if obj_col_destino.id == self.jugador_id and estaba_activo_antes_del_golpe:
                         if self.player_final_destruction_sound and pygame.mixer.get_init():
                            try: self.player_final_destruction_sound.play()
                            except pygame.error as e: print(f"Error al reproducir sonido de explosión final: {e}")
                return True
            elif isinstance(obj_col_destino, ObjetivoPrimarioModel) and bala.tipo_propietario == TIPO_JUGADOR:
                bala.activo = False; obj_col_destino.ser_destruido(); return True
        return False

    def actualizar_estado(self, acciones_jugador, tiempo_delta_ms):
        self.tiempo_ms_juego += tiempo_delta_ms
        self.ticks_logicos_actuales += 1
        
        ids_a_quitar_definitivamente = []
        for obj_id, obj in list(self.objetos_del_juego.items()):
            if isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual:
                if pygame.time.get_ticks() - obj.tiempo_destruccion_visual > obj.duracion_explosion_visual:
                    ids_a_quitar_definitivamente.append(obj_id)
            elif not obj.activo and obj_id != self.jugador_id:
                ids_a_quitar_definitivamente.append(obj_id)

        for obj_id in ids_a_quitar_definitivamente:
            self._quitar_objeto(obj_id)

        jugador = self.objetos_del_juego.get(self.jugador_id)
        if not jugador: return GAME_OVER
        if not jugador.activo: return GAME_OVER

        jugador.actualizar_contador_movimiento_jugador()
        current_player_pos_tile_before_move = (jugador.x_tile, jugador.y_tile)
        
        jugador_puede_actuar_este_tick = jugador.puede_moverse_este_tick_jugador()


        player_moved_this_tick = False

        nueva_intencion_movimiento = None
        if acciones_jugador.get("detenerse"):
            jugador.detenido_por_usuario = True; nueva_intencion_movimiento = STAY
        elif acciones_jugador.get("mover"):
            jugador.detenido_por_usuario = False; nueva_intencion_movimiento = acciones_jugador["mover"]
        elif jugador.detenido_por_usuario: nueva_intencion_movimiento = STAY
        else: nueva_intencion_movimiento = jugador.direccion_actual
        jugador.intentar_mover(nueva_intencion_movimiento)

        if acciones_jugador.get("disparar") and jugador.puede_disparar(self.tiempo_ms_juego):
            jugador.registrar_disparo(self.tiempo_ms_juego)
            bala_x = jugador.x_tile + jugador.direccion_actual[0]; bala_y = jugador.y_tile + jugador.direccion_actual[1]
            if 0 <= bala_x < GRID_WIDTH and 0 <= bala_y < GRID_HEIGHT:
                bala = BalaModel(bala_x, bala_y, jugador.direccion_actual, self.jugador_id, TIPO_JUGADOR)
                self._agregar_objeto(bala); self._resolver_colision_inmediata_bala(bala)
                if self.player_shoot_sound and pygame.mixer.get_init():
                    try: self.player_shoot_sound.play()
                    except pygame.error as e: print(f"Error al reproducir sonido de disparo del jugador: {e}")
            
        jugador.moviendose_este_tick = False
        if jugador.accion_actual != STAY and not jugador.detenido_por_usuario:
            if jugador_puede_actuar_este_tick:
                nueva_x_j = jugador.x_tile + jugador.accion_actual[0]; nueva_y_j = jugador.y_tile + jugador.accion_actual[1]
                if self._es_posicion_valida_y_libre(nueva_x_j, nueva_y_j, para_objeto_id=jugador.id):
                    self._actualizar_mapa_colisiones_objeto(jugador, agregar=False); jugador.x_tile = nueva_x_j; jugador.y_tile = nueva_y_j
                    jugador.moviendose_este_tick = True; self._actualizar_mapa_colisiones_objeto(jugador, agregar=True); jugador.registrar_movimiento_exitoso_jugador()
        
        current_player_pos_tile_after_move = (jugador.x_tile, jugador.y_tile)
        if current_player_pos_tile_after_move != current_player_pos_tile_before_move:
            player_moved_this_tick = True
            self.last_player_tile_pos_for_enemy_logic = current_player_pos_tile_after_move
            if isinstance(jugador, TanqueJugadorModel):
                 jugador.last_known_tile_pos = current_player_pos_tile_after_move

        tanques_enemigos_ids = [obj_id for obj_id, obj in self.objetos_del_juego.items() if isinstance(obj, TanqueEnemigoModel) and obj.activo]
        
        for tanque_id in tanques_enemigos_ids:
            tanque = self.objetos_del_juego.get(tanque_id)
            if not tanque or not tanque.activo : continue
            
            tanque.moviendose_este_tick = False
            accion_movimiento_definida = STAY
            usar_dfs_para_jugador = False

            pos_j_actual_para_enemigo = self.last_player_tile_pos_for_enemy_logic if self.last_player_tile_pos_for_enemy_logic else (jugador.x_tile, jugador.y_tile)
            distancia_al_jugador_sq = tanque.pos_distancia_sq(pos_j_actual_para_enemigo)
            
            recalc_dfs_decision_made = False
            if jugador and jugador.activo and distancia_al_jugador_sq <= DFS_ACTIVATION_RANGE_SQ:
                
                jugador_se_movio_desde_ultima_ruta_del_tanque = tanque.ultima_pos_jugador_vista_para_ruta != pos_j_actual_para_enemigo
                
                if tanque.debe_recalcular_ruta(pos_j_actual_para_enemigo, jugador_se_movio_desde_ultima_ruta_del_tanque):
                    recalc_dfs_decision_made = True
                    if jugador_puede_actuar_este_tick:
                        tanque.ticks_para_recalcular_ruta = 1
                    else:
                        pos_e_actual = (tanque.x_tile, tanque.y_tile)
                        nueva_ruta = self._encontrar_ruta_a_estrella(pos_e_actual, pos_j_actual_para_enemigo)
                        if nueva_ruta:
                            nueva_ruta.pop(0) 
                        tanque.ruta_actual_tiles = nueva_ruta if nueva_ruta else []
                        tanque.reset_timer_recalcular_ruta()
                        tanque.ultima_pos_jugador_vista_para_ruta = pos_j_actual_para_enemigo
            
            if tanque.ruta_actual_tiles:
                siguiente_paso_tile_test = tanque.ruta_actual_tiles[0]
                if isinstance(siguiente_paso_tile_test, tuple) and len(siguiente_paso_tile_test) == 2:
                     if not self._es_posicion_valida_y_libre(siguiente_paso_tile_test[0], siguiente_paso_tile_test[1], para_objeto_id=tanque.id, considerar_tanques=True):
                        tanque.ruta_actual_tiles = []
                     else:
                         usar_dfs_para_jugador = True
                         siguiente_paso_tile = tanque.ruta_actual_tiles[0]
                         dx_tile = siguiente_paso_tile[0] - tanque.x_tile; dy_tile = siguiente_paso_tile[1] - tanque.y_tile
                         if dx_tile > 0: accion_movimiento_definida = RIGHT
                         elif dx_tile < 0: accion_movimiento_definida = LEFT
                         elif dy_tile > 0: accion_movimiento_definida = DOWN
                         elif dy_tile < 0: accion_movimiento_definida = UP
                else:
                    tanque.ruta_actual_tiles = []

            if not usar_dfs_para_jugador:
                if not recalc_dfs_decision_made :
                     tanque.ticks_para_nueva_decision_patrulla -= 1

                objetivo_asignado_model = None
                if tanque.objetivo_primario_id_asignado:
                    objetivo_asignado_model = self.objetos_del_juego.get(tanque.objetivo_primario_id_asignado)
                
                if tanque.ticks_para_nueva_decision_patrulla <= 0:
                    if jugador_puede_actuar_este_tick:
                        tanque.ticks_para_nueva_decision_patrulla = 1
                    else:
                        nueva_dir_patrulla = STAY
                        if objetivo_asignado_model and objetivo_asignado_model.activo:
                            pos_objetivo = (objetivo_asignado_model.x_tile, objetivo_asignado_model.y_tile)
                            dist_al_objetivo_sq = tanque.pos_distancia_sq(pos_objetivo)
                            
                            movimientos_posibles_evaluados = []
                            for dir_intento in DIRECTIONS:
                                px = tanque.x_tile + dir_intento[0]; py = tanque.y_tile + dir_intento[1]
                                if self._es_posicion_valida_y_libre(px, py, para_objeto_id=tanque.id, considerar_tanques=True):
                                    nueva_dist_obj_sq = (px - pos_objetivo[0])**2 + (py - pos_objetivo[1])**2
                                    movimientos_posibles_evaluados.append({"dir": dir_intento, "new_dist_sq": nueva_dist_obj_sq})
                            
                            if movimientos_posibles_evaluados:
                                if dist_al_objetivo_sq > OBJECTIVE_PATROL_MAX_DISTANCE_SQ:
                                    movimientos_posibles_evaluados.sort(key=lambda m: m["new_dist_sq"])
                                    nueva_dir_patrulla = movimientos_posibles_evaluados[0]["dir"]
                                elif dist_al_objetivo_sq < OBJECTIVE_PATROL_MIN_DISTANCE_SQ:
                                    movimientos_posibles_evaluados.sort(key=lambda m: m["new_dist_sq"], reverse=True)
                                    nueva_dir_patrulla = movimientos_posibles_evaluados[0]["dir"]
                                else:
                                    random.shuffle(movimientos_posibles_evaluados)
                                    nueva_dir_patrulla = movimientos_posibles_evaluados[0]["dir"]
                        else: 
                            direcciones_validas_solo = []
                            shuffled_directions = list(DIRECTIONS); random.shuffle(shuffled_directions)
                            for dir_intento in shuffled_directions:
                                pos_intento_x = tanque.x_tile + dir_intento[0]; pos_intento_y = tanque.y_tile + dir_intento[1]
                                if self._es_posicion_valida_y_libre(pos_intento_x, pos_intento_y, para_objeto_id=tanque.id, considerar_tanques=True):
                                    direcciones_validas_solo.append(dir_intento)
                            if direcciones_validas_solo:
                                nueva_dir_patrulla = random.choice(direcciones_validas_solo)
                        
                        tanque.direccion_patrulla_actual = nueva_dir_patrulla
                        tanque.ticks_para_nueva_decision_patrulla = tanque.frecuencia_decision_patrulla
                
                accion_movimiento_definida = tanque.direccion_patrulla_actual
            
            tanque.intentar_mover(accion_movimiento_definida)
            
            decision_disparar = False
            if jugador and jugador.activo:
                dist_x_sq_disp = (tanque.x_tile - jugador.x_tile)**2; dist_y_sq_disp = (tanque.y_tile - jugador.y_tile)**2
                if (dist_x_sq_disp + dist_y_sq_disp) <= (tanque.rango_disparo ** 2):
                    if self._linea_de_vision_libre(tanque, jugador):
                        decision_disparar = True; dist_x_abs = jugador.x_tile - tanque.x_tile; dist_y_abs = jugador.y_tile - tanque.y_tile
                        if abs(dist_x_abs) > abs(dist_y_abs): tanque.direccion_actual = RIGHT if dist_x_abs > 0 else LEFT
                        elif abs(dist_y_abs) > 0 : tanque.direccion_actual = DOWN if dist_y_abs > 0 else UP
            
            if decision_disparar and tanque.puede_disparar(self.tiempo_ms_juego):
                tanque.registrar_disparo(self.tiempo_ms_juego)
                bala_x = tanque.x_tile + tanque.direccion_actual[0]; bala_y = tanque.y_tile + tanque.direccion_actual[1]
                if 0 <= bala_x < GRID_WIDTH and 0 <= bala_y < GRID_HEIGHT:
                    bala = BalaModel(bala_x, bala_y, tanque.direccion_actual, tanque.id, tanque.tipo_objeto); self._agregar_objeto(bala); self._resolver_colision_inmediata_bala(bala)
            
            tanque.actualizar_contador_movimiento();
            if tanque.accion_actual != STAY:
                if tanque.puede_moverse_este_tick():
                    nueva_x_tile = tanque.x_tile + tanque.accion_actual[0]; nueva_y_tile = tanque.y_tile + tanque.accion_actual[1]
                    if self._es_posicion_valida_y_libre(nueva_x_tile, nueva_y_tile, para_objeto_id=tanque.id, considerar_tanques=True):
                        self._actualizar_mapa_colisiones_objeto(tanque, agregar=False); tanque.x_tile = nueva_x_tile; tanque.y_tile = nueva_y_tile
                        tanque.moviendose_este_tick = True; self._actualizar_mapa_colisiones_objeto(tanque, agregar=True); tanque.registrar_movimiento_exitoso()
                        if usar_dfs_para_jugador and tanque.ruta_actual_tiles and \
                           len(tanque.ruta_actual_tiles) > 0 and isinstance(tanque.ruta_actual_tiles[0], tuple) and len(tanque.ruta_actual_tiles[0]) == 2 and \
                           tanque.x_tile == tanque.ruta_actual_tiles[0][0] and tanque.y_tile == tanque.ruta_actual_tiles[0][1]:
                            tanque.ruta_actual_tiles.pop(0)
            tanque.accion_actual = STAY


        balas_a_quitar_ids = []
        for obj_id, obj in list(self.objetos_del_juego.items()):
            if isinstance(obj, TanqueEnemigoModel) and obj.fue_destruido_visual: continue
            if not obj.activo : continue
            if isinstance(obj, BalaModel):
                bala = obj
                if not bala.activo:
                    if bala.id not in balas_a_quitar_ids: balas_a_quitar_ids.append(bala.id)
                    continue
                bala.distancia_recorrida_tick += VELOCIDAD_BALA
                movimientos_de_bala_este_tick = 0
                while bala.distancia_recorrida_tick >= 1.0 and bala.activo:
                    bala.distancia_recorrida_tick -= 1.0; movimientos_de_bala_este_tick +=1
                    if movimientos_de_bala_este_tick > max(GRID_WIDTH, GRID_HEIGHT) * 2 : bala.activo = False; break
                    nueva_bala_x = bala.x_tile + bala.direccion_vector[0]; nueva_bala_y = bala.y_tile + bala.direccion_vector[1]
                    if not (0 <= nueva_bala_x < GRID_WIDTH and 0 <= nueva_bala_y < GRID_HEIGHT): bala.activo = False; break
                    ids_objetos_en_destino = list(self.mapa_colisiones.get((nueva_bala_x, nueva_bala_y), []))
                    colision_encontrada = False
                    for id_obj_col_destino in ids_objetos_en_destino:
                        obj_col_destino = self.objetos_del_juego.get(id_obj_col_destino)
                        if not obj_col_destino or not obj_col_destino.activo: continue
                        if isinstance(obj_col_destino, TanqueEnemigoModel) and obj_col_destino.fue_destruido_visual: continue

                        if isinstance(obj_col_destino, MuroModel): bala.activo = False; colision_encontrada = True; break
                        elif isinstance(obj_col_destino, TanqueModel) and obj_col_destino.id != bala.propietario_id:
                            bala.activo = False; colision_encontrada = True
                            estaba_activo_antes_del_golpe = obj_col_destino.activo

                            es_jugador_impactado = (obj_col_destino.id == self.jugador_id)
                            propietario_es_enemigo_fuerte = (bala.tipo_propietario == TIPO_ENEMIGO_FUERTE)

                            if es_jugador_impactado and propietario_es_enemigo_fuerte:
                                obj_col_destino.vidas = 0

                            if obj_col_destino.recibir_impacto():
                                if obj_col_destino.id == self.jugador_id and estaba_activo_antes_del_golpe:
                                    if self.player_final_destruction_sound and pygame.mixer.get_init():
                                        try: self.player_final_destruction_sound.play()
                                        except pygame.error as e: print(f"Error al reproducir sonido de explosión final: {e}")
                            break
                        elif isinstance(obj_col_destino, ObjetivoPrimarioModel) and bala.tipo_propietario == TIPO_JUGADOR:
                            bala.activo = False; colision_encontrada = True; obj_col_destino.ser_destruido()
                            break
                    if not colision_encontrada: bala.x_tile = nueva_bala_x; bala.y_tile = nueva_bala_y
                    else: break
                if not bala.activo:
                    if bala.id not in balas_a_quitar_ids: balas_a_quitar_ids.append(bala.id)
        
        for bala_id in balas_a_quitar_ids: self._quitar_objeto(bala_id)

        if not jugador.activo: return GAME_OVER
        if self._todos_objetivos_destruidos():
            if self.es_nivel_editado_actualmente:
                return VICTORIA_FINAL
            elif isinstance(self.nivel_actual_numero, int) and self.nivel_actual_numero < MAX_NIVELES:
                return NIVEL_COMPLETADO
            else:
                return VICTORIA_FINAL
        
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
        """
        Implementación del algoritmo A* para encontrar la ruta más corta.
        Devuelve una lista de tuplas (x, y) representando el camino.
        """
        frontera = [(0, 0, inicio, [])]  # (f, g, pos, camino)
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
            if obj_modelo.activo:
                obj_id = getattr(obj_modelo, 'id', None)
                if obj_id is None: continue
                vista_objetos.append({
                    "id": obj_id, "tipo": obj_modelo.tipo_objeto,
                    "x_tile": obj_modelo.x_tile, "y_tile": obj_modelo.y_tile,
                    "direccion": getattr(obj_modelo, 'direccion_actual', None),
                    "moviendose": getattr(obj_modelo, 'moviendose_este_tick', False)
                })
            elif isinstance(obj_modelo, TanqueEnemigoModel) and obj_modelo.fue_destruido_visual:
                if pygame.time.get_ticks() - obj_modelo.tiempo_destruccion_visual <= obj_modelo.duracion_explosion_visual:
                    enemigos_destruyendose_vista.append({
                        "id": obj_modelo.id,
                        "x_tile": obj_modelo.x_tile,
                        "y_tile": obj_modelo.y_tile,
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