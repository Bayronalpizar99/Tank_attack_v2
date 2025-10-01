# main_multijugador.py
import pygame
import os 
from constantes import ( 
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, UP, DOWN, LEFT, RIGHT, STAY,
    MENU_INICIO, CARGANDO_NIVEL, JUGANDO, NIVEL_COMPLETADO, GAME_OVER, VICTORIA_FINAL, PAUSA, EDITOR_NIVELES,
    MENU_MULTIJUGADOR, CONFIGURANDO_JUGADORES, ESPERANDO_JUGADORES,
    MAX_NIVELES, TIPO_JUGADOR, TIPO_JUGADOR_1, TIPO_JUGADOR_2, TIPO_JUGADOR_3, TIPO_JUGADOR_4,
    MENU_MUSIC_PATH, AMBIENT_LEVEL_MUSIC_PATH, GENERAL_TANK_MOVING_SOUND_PATH, PLAYER_SHOOT_SOUND_PATH,
    PLAYER_FINAL_DESTRUCTION_SOUND_PATH, GAME_OVER_SCREEN_MUSIC_PATH,
    LEVEL_COMPLETE_MUSIC_PATH, FINAL_VICTORY_MUSIC_PATH, ENEMY_DESTRUCTION_IMAGE_PATH,
    EDITOR_NIVELES_PATH, DEFAULT_EDITOR_FILENAME 
)
from backend.motor_juego import MotorJuego 
from multiplayer.motor_multijugador import MotorMultijugador
from multiplayer.player_manager import PlayerManager
from frontend.vista import VistaJuego 

EVENTO_SIGUIENTE_NIVEL = pygame.USEREVENT + 1

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.set_num_channels(16) 
    
    # Cargar sonidos
    sonido_ambiente_tanques_obj = None
    player_shoot_sound_obj = None
    player_final_destruction_sound_obj = None 
    
    if pygame.mixer.get_init(): 
        try: 
            sonido_ambiente_tanques_obj = pygame.mixer.Sound(GENERAL_TANK_MOVING_SOUND_PATH) 
        except pygame.error as e: 
            print(f"Error carga sonido ambiente tanques: {e}")
        try: 
            player_shoot_sound_obj = pygame.mixer.Sound(PLAYER_SHOOT_SOUND_PATH)
            player_shoot_sound_obj.set_volume(0.6) 
        except pygame.error as e: 
            print(f"Error carga sonido disparo: {e}")
        try: 
            player_final_destruction_sound_obj = pygame.mixer.Sound(PLAYER_FINAL_DESTRUCTION_SOUND_PATH)
            player_final_destruction_sound_obj.set_volume(0.8) 
        except pygame.error as e: 
            print(f"Error carga sonido explosión jugador: {e}")

    # Inicializar componentes
    motor_individual = MotorJuego(player_shoot_sound=player_shoot_sound_obj, 
                                 player_final_destruction_sound=player_final_destruction_sound_obj) 
    player_manager = PlayerManager()
    motor_multijugador = MotorMultijugador(player_manager, 
                                          player_shoot_sound=player_shoot_sound_obj,
                                          player_final_destruction_sound=player_final_destruction_sound_obj)
    
    # Motor activo (individual por defecto)
    motor_activo = motor_individual
    modo_multijugador = False
    
    vista = VistaJuego()
    clock = pygame.time.Clock() 
    running = True
    
    # Estados del juego
    estado_global_juego = ""
    nuevo_estado_global_juego = MENU_INICIO
    estado_previo_pausa = JUGANDO 
    
    # Variables de música
    musica_menu_reproduciendo = False
    musica_ambiente_reproduciendo = False
    musica_game_over_reproduciendo = False 
    musica_level_complete_reproduciendo = False
    musica_final_victory_reproduciendo = False 
    sonido_ambiente_tanques_canal = None
    sonido_ambiente_tanques_activo = False
    MASTER_VOLUME_AMBIENTE_TANQUES = 0.3 
    
    motor_activo.nivel_actual_numero = 0 

    while running:
        estado_anterior_real_para_sonidos = estado_global_juego  
        if nuevo_estado_global_juego is not None:
            estado_global_juego = nuevo_estado_global_juego
            nuevo_estado_global_juego = None  
            
            # --- Lógica de Música ---
            if pygame.mixer.get_init(): 
                if musica_menu_reproduciendo and estado_global_juego not in [MENU_INICIO, CONFIGURANDO_JUGADORES]: 
                    pygame.mixer.music.stop()
                    musica_menu_reproduciendo = False 
                if musica_ambiente_reproduciendo and estado_global_juego not in [JUGANDO, PAUSA]: 
                    pygame.mixer.music.stop()
                    musica_ambiente_reproduciendo = False 
                if musica_game_over_reproduciendo and estado_global_juego != GAME_OVER: 
                    pygame.mixer.music.stop()
                    musica_game_over_reproduciendo = False 
                if musica_level_complete_reproduciendo and estado_global_juego != NIVEL_COMPLETADO: 
                    pygame.mixer.music.stop()
                    musica_level_complete_reproduciendo = False 
                if musica_final_victory_reproduciendo and estado_global_juego != VICTORIA_FINAL: 
                    pygame.mixer.music.stop()
                    musica_final_victory_reproduciendo = False 
                
                if (estado_anterior_real_para_sonidos in [JUGANDO, PAUSA] and 
                    estado_global_juego not in [JUGANDO, PAUSA, EDITOR_NIVELES]): 
                    if sonido_ambiente_tanques_canal and sonido_ambiente_tanques_activo: 
                        sonido_ambiente_tanques_canal.stop()
                        sonido_ambiente_tanques_canal = None
                        sonido_ambiente_tanques_activo = False 
                
                if estado_global_juego in [MENU_INICIO, CONFIGURANDO_JUGADORES] and not musica_menu_reproduciendo: 
                    if pygame.mixer.music.get_busy(): 
                        pygame.mixer.music.stop() 
                    try: 
                        pygame.mixer.music.load(MENU_MUSIC_PATH)
                        pygame.mixer.music.set_volume(0.5)
                        pygame.mixer.music.play(loops=-1)
                        musica_menu_reproduciendo = True
                        musica_ambiente_reproduciendo = False
                        musica_game_over_reproduciendo = False
                        musica_level_complete_reproduciendo = False
                        musica_final_victory_reproduciendo = False 
                    except pygame.error as e: 
                        print(f"Error música menú: {e}")
                elif estado_global_juego == JUGANDO: 
                    if not musica_ambiente_reproduciendo:
                        if pygame.mixer.music.get_busy(): 
                            pygame.mixer.music.stop() 
                        try: 
                            pygame.mixer.music.load(AMBIENT_LEVEL_MUSIC_PATH)
                            pygame.mixer.music.set_volume(0.4)
                            pygame.mixer.music.play(loops=-1)
                            musica_ambiente_reproduciendo = True
                            musica_menu_reproduciendo = False
                            musica_game_over_reproduciendo = False
                            musica_level_complete_reproduciendo = False
                            musica_final_victory_reproduciendo = False 
                        except pygame.error as e: 
                            print(f"Error música ambiente: {e}")
                    if sonido_ambiente_tanques_obj and not sonido_ambiente_tanques_activo: 
                        try: 
                            sonido_ambiente_tanques_canal = sonido_ambiente_tanques_obj.play(loops=-1)
                            sonido_ambiente_tanques_canal.set_volume(MASTER_VOLUME_AMBIENTE_TANQUES)
                            sonido_ambiente_tanques_activo = True 
                        except pygame.error as e: 
                            print(f"Error sonido ambiente tanques: {e}")
                elif estado_global_juego == GAME_OVER and not musica_game_over_reproduciendo: 
                    if pygame.mixer.music.get_busy(): 
                        pygame.mixer.music.stop() 
                    try: 
                        pygame.mixer.music.load(GAME_OVER_SCREEN_MUSIC_PATH)
                        pygame.mixer.music.set_volume(0.6)
                        pygame.mixer.music.play(loops=-1)
                        musica_game_over_reproduciendo = True
                        musica_menu_reproduciendo = False
                        musica_ambiente_reproduciendo = False
                        musica_level_complete_reproduciendo = False
                        musica_final_victory_reproduciendo = False 
                    except pygame.error as e: 
                        print(f"Error música Game Over: {e}")
                elif estado_global_juego == NIVEL_COMPLETADO and not musica_level_complete_reproduciendo: 
                    if pygame.mixer.music.get_busy(): 
                        pygame.mixer.music.stop() 
                    try: 
                        pygame.mixer.music.load(LEVEL_COMPLETE_MUSIC_PATH)
                        pygame.mixer.music.set_volume(0.6)
                        pygame.mixer.music.play(loops=0)
                        musica_level_complete_reproduciendo = True
                        musica_menu_reproduciendo = False
                        musica_ambiente_reproduciendo = False
                        musica_game_over_reproduciendo = False
                        musica_final_victory_reproduciendo = False 
                    except pygame.error as e: 
                        print(f"Error música Nivel Completado: {e}")
                elif estado_global_juego == VICTORIA_FINAL and not musica_final_victory_reproduciendo: 
                    if pygame.mixer.music.get_busy(): 
                        pygame.mixer.music.stop() 
                    try: 
                        pygame.mixer.music.load(FINAL_VICTORY_MUSIC_PATH)
                        pygame.mixer.music.set_volume(0.7)
                        pygame.mixer.music.play(loops=-1)
                        musica_final_victory_reproduciendo = True
                        musica_menu_reproduciendo = False
                        musica_ambiente_reproduciendo = False
                        musica_game_over_reproduciendo = False
                        musica_level_complete_reproduciendo = False 
                    except pygame.error as e: 
                        print(f"Error música Victoria Final: {e}")
                elif estado_global_juego == EDITOR_NIVELES: 
                    if musica_ambiente_reproduciendo: 
                        pygame.mixer.music.stop()
                        musica_ambiente_reproduciendo = False
                    if sonido_ambiente_tanques_canal and sonido_ambiente_tanques_activo: 
                        sonido_ambiente_tanques_canal.stop()
                        sonido_ambiente_tanques_canal = None
                        sonido_ambiente_tanques_activo = False
                    if (not musica_menu_reproduciendo and 
                        estado_anterior_real_para_sonidos == MENU_INICIO):
                         if pygame.mixer.music.get_busy(): 
                             pygame.mixer.music.stop()
                         try: 
                             pygame.mixer.music.load(MENU_MUSIC_PATH)
                             pygame.mixer.music.set_volume(0.5)
                             pygame.mixer.music.play(loops=-1)
                             musica_menu_reproduciendo = True
                         except pygame.error as e: 
                             print(f"Error música menú (editor): {e}")

        # Procesar eventos
        acciones_jugador = {}  # Para modo individual
        acciones_todos_jugadores = {}  # Para modo multijugador
        accion_ui_raw = None

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: 
                running = False
            
            accion_ui_raw_temp = vista.manejar_eventos_ui(evento, estado_global_juego, player_manager) 
            if accion_ui_raw_temp: 
                accion_ui_raw = accion_ui_raw_temp 
            
            if estado_global_juego == JUGANDO: 
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE: 
                        nuevo_estado_global_juego = PAUSA
                        estado_previo_pausa = JUGANDO 
                    elif not modo_multijugador:
                        # Modo individual - usar las teclas originales
                        if evento.key == pygame.K_SPACE: 
                            acciones_jugador["disparar"] = True 
                        elif evento.key == pygame.K_x: 
                            acciones_jugador["detenerse"] = True 
            elif estado_global_juego == PAUSA: 
                 if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE: 
                    nuevo_estado_global_juego = estado_previo_pausa 
            elif estado_global_juego == EDITOR_NIVELES: 
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    if vista.editor_manager and not vista.editor_manager.is_typing_filename: 
                         accion_ui_raw = "ir_a_menu_desde_editor"

            if evento.type == EVENTO_SIGUIENTE_NIVEL: 
                if estado_global_juego == NIVEL_COMPLETADO: 
                    pygame.time.set_timer(EVENTO_SIGUIENTE_NIVEL, 0)
                    if isinstance(motor_activo.nivel_actual_numero, int):
                        motor_activo.nivel_actual_numero += 1
                    else: 
                        print("Nivel editado completado. Volviendo al menú.")
                        nuevo_estado_global_juego = MENU_INICIO
                        motor_activo.nivel_actual_numero = 0
                        continue 
                    nuevo_estado_global_juego = CARGANDO_NIVEL
        
        # Procesar entrada de teclado para el juego
        if estado_global_juego == JUGANDO: 
            teclas_presionadas = pygame.key.get_pressed()
            
            if modo_multijugador:
                # Procesar entrada para todos los jugadores activos
                for player in player_manager.get_active_players():
                    acciones_player = player_manager.process_input(teclas_presionadas, player.player_id)
                    if acciones_player:
                        acciones_todos_jugadores[player.player_id] = acciones_player
            else:
                # Modo individual - usar las teclas originales
                direccion_movimiento_jugador = None
                if not acciones_jugador.get("detenerse"):  
                    if teclas_presionadas[pygame.K_LEFT]: 
                        direccion_movimiento_jugador = LEFT 
                    elif teclas_presionadas[pygame.K_RIGHT]: 
                        direccion_movimiento_jugador = RIGHT 
                    elif teclas_presionadas[pygame.K_UP]: 
                        direccion_movimiento_jugador = UP 
                    elif teclas_presionadas[pygame.K_DOWN]: 
                        direccion_movimiento_jugador = DOWN 
                if direccion_movimiento_jugador: 
                    acciones_jugador["mover"] = direccion_movimiento_jugador

        # Procesar acciones de UI
        nombre_accion = None
        datos_accion = None

        if isinstance(accion_ui_raw, tuple):
            nombre_accion, datos_accion = accion_ui_raw
        elif isinstance(accion_ui_raw, str):
            nombre_accion = accion_ui_raw
        
        if nombre_accion:
            if nombre_accion == "iniciar_juego_procedural": 
                motor_activo = motor_individual
                modo_multijugador = False
                motor_activo.nivel_actual_numero = 1 
                nuevo_estado_global_juego = CARGANDO_NIVEL
            elif nombre_accion == "abrir_multijugador":
                nuevo_estado_global_juego = CONFIGURANDO_JUGADORES
            elif nombre_accion == "agregar_jugador":
                # Agregar jugador si hay espacio
                current_players = len(player_manager.get_all_players())
                if current_players < 4:
                    next_id = current_players + 1
                    if player_manager.add_player(next_id):
                        print(f"Jugador {next_id} agregado")
            elif nombre_accion == "quitar_jugador":
                # Quitar el último jugador
                players = player_manager.get_all_players()
                if players:
                    last_player = max(players, key=lambda p: p.player_id)
                    if player_manager.remove_player(last_player.player_id):
                        print(f"Jugador {last_player.player_id} eliminado")
            elif nombre_accion == "iniciar_partida_multijugador":
                if len(player_manager.get_all_players()) >= 2:
                    motor_activo = motor_multijugador
                    modo_multijugador = True
                    motor_activo.nivel_actual_numero = 1
                    nuevo_estado_global_juego = CARGANDO_NIVEL
                else:
                    print("Se necesitan al menos 2 jugadores para modo multijugador")
            elif nombre_accion == "volver_menu_principal":
                nuevo_estado_global_juego = MENU_INICIO
                # Limpiar jugadores
                player_manager = PlayerManager()
            elif nombre_accion == "jugar_nivel_especifico":
                if datos_accion:
                    motor_activo.nivel_actual_numero = os.path.join(EDITOR_NIVELES_PATH, datos_accion + ".txt")
                    nuevo_estado_global_juego = CARGANDO_NIVEL
                    if hasattr(vista, 'mostrando_selector_nivel_editado'):
                        vista.mostrando_selector_nivel_editado = False
            elif nombre_accion == "abrir_selector_nivel":
                 pass
            elif nombre_accion == "refrescar_menu":
                 pass
            elif nombre_accion == "abrir_editor":
                nuevo_estado_global_juego = EDITOR_NIVELES
            elif nombre_accion == "ir_a_menu_desde_editor":
                nuevo_estado_global_juego = MENU_INICIO
                motor_activo.nivel_actual_numero = 0 
            elif nombre_accion == "siguiente_nivel": 
                if isinstance(motor_activo.nivel_actual_numero, int): 
                    motor_activo.nivel_actual_numero += 1 
                else: 
                    nuevo_estado_global_juego = MENU_INICIO
                    motor_activo.nivel_actual_numero = 0
                if nuevo_estado_global_juego != MENU_INICIO:
                    nuevo_estado_global_juego = CARGANDO_NIVEL
            elif nombre_accion == "reintentar_nivel": 
                nuevo_estado_global_juego = CARGANDO_NIVEL 
            elif nombre_accion == "reanudar_juego": 
                nuevo_estado_global_juego = estado_previo_pausa 
            elif nombre_accion == "reintentar_nivel_pausa": 
                nuevo_estado_global_juego = CARGANDO_NIVEL 
            elif nombre_accion in ["ir_a_menu", "ir_a_menu_pausa"]: 
                nuevo_estado_global_juego = MENU_INICIO
                motor_activo.nivel_actual_numero = 0
                # Resetear modo
                motor_activo = motor_individual
                modo_multijugador = False
                player_manager = PlayerManager()
            elif nombre_accion == "salir_juego": 
                running = False 
        
        # Lógica de estados
        if estado_global_juego == CARGANDO_NIVEL: 
            if isinstance(motor_activo.nivel_actual_numero, int): 
                if 0 < motor_activo.nivel_actual_numero <= MAX_NIVELES: 
                    if motor_activo.cargar_nivel(motor_activo.nivel_actual_numero):
                        nuevo_estado_global_juego = JUGANDO
                        estado_previo_pausa = JUGANDO 
                    else: 
                        nuevo_estado_global_juego = MENU_INICIO
                        motor_activo.nivel_actual_numero = 0
                else: 
                     nuevo_estado_global_juego = MENU_INICIO
                     motor_activo.nivel_actual_numero = 0 
            elif isinstance(motor_activo.nivel_actual_numero, str): 
                if motor_activo.cargar_nivel(motor_activo.nivel_actual_numero): 
                    nuevo_estado_global_juego = JUGANDO
                    estado_previo_pausa = JUGANDO
                else: 
                    print(f"Error: No se pudo cargar el nivel desde {motor_activo.nivel_actual_numero}. Volviendo al menú.")
                    nuevo_estado_global_juego = MENU_INICIO
                    motor_activo.nivel_actual_numero = 0
            else: 
                 nuevo_estado_global_juego = MENU_INICIO
                 motor_activo.nivel_actual_numero = 0
        
        elif estado_global_juego == JUGANDO: 
            tiempo_delta_ms = clock.get_time() 
            if modo_multijugador:
                resultado_actualizacion = motor_activo.actualizar_estado(acciones_todos_jugadores, tiempo_delta_ms)
            else:
                resultado_actualizacion = motor_activo.actualizar_estado(acciones_jugador, tiempo_delta_ms) 
            if resultado_actualizacion != JUGANDO: 
                nuevo_estado_global_juego = resultado_actualizacion 
        
        elif estado_global_juego == EDITOR_NIVELES:
            pass

        # Obtener estado para la vista
        if estado_global_juego not in [EDITOR_NIVELES, MENU_INICIO, CONFIGURANDO_JUGADORES] or (estado_global_juego == MENU_INICIO and not vista.mostrando_selector_nivel_editado):
            if estado_global_juego in [JUGANDO, PAUSA, NIVEL_COMPLETADO, GAME_OVER, VICTORIA_FINAL]:
                estado_para_vista = motor_activo.get_estado_para_vista() 
            else:
                estado_para_vista = None
        else:
            estado_para_vista = None 

        # Manejo de sonido ambiente (adaptado para múltiples jugadores)
        if (pygame.mixer.get_init() and estado_global_juego == JUGANDO and 
            sonido_ambiente_tanques_canal and sonido_ambiente_tanques_activo): 
            
            if modo_multijugador and estado_para_vista and "jugadores" in estado_para_vista:
                # Usar el primer jugador activo para el sonido
                jugadores_info = estado_para_vista["jugadores"]
                if jugadores_info:
                    first_player_id = next(iter(jugadores_info.keys()))
                    # Buscar la posición del tanque de este jugador en los objetos
                    for obj_vista in estado_para_vista.get("objetos", []):
                        if obj_vista["tipo"] in [TIPO_JUGADOR_1, TIPO_JUGADOR_2, TIPO_JUGADOR_3, TIPO_JUGADOR_4]:
                            player_x_tile_vista = obj_vista["x_tile"]
                            player_screen_x = player_x_tile_vista * TILE_SIZE 
                            pan_factor = (player_screen_x - (SCREEN_WIDTH / 2)) / (SCREEN_WIDTH / 2)
                            pan_factor = max(-1.0, min(1.0, pan_factor)) 
                            vol_izq_pan = 1.0
                            vol_der_pan = 1.0 
                            if pan_factor < 0: 
                                vol_der_pan = 1.0 + pan_factor  
                            elif pan_factor > 0: 
                                vol_izq_pan = 1.0 - pan_factor   
                            vol_final_izq = MASTER_VOLUME_AMBIENTE_TANQUES * vol_izq_pan
                            vol_final_der = MASTER_VOLUME_AMBIENTE_TANQUES * vol_der_pan 
                            vol_final_izq = max(0.0, min(1.0, vol_final_izq))
                            vol_final_der = max(0.0, min(1.0, vol_final_der)) 
                            sonido_ambiente_tanques_canal.set_volume(vol_final_izq, vol_final_der)
                            break
            elif not modo_multijugador:
                # Lógica original para modo individual
                player_x_tile_vista = None
                player_found_in_vista = False 
                if estado_para_vista and "objetos" in estado_para_vista: 
                    for obj_vista in estado_para_vista["objetos"]: 
                        if obj_vista["tipo"] == TIPO_JUGADOR: 
                            player_x_tile_vista = obj_vista["x_tile"]
                            player_found_in_vista = True
                            break 
                if player_found_in_vista and player_x_tile_vista is not None: 
                    player_screen_x = player_x_tile_vista * TILE_SIZE 
                    pan_factor = (player_screen_x - (SCREEN_WIDTH / 2)) / (SCREEN_WIDTH / 2)
                    pan_factor = max(-1.0, min(1.0, pan_factor)) 
                    vol_izq_pan = 1.0
                    vol_der_pan = 1.0 
                    if pan_factor < 0: 
                        vol_der_pan = 1.0 + pan_factor  
                    elif pan_factor > 0: 
                        vol_izq_pan = 1.0 - pan_factor   
                    vol_final_izq = MASTER_VOLUME_AMBIENTE_TANQUES * vol_izq_pan
                    vol_final_der = MASTER_VOLUME_AMBIENTE_TANQUES * vol_der_pan 
                    vol_final_izq = max(0.0, min(1.0, vol_final_izq))
                    vol_final_der = max(0.0, min(1.0, vol_final_der)) 
                    sonido_ambiente_tanques_canal.set_volume(vol_final_izq, vol_final_der) 
                elif sonido_ambiente_tanques_canal: 
                    sonido_ambiente_tanques_canal.set_volume(MASTER_VOLUME_AMBIENTE_TANQUES) 

        vista.dibujar_estado_juego(estado_para_vista, estado_global_juego, player_manager) 
        clock.tick(30)

    # Limpieza al salir
    if pygame.mixer.get_init(): 
        if sonido_ambiente_tanques_canal: 
            sonido_ambiente_tanques_canal.stop() 
        pygame.mixer.music.stop() 
        pygame.mixer.quit() 
    pygame.quit()


if __name__ == '__main__':
    main()