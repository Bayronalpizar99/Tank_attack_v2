# main.py
import pygame
import os 
from constantes import ( 
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, UP, DOWN, LEFT, RIGHT, STAY, #
    MENU_INICIO, CARGANDO_NIVEL, JUGANDO, NIVEL_COMPLETADO, GAME_OVER, VICTORIA_FINAL, PAUSA, EDITOR_NIVELES, #
    MAX_NIVELES, TIPO_JUGADOR, #
    MENU_MUSIC_PATH, AMBIENT_LEVEL_MUSIC_PATH, GENERAL_TANK_MOVING_SOUND_PATH, PLAYER_SHOOT_SOUND_PATH, #
    PLAYER_FINAL_DESTRUCTION_SOUND_PATH, GAME_OVER_SCREEN_MUSIC_PATH, #
    LEVEL_COMPLETE_MUSIC_PATH, FINAL_VICTORY_MUSIC_PATH, ENEMY_DESTRUCTION_IMAGE_PATH, #
    EDITOR_NIVELES_PATH, DEFAULT_EDITOR_FILENAME 
)
from backend.motor_juego import MotorJuego 
from frontend.vista import VistaJuego 

EVENTO_SIGUIENTE_NIVEL = pygame.USEREVENT + 1

def main():
    pygame.init(); pygame.mixer.init(); pygame.mixer.set_num_channels(16) 
    sonido_ambiente_tanques_obj = None; player_shoot_sound_obj = None; player_final_destruction_sound_obj = None 
    if pygame.mixer.get_init(): 
        try: sonido_ambiente_tanques_obj = pygame.mixer.Sound(GENERAL_TANK_MOVING_SOUND_PATH) 
        except pygame.error as e: print(f"Error carga sonido ambiente tanques: {e}")
        try: player_shoot_sound_obj = pygame.mixer.Sound(PLAYER_SHOOT_SOUND_PATH); player_shoot_sound_obj.set_volume(0.6) 
        except pygame.error as e: print(f"Error carga sonido disparo: {e}")
        try: player_final_destruction_sound_obj = pygame.mixer.Sound(PLAYER_FINAL_DESTRUCTION_SOUND_PATH); player_final_destruction_sound_obj.set_volume(0.8) 
        except pygame.error as e: print(f"Error carga sonido explosión jugador: {e}")

    motor = MotorJuego(player_shoot_sound=player_shoot_sound_obj, player_final_destruction_sound=player_final_destruction_sound_obj) 
    vista = VistaJuego(); clock = pygame.time.Clock() 
    running = True
    estado_global_juego = ""; nuevo_estado_global_juego = MENU_INICIO; estado_previo_pausa = JUGANDO 
    musica_menu_reproduciendo = False; musica_ambiente_reproduciendo = False; musica_game_over_reproduciendo = False 
    musica_level_complete_reproduciendo = False; musica_final_victory_reproduciendo = False 
    sonido_ambiente_tanques_canal = None; sonido_ambiente_tanques_activo = False; MASTER_VOLUME_AMBIENTE_TANQUES = 0.3 
    
    motor.nivel_actual_numero = 0 

    while running:
        estado_anterior_real_para_sonidos = estado_global_juego  
        if nuevo_estado_global_juego is not None:
            estado_global_juego = nuevo_estado_global_juego; nuevo_estado_global_juego = None  
            # --- Lógica de Música ---
            if pygame.mixer.get_init(): 
                if musica_menu_reproduciendo and estado_global_juego != MENU_INICIO: pygame.mixer.music.stop(); musica_menu_reproduciendo = False 
                if musica_ambiente_reproduciendo and estado_global_juego not in [JUGANDO, PAUSA]: pygame.mixer.music.stop(); musica_ambiente_reproduciendo = False 
                if musica_game_over_reproduciendo and estado_global_juego != GAME_OVER: pygame.mixer.music.stop(); musica_game_over_reproduciendo = False 
                if musica_level_complete_reproduciendo and estado_global_juego != NIVEL_COMPLETADO: pygame.mixer.music.stop(); musica_level_complete_reproduciendo = False 
                if musica_final_victory_reproduciendo and estado_global_juego != VICTORIA_FINAL: pygame.mixer.music.stop(); musica_final_victory_reproduciendo = False 
                
                if estado_anterior_real_para_sonidos in [JUGANDO, PAUSA] and estado_global_juego not in [JUGANDO, PAUSA, EDITOR_NIVELES]: 
                    if sonido_ambiente_tanques_canal and sonido_ambiente_tanques_activo: sonido_ambiente_tanques_canal.stop(); sonido_ambiente_tanques_canal = None; sonido_ambiente_tanques_activo = False 
                
                if estado_global_juego == MENU_INICIO and not musica_menu_reproduciendo: 
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop() 
                    try: pygame.mixer.music.load(MENU_MUSIC_PATH); pygame.mixer.music.set_volume(0.5); pygame.mixer.music.play(loops=-1); musica_menu_reproduciendo = True; musica_ambiente_reproduciendo = False; musica_game_over_reproduciendo = False; musica_level_complete_reproduciendo = False; musica_final_victory_reproduciendo = False 
                    except pygame.error as e: print(f"Error música menú: {e}")
                elif estado_global_juego == JUGANDO: 
                    if not musica_ambiente_reproduciendo:
                        if pygame.mixer.music.get_busy(): pygame.mixer.music.stop() 
                        try: pygame.mixer.music.load(AMBIENT_LEVEL_MUSIC_PATH); pygame.mixer.music.set_volume(0.4); pygame.mixer.music.play(loops=-1); musica_ambiente_reproduciendo = True; musica_menu_reproduciendo = False; musica_game_over_reproduciendo = False; musica_level_complete_reproduciendo = False; musica_final_victory_reproduciendo = False 
                        except pygame.error as e: print(f"Error música ambiente: {e}")
                    if sonido_ambiente_tanques_obj and not sonido_ambiente_tanques_activo: 
                        try: sonido_ambiente_tanques_canal = sonido_ambiente_tanques_obj.play(loops=-1); sonido_ambiente_tanques_canal.set_volume(MASTER_VOLUME_AMBIENTE_TANQUES); sonido_ambiente_tanques_activo = True 
                        except pygame.error as e: print(f"Error sonido ambiente tanques: {e}")
                elif estado_global_juego == GAME_OVER and not musica_game_over_reproduciendo: 
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop() 
                    try: pygame.mixer.music.load(GAME_OVER_SCREEN_MUSIC_PATH); pygame.mixer.music.set_volume(0.6); pygame.mixer.music.play(loops=-1); musica_game_over_reproduciendo = True; musica_menu_reproduciendo = False; musica_ambiente_reproduciendo = False; musica_level_complete_reproduciendo = False; musica_final_victory_reproduciendo = False 
                    except pygame.error as e: print(f"Error música Game Over: {e}")
                elif estado_global_juego == NIVEL_COMPLETADO and not musica_level_complete_reproduciendo: 
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop() 
                    try: pygame.mixer.music.load(LEVEL_COMPLETE_MUSIC_PATH); pygame.mixer.music.set_volume(0.6); pygame.mixer.music.play(loops=0); musica_level_complete_reproduciendo = True; musica_menu_reproduciendo = False; musica_ambiente_reproduciendo = False; musica_game_over_reproduciendo = False; musica_final_victory_reproduciendo = False 
                    except pygame.error as e: print(f"Error música Nivel Completado: {e}")
                elif estado_global_juego == VICTORIA_FINAL and not musica_final_victory_reproduciendo: 
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop() 
                    try: pygame.mixer.music.load(FINAL_VICTORY_MUSIC_PATH); pygame.mixer.music.set_volume(0.7); pygame.mixer.music.play(loops=-1); musica_final_victory_reproduciendo = True; musica_menu_reproduciendo = False; musica_ambiente_reproduciendo = False; musica_game_over_reproduciendo = False; musica_level_complete_reproduciendo = False 
                    except pygame.error as e: print(f"Error música Victoria Final: {e}")
                elif estado_global_juego == EDITOR_NIVELES: 
                    if musica_ambiente_reproduciendo: pygame.mixer.music.stop(); musica_ambiente_reproduciendo = False
                    if sonido_ambiente_tanques_canal and sonido_ambiente_tanques_activo: sonido_ambiente_tanques_canal.stop(); sonido_ambiente_tanques_canal = None; sonido_ambiente_tanques_activo = False
                    if not musica_menu_reproduciendo and estado_anterior_real_para_sonidos == MENU_INICIO:
                         if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                         try: pygame.mixer.music.load(MENU_MUSIC_PATH); pygame.mixer.music.set_volume(0.5); pygame.mixer.music.play(loops=-1); musica_menu_reproduciendo = True
                         except pygame.error as e: print(f"Error música menú (editor): {e}")


        acciones_jugador = {}  
        accion_ui_raw = None # Renombrado para distinguir de la tupla

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT: running = False
            
            accion_ui_raw_temp = vista.manejar_eventos_ui(evento, estado_global_juego) 
            if accion_ui_raw_temp: accion_ui_raw = accion_ui_raw_temp 
            
            if estado_global_juego == JUGANDO: 
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE: 
                        nuevo_estado_global_juego = PAUSA; estado_previo_pausa = JUGANDO 
                    elif evento.key == pygame.K_SPACE: acciones_jugador["disparar"] = True 
                    elif evento.key == pygame.K_x: acciones_jugador["detenerse"] = True 
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
                    if isinstance(motor.nivel_actual_numero, int):
                        motor.nivel_actual_numero +=1
                    else: 
                        print("Nivel editado completado. Volviendo al menú.")
                        nuevo_estado_global_juego = MENU_INICIO
                        motor.nivel_actual_numero = 0
                        continue 
                    nuevo_estado_global_juego = CARGANDO_NIVEL
        
        if estado_global_juego == JUGANDO: 
            teclas_presionadas = pygame.key.get_pressed()
            direccion_movimiento_jugador = None
            if not acciones_jugador.get("detenerse"):  
                if teclas_presionadas[pygame.K_LEFT]: direccion_movimiento_jugador = LEFT 
                elif teclas_presionadas[pygame.K_RIGHT]: direccion_movimiento_jugador = RIGHT 
                elif teclas_presionadas[pygame.K_UP]: direccion_movimiento_jugador = UP 
                elif teclas_presionadas[pygame.K_DOWN]: direccion_movimiento_jugador = DOWN 
            if direccion_movimiento_jugador: acciones_jugador["mover"] = direccion_movimiento_jugador

        # Procesar accion_ui_raw (puede ser string o tupla)
        nombre_accion = None
        datos_accion = None

        if isinstance(accion_ui_raw, tuple):
            nombre_accion, datos_accion = accion_ui_raw
        elif isinstance(accion_ui_raw, str):
            nombre_accion = accion_ui_raw
        
        if nombre_accion:
            if nombre_accion == "iniciar_juego_procedural": 
                motor.nivel_actual_numero = 1 
                nuevo_estado_global_juego = CARGANDO_NIVEL 
            elif nombre_accion == "jugar_nivel_especifico": # Nueva acción
                if datos_accion: # datos_accion es el nombre base del archivo
                    motor.nivel_actual_numero = os.path.join(EDITOR_NIVELES_PATH, datos_accion + ".txt")
                    nuevo_estado_global_juego = CARGANDO_NIVEL
                    if hasattr(vista, 'mostrando_selector_nivel_editado'): # Resetear vista del selector
                        vista.mostrando_selector_nivel_editado = False
                else:
                    print("Error: Intento de jugar nivel específico sin nombre de archivo.")
            elif nombre_accion == "abrir_selector_nivel": # Manejado por la vista, solo para claridad
                 pass # La vista ya cambió su estado interno
            elif nombre_accion == "refrescar_menu": # Para cuando se vuelve del selector
                 pass # Solo permite que el menú se redibuje sin el selector
            elif nombre_accion == "abrir_editor":
                nuevo_estado_global_juego = EDITOR_NIVELES
            elif nombre_accion == "ir_a_menu_desde_editor":
                nuevo_estado_global_juego = MENU_INICIO
                motor.nivel_actual_numero = 0 
            elif nombre_accion == "siguiente_nivel": 
                if isinstance(motor.nivel_actual_numero, int): 
                    motor.nivel_actual_numero +=1 
                else: 
                    nuevo_estado_global_juego = MENU_INICIO
                    motor.nivel_actual_numero = 0
                if nuevo_estado_global_juego != MENU_INICIO:
                    nuevo_estado_global_juego = CARGANDO_NIVEL
            elif nombre_accion == "reintentar_nivel": nuevo_estado_global_juego = CARGANDO_NIVEL 
            elif nombre_accion == "reanudar_juego": nuevo_estado_global_juego = estado_previo_pausa 
            elif nombre_accion == "reintentar_nivel_pausa": nuevo_estado_global_juego = CARGANDO_NIVEL 
            elif nombre_accion == "ir_a_menu" or nombre_accion == "ir_a_menu_pausa": nuevo_estado_global_juego = MENU_INICIO; motor.nivel_actual_numero = 0 
            elif nombre_accion == "salir_juego": running = False 
        
        if estado_global_juego == CARGANDO_NIVEL: 
            if isinstance(motor.nivel_actual_numero, int): 
                if 0 < motor.nivel_actual_numero <= MAX_NIVELES: 
                    if motor.cargar_nivel(motor.nivel_actual_numero):
                        nuevo_estado_global_juego = JUGANDO; estado_previo_pausa = JUGANDO 
                    else: 
                        nuevo_estado_global_juego = MENU_INICIO; motor.nivel_actual_numero = 0
                else: 
                     nuevo_estado_global_juego = MENU_INICIO; motor.nivel_actual_numero = 0 
            elif isinstance(motor.nivel_actual_numero, str): 
                if motor.cargar_nivel(motor.nivel_actual_numero): 
                    nuevo_estado_global_juego = JUGANDO; estado_previo_pausa = JUGANDO
                else: 
                    print(f"Error: No se pudo cargar el nivel desde {motor.nivel_actual_numero}. Volviendo al menú.")
                    nuevo_estado_global_juego = MENU_INICIO; motor.nivel_actual_numero = 0
            else: 
                 nuevo_estado_global_juego = MENU_INICIO; motor.nivel_actual_numero = 0
        
        elif estado_global_juego == JUGANDO: 
            tiempo_delta_ms = clock.get_time() 
            resultado_actualizacion = motor.actualizar_estado(acciones_jugador, tiempo_delta_ms) 
            if resultado_actualizacion != JUGANDO: nuevo_estado_global_juego = resultado_actualizacion 
        
        elif estado_global_juego == EDITOR_NIVELES:
            pass


        if estado_global_juego != EDITOR_NIVELES and not (estado_global_juego == MENU_INICIO and vista.mostrando_selector_nivel_editado):
            estado_para_vista = motor.get_estado_para_vista() 
        else:
            estado_para_vista = None 

        if pygame.mixer.get_init() and estado_global_juego == JUGANDO and sonido_ambiente_tanques_canal and sonido_ambiente_tanques_activo: 
            player_x_tile_vista = None; player_found_in_vista = False 
            if estado_para_vista and "objetos" in estado_para_vista: 
                for obj_vista in estado_para_vista["objetos"]: 
                    if obj_vista["tipo"] == TIPO_JUGADOR: player_x_tile_vista = obj_vista["x_tile"]; player_found_in_vista = True; break 
            if player_found_in_vista and player_x_tile_vista is not None: 
                player_screen_x = player_x_tile_vista * TILE_SIZE 
                pan_factor = (player_screen_x - (SCREEN_WIDTH / 2)) / (SCREEN_WIDTH / 2); pan_factor = max(-1.0, min(1.0, pan_factor)) 
                vol_izq_pan = 1.0; vol_der_pan = 1.0 
                if pan_factor < 0: vol_der_pan = 1.0 + pan_factor  
                elif pan_factor > 0: vol_izq_pan = 1.0 - pan_factor   
                vol_final_izq = MASTER_VOLUME_AMBIENTE_TANQUES * vol_izq_pan; vol_final_der = MASTER_VOLUME_AMBIENTE_TANQUES * vol_der_pan 
                vol_final_izq = max(0.0, min(1.0, vol_final_izq)); vol_final_der = max(0.0, min(1.0, vol_final_der)) 
                sonido_ambiente_tanques_canal.set_volume(vol_final_izq, vol_final_der) 
            elif sonido_ambiente_tanques_canal: sonido_ambiente_tanques_canal.set_volume(MASTER_VOLUME_AMBIENTE_TANQUES) 

        vista.dibujar_estado_juego(estado_para_vista, estado_global_juego) 
        clock.tick(30)

    if pygame.mixer.get_init(): 
        if sonido_ambiente_tanques_canal: sonido_ambiente_tanques_canal.stop() 
        pygame.mixer.music.stop() 
        pygame.mixer.quit() 
    pygame.quit()


if __name__ == '__main__':
    main()