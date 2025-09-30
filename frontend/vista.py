# frontend/vista.py
import pygame
import os 
from constantes import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, BLACK, WHITE, GREY, GREEN, RED, GOLD, BLUE, 
    PLAYER_TANK_IMG, ENEMY_NORMAL_IMG, ENEMY_RAPIDO_IMG, ENEMY_FUERTE_IMG, 
    BULLET_IMG, WALL_IMG, TARGET1_IMG, TARGET2_IMG, 
    ENEMY_DESTRUCTION_IMAGE_PATH, 
    TIPO_JUGADOR, TIPO_ENEMIGO_NORMAL, TIPO_ENEMIGO_RAPIDO, TIPO_ENEMIGO_FUERTE, 
    TIPO_BALA, TIPO_MURO, TIPO_OBJETIVO1, TIPO_OBJETIVO2, 
    MENU_INICIO, JUGANDO, NIVEL_COMPLETADO, GAME_OVER, VICTORIA_FINAL, PAUSA, EDITOR_NIVELES, 
    DEFAULT_EDITOR_FILENAME, EDITOR_NIVELES_PATH, EDITOR_CHAR_VACIO, EDITOR_DISPLAY_TILE_SIZE, 
    EDITOR_COLOR_CURSOR, EDITOR_COLOR_TEXTO_INFO, EDITOR_COLOR_FONDO_INPUT, EDITOR_COLOR_TEXTO_INPUT,
    EDITOR_PLACABLE_CHARS
)
from frontend.ui_elementos import Boton 
from editor_manager import EditorManager 

class VistaJuego:
    def __init__(self):
        pygame.init()
        pygame.font.init() 
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tank Attack MVC") 
        self.fuente_hud = pygame.font.Font(None, 36) 
        self.fuente_mensajes = pygame.font.Font(None, 72) 
        self.fuente_editor_info = pygame.font.Font(None, 28) 
        self.fuente_selector_nivel = pygame.font.Font(None, 40) 
        self.assets = self._cargar_assets()

        self.sprites_visuales = pygame.sprite.Group() 
        self.objetos_visuales_map = {} 

        self.editor_manager = None 

        self.mostrando_selector_nivel_editado = False
        self.lista_nombres_niveles_editados = [] 
        self.botones_niveles_editados = [] 
        self.nivel_editado_seleccionado_nombre = None 
        self.scroll_offset_selector = 0
        self.max_niveles_visibles_selector = 8 

        y_menu_start = SCREEN_HEIGHT // 2 - 120
        menu_button_height = 50
        menu_button_spacing = 20

        self.boton_inicio = Boton("Iniciar Juego (Nivel 1)", SCREEN_WIDTH // 2 - 150, y_menu_start, 300, menu_button_height)
        self.boton_cargar_nivel_editado_abrir_selector = Boton("Seleccionar Nivel Editado", SCREEN_WIDTH // 2 - 150, y_menu_start + (menu_button_height + menu_button_spacing), 300, menu_button_height)
        self.boton_abrir_editor = Boton("Editor de Niveles", SCREEN_WIDTH // 2 - 150, y_menu_start + 2 * (menu_button_height + menu_button_spacing), 300, menu_button_height)
        self.boton_salir_juego_principal = Boton("Salir del Juego", SCREEN_WIDTH // 2 - 150, y_menu_start + 3 * (menu_button_height + menu_button_spacing), 300, menu_button_height)
        
        selector_button_y = SCREEN_HEIGHT - 80
        self.boton_jugar_nivel_seleccionado = Boton("Jugar Seleccionado", SCREEN_WIDTH // 2 - 220, selector_button_y, 200, 50, color_fondo=GREEN)
        self.boton_volver_de_seleccion_a_menu = Boton("Volver al Menú", SCREEN_WIDTH // 2 + 20, selector_button_y, 200, 50, color_fondo=RED)

        self.boton_siguiente_nivel = Boton("Siguiente Nivel", SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 20, 240, 50)
        self.boton_reintentar = Boton("Reintentar", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 25, 200, 50)
        self.boton_salir_menu_gameover = Boton("Salir al Menú", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 45, 200, 50)
        
        self.boton_reanudar_pausa = Boton("Reanudar", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 80, 200, 50)
        self.boton_reiniciar_pausa = Boton("Reiniciar Nivel", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 10, 200, 50)
        self.boton_salir_menu_pausa = Boton("Salir al Menú", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 60, 200, 50)

        self.boton_salir_editor_a_menu = Boton("Volver al Menú Principal", SCREEN_WIDTH - 220, SCREEN_HEIGHT - 70, 200, 50, color_fondo=(0,100,200))

        self._actualizar_visibilidad_botones(MENU_INICIO)

    def _cargar_assets(self): 
        assets = {}
        def cargar_o_crear_placeholder(ruta_img, color_placeholder, ancho=TILE_SIZE, alto=TILE_SIZE): 
            try:
                img = pygame.image.load(ruta_img).convert_alpha()
                return pygame.transform.scale(img, (ancho, alto))
            except pygame.error as e: 
                print(f"Advertencia: No se pudo cargar la imagen '{ruta_img}'. Creando placeholder. Error: {e}")
                surf = pygame.Surface((ancho, alto))
                surf.fill(color_placeholder)
                return surf

        assets[PLAYER_TANK_IMG] = cargar_o_crear_placeholder(PLAYER_TANK_IMG, GREEN) 
        assets[ENEMY_NORMAL_IMG] = cargar_o_crear_placeholder(ENEMY_NORMAL_IMG, RED) 
        assets[ENEMY_RAPIDO_IMG] = cargar_o_crear_placeholder(ENEMY_RAPIDO_IMG, (255,100,100)) 
        assets[ENEMY_FUERTE_IMG] = cargar_o_crear_placeholder(ENEMY_FUERTE_IMG, (150,0,0)) 
        assets[BULLET_IMG] = cargar_o_crear_placeholder(BULLET_IMG, WHITE, TILE_SIZE // 3, TILE_SIZE // 3) 
        assets[WALL_IMG] = cargar_o_crear_placeholder(WALL_IMG, GREY) 
        assets[TARGET1_IMG] = cargar_o_crear_placeholder(TARGET1_IMG, GOLD) 
        assets[TARGET2_IMG] = cargar_o_crear_placeholder(TARGET2_IMG, (255, 165, 0)) 
        assets[ENEMY_DESTRUCTION_IMAGE_PATH] = cargar_o_crear_placeholder(ENEMY_DESTRUCTION_IMAGE_PATH, RED, TILE_SIZE, TILE_SIZE) 
        return assets

    def _get_imagen_para_objeto(self, tipo_objeto_modelo): 
        if tipo_objeto_modelo == TIPO_JUGADOR: return self.assets[PLAYER_TANK_IMG] 
        if tipo_objeto_modelo == TIPO_ENEMIGO_NORMAL: return self.assets[ENEMY_NORMAL_IMG] 
        if tipo_objeto_modelo == TIPO_ENEMIGO_RAPIDO: return self.assets[ENEMY_RAPIDO_IMG] 
        if tipo_objeto_modelo == TIPO_ENEMIGO_FUERTE: return self.assets[ENEMY_FUERTE_IMG] 
        if tipo_objeto_modelo == TIPO_BALA: return self.assets[BULLET_IMG] 
        if tipo_objeto_modelo == TIPO_MURO: return self.assets[WALL_IMG] 
        if tipo_objeto_modelo == TIPO_OBJETIVO1: return self.assets[TARGET1_IMG] 
        if tipo_objeto_modelo == TIPO_OBJETIVO2: return self.assets[TARGET2_IMG] 
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE)) 
        surf.fill(BLACK) 
        return surf
        
    def actualizar_objetos_visuales(self, estado_del_modelo): 
        ids_modelos_actuales = {obj_info["id"] for obj_info in estado_del_modelo["objetos"]}
        for obj_id_modelo, sprite_visual in list(self.objetos_visuales_map.items()):
            if obj_id_modelo not in ids_modelos_actuales:
                sprite_visual.kill(); del self.objetos_visuales_map[obj_id_modelo]
        for obj_info in estado_del_modelo["objetos"]:
            obj_id_modelo = obj_info["id"]
            if obj_id_modelo not in self.objetos_visuales_map:
                imagen_base = self._get_imagen_para_objeto(obj_info["tipo"]) 
                sprite_visual = ObjetoVisualSprite(imagen_base); self.objetos_visuales_map[obj_id_modelo] = sprite_visual 
                self.sprites_visuales.add(sprite_visual)
            else: sprite_visual = self.objetos_visuales_map[obj_id_modelo]
            sprite_visual.rect.topleft = (obj_info["x_tile"] * TILE_SIZE, obj_info["y_tile"] * TILE_SIZE) 
            if obj_info["direccion"]:
                angulo = 0; dx, dy = obj_info["direccion"]
                if dy == -1: angulo = 90  
                elif dy == 1: angulo = -90 
                elif dx == -1: angulo = 180 
                elif dx == 1: angulo = 0   
                sprite_visual.rotar(angulo) 

    def _actualizar_visibilidad_botones(self, estado_global_juego): 
        es_menu_inicio = (estado_global_juego == MENU_INICIO) 
        mostrando_selector = es_menu_inicio and self.mostrando_selector_nivel_editado

        self.boton_inicio.activo = es_menu_inicio and not mostrando_selector
        self.boton_abrir_editor.activo = es_menu_inicio and not mostrando_selector
        self.boton_cargar_nivel_editado_abrir_selector.activo = es_menu_inicio and not mostrando_selector
        self.boton_salir_juego_principal.activo = es_menu_inicio and not mostrando_selector

        self.boton_jugar_nivel_seleccionado.activo = mostrando_selector
        self.boton_volver_de_seleccion_a_menu.activo = mostrando_selector
        for btn in self.botones_niveles_editados: 
            btn.activo = mostrando_selector

        self.boton_siguiente_nivel.activo = (estado_global_juego == NIVEL_COMPLETADO) 
        self.boton_reintentar.activo = (estado_global_juego == GAME_OVER) 
        self.boton_salir_menu_gameover.activo = (estado_global_juego == GAME_OVER or estado_global_juego == VICTORIA_FINAL) 
        
        es_pausa = (estado_global_juego == PAUSA) 
        self.boton_reanudar_pausa.activo = es_pausa 
        self.boton_reiniciar_pausa.activo = es_pausa 
        self.boton_salir_menu_pausa.activo = es_pausa 

        self.boton_salir_editor_a_menu.activo = (estado_global_juego == EDITOR_NIVELES)

    def _preparar_lista_niveles_para_mostrar(self):
        if not self.editor_manager: 
             self.editor_manager = EditorManager(self.fuente_mensajes, self.fuente_editor_info)

        self.lista_nombres_niveles_editados = self.editor_manager.get_saved_levels()
        self.botones_niveles_editados.clear()
        
        start_x = SCREEN_WIDTH // 2 - 200
        start_y = 120
        button_height = 40
        button_width = 400
        spacing = 10

        for i, nombre_nivel in enumerate(self.lista_nombres_niveles_editados):
            btn = Boton(nombre_nivel, start_x, start_y + i * (button_height + spacing), 
                        button_width, button_height, 
                        color_fondo=(50, 50, 80), color_texto=WHITE, fuente_tam=30)
            self.botones_niveles_editados.append(btn)
        self.scroll_offset_selector = 0 
        self.nivel_editado_seleccionado_nombre = None 


    def _dibujar_hud(self, estado_del_modelo): 
        vidas_texto = self.fuente_hud.render(f"Vidas: {estado_del_modelo.get('vidas_jugador', 0)}", True, WHITE) 
        self.screen.blit(vidas_texto, (10, 10))
        
        # --- MODIFICACIÓN AQUÍ ---
        nivel_actual_info = estado_del_modelo.get('nivel', 0)
        texto_nivel_para_mostrar = "Nivel: "

        if isinstance(nivel_actual_info, str) and EDITOR_NIVELES_PATH in nivel_actual_info: #
            # Es un nivel editado cargado por su ruta completa
            texto_nivel_para_mostrar += "Nivel Libre"
        elif isinstance(nivel_actual_info, int):
            # Es un nivel procedural (número)
            texto_nivel_para_mostrar += str(nivel_actual_info)
        else:
            # Otro caso (podría ser un nombre de archivo sin ruta, aunque el motor ahora usa rutas completas)
            # O si el estado 'nivel' es inesperado, lo convertimos a string.
            nombre_base = str(nivel_actual_info).split(os.sep)[-1]
            if nombre_base.endswith(".txt"):
                 nombre_base = nombre_base[:-4]
            texto_nivel_para_mostrar += nombre_base
        # --- FIN DE MODIFICACIÓN ---

        nivel_texto_renderizado = self.fuente_hud.render(texto_nivel_para_mostrar, True, WHITE) 
        self.screen.blit(nivel_texto_renderizado, (SCREEN_WIDTH - nivel_texto_renderizado.get_width() - 10, 10)) 

    def _dibujar_selector_nivel_editado(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230)) 
        self.screen.blit(overlay, (0,0))

        titulo_surf = self.fuente_mensajes.render("Seleccionar Nivel", True, GOLD)
        titulo_rect = titulo_surf.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(titulo_surf, titulo_rect)

        list_render_y_start = 120
        button_height = 40
        spacing = 10
        
        for i in range(self.scroll_offset_selector, len(self.botones_niveles_editados)):
            idx_visible = i - self.scroll_offset_selector
            if idx_visible >= self.max_niveles_visibles_selector:
                break 

            btn = self.botones_niveles_editados[i]
            btn.rect.y = list_render_y_start + idx_visible * (button_height + spacing)
            
            if btn.texto == self.nivel_editado_seleccionado_nombre:
                # Guardar color original si no se ha hecho o si ha cambiado
                if not hasattr(btn, 'color_fondo_original_guardado') or btn.color_fondo_original_guardado != btn.color_fondo:
                    btn.color_fondo_original_guardado = btn.color_fondo 
                btn.color_fondo = (80, 80, 120) 
            else:
                if hasattr(btn, 'color_fondo_original_guardado'):
                    btn.color_fondo = btn.color_fondo_original_guardado 
                # else: # Asegurar un color por defecto si no hay original (aunque Boton lo tiene)
                #    btn.color_fondo = (50,50,80)


            btn.dibujar(self.screen)
            if btn.texto == self.nivel_editado_seleccionado_nombre and hasattr(btn, 'color_fondo_original_guardado'):
                 btn.color_fondo = btn.color_fondo_original_guardado


        if len(self.botones_niveles_editados) > self.max_niveles_visibles_selector:
            scroll_info_y = list_render_y_start + self.max_niveles_visibles_selector * (button_height + spacing) + 10
            scroll_text = "Usa la rueda del mouse para más niveles"
            if self.scroll_offset_selector > 0:
                scroll_text += " (Arriba)"
            if self.scroll_offset_selector + self.max_niveles_visibles_selector < len(self.botones_niveles_editados):
                 scroll_text += " (Abajo)"
            
            scroll_surf = self.fuente_editor_info.render(scroll_text, True, GREY)
            self.screen.blit(scroll_surf, (SCREEN_WIDTH // 2 - scroll_surf.get_width() // 2, scroll_info_y))


        self.boton_jugar_nivel_seleccionado.dibujar(self.screen)
        self.boton_volver_de_seleccion_a_menu.dibujar(self.screen)


    def dibujar_estado_juego(self, estado_del_modelo, estado_global_juego): 
        self._actualizar_visibilidad_botones(estado_global_juego) 
        pygame.display.set_caption(f"Tank Attack MVC - {estado_global_juego.replace('_',' ').title()}")


        self.screen.fill(BLACK) 
        if estado_global_juego == JUGANDO or estado_global_juego == PAUSA: 
            for x in range(0, SCREEN_WIDTH, TILE_SIZE): pygame.draw.line(self.screen, GREY, (x, 0), (x, SCREEN_HEIGHT)) 
            for y in range(0, SCREEN_HEIGHT, TILE_SIZE): pygame.draw.line(self.screen, GREY, (0, y), (SCREEN_WIDTH, y)) 
            if estado_del_modelo: 
                self.actualizar_objetos_visuales(estado_del_modelo)
            self.sprites_visuales.draw(self.screen) 
            if estado_del_modelo: self._dibujar_hud(estado_del_modelo) 
            if estado_del_modelo and "enemigos_destruyendose" in estado_del_modelo: 
                img_explosion = self.assets.get(ENEMY_DESTRUCTION_IMAGE_PATH) 
                if img_explosion:
                    for destruccion_info in estado_del_modelo["enemigos_destruyendose"]: 
                        x_pos = destruccion_info["x_tile"] * TILE_SIZE; y_pos = destruccion_info["y_tile"] * TILE_SIZE 
                        self.screen.blit(img_explosion, (x_pos, y_pos))

        if estado_global_juego == PAUSA: 
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); self.screen.blit(overlay, (0,0)) 
            titulo_pausa = self.fuente_mensajes.render("Pausa", True, WHITE); rect_titulo = titulo_pausa.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4)); self.screen.blit(titulo_pausa, rect_titulo) 
            self.boton_reanudar_pausa.dibujar(self.screen); self.boton_reiniciar_pausa.dibujar(self.screen); self.boton_salir_menu_pausa.dibujar(self.screen) 
        elif estado_global_juego == MENU_INICIO: 
            if self.mostrando_selector_nivel_editado:
                self._dibujar_selector_nivel_editado()
            else:
                self.boton_inicio.dibujar(self.screen) 
                self.boton_abrir_editor.dibujar(self.screen)
                self.boton_cargar_nivel_editado_abrir_selector.dibujar(self.screen)
                self.boton_salir_juego_principal.dibujar(self.screen) 
                titulo = self.fuente_mensajes.render("Tank Attack!", True, GREEN); rect_titulo = titulo.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4 - 20)); self.screen.blit(titulo, rect_titulo) 
        elif estado_global_juego == NIVEL_COMPLETADO: 
            texto_msg = self.fuente_mensajes.render("Nivel Completado!", True, GREEN); self.boton_siguiente_nivel.dibujar(self.screen); rect_msg = texto_msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)); self.screen.blit(texto_msg, rect_msg) 
        elif estado_global_juego == GAME_OVER: 
            texto_msg = self.fuente_mensajes.render("GAME OVER", True, RED); self.boton_reintentar.dibujar(self.screen); self.boton_salir_menu_gameover.dibujar(self.screen); rect_msg = texto_msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)); self.screen.blit(texto_msg, rect_msg) 
        elif estado_global_juego == VICTORIA_FINAL: 
            texto_msg = self.fuente_mensajes.render("¡VICTORIA!", True, GOLD); self.boton_salir_menu_gameover.update_texto("Volver al Menú"); self.boton_salir_menu_gameover.dibujar(self.screen); rect_msg = texto_msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)); self.screen.blit(texto_msg, rect_msg) 
        
        elif estado_global_juego == EDITOR_NIVELES:
            if not self.editor_manager: 
                self.editor_manager = EditorManager(self.fuente_mensajes, self.fuente_editor_info)
                default_path = os.path.join(EDITOR_NIVELES_PATH, DEFAULT_EDITOR_FILENAME + "_autosave.txt")
                if not os.path.exists(default_path):
                    default_path = os.path.join(EDITOR_NIVELES_PATH, DEFAULT_EDITOR_FILENAME + ".txt")
                self.editor_manager.load_map_from_file(default_path)
            self.editor_manager.draw(self.screen)
            self.boton_salir_editor_a_menu.dibujar(self.screen) 

        pygame.display.flip() 

    def manejar_eventos_ui(self, evento, estado_actual_juego): 
        if estado_actual_juego == MENU_INICIO: 
            if self.mostrando_selector_nivel_editado:
                if self.boton_jugar_nivel_seleccionado.manejar_evento(evento):
                    if self.nivel_editado_seleccionado_nombre:
                        self.mostrando_selector_nivel_editado = False 
                        return ("jugar_nivel_especifico", self.nivel_editado_seleccionado_nombre)
                elif self.boton_volver_de_seleccion_a_menu.manejar_evento(evento):
                    self.mostrando_selector_nivel_editado = False
                    self.nivel_editado_seleccionado_nombre = None 
                    return "refrescar_menu" 
                
                for btn_nivel in self.botones_niveles_editados:
                    visible_start_y = 120 
                    visible_end_y = visible_start_y + self.max_niveles_visibles_selector * (40 + 10)
                    if visible_start_y <= btn_nivel.rect.y < visible_end_y:
                        if btn_nivel.manejar_evento(evento):
                            self.nivel_editado_seleccionado_nombre = btn_nivel.texto
                            return "seleccion_nivel_cambiada" 
                
                if evento.type == pygame.MOUSEWHEEL:
                    if evento.y > 0: 
                        self.scroll_offset_selector = max(0, self.scroll_offset_selector - 1)
                    elif evento.y < 0: 
                        max_scroll = len(self.botones_niveles_editados) - self.max_niveles_visibles_selector
                        self.scroll_offset_selector = min(max_scroll, self.scroll_offset_selector + 1)
                    if self.scroll_offset_selector < 0 : self.scroll_offset_selector = 0 
                    return "scroll_selector"


            else: 
                if self.boton_inicio.manejar_evento(evento): return "iniciar_juego_procedural" 
                if self.boton_abrir_editor.manejar_evento(evento): return "abrir_editor"
                if self.boton_cargar_nivel_editado_abrir_selector.manejar_evento(evento): 
                    self.mostrando_selector_nivel_editado = True
                    self._preparar_lista_niveles_para_mostrar() 
                    return "abrir_selector_nivel" 
                if self.boton_salir_juego_principal.manejar_evento(evento): return "salir_juego" 
        elif estado_actual_juego == NIVEL_COMPLETADO: 
            if self.boton_siguiente_nivel.manejar_evento(evento): return "siguiente_nivel" 
        elif estado_actual_juego == GAME_OVER: 
            if self.boton_reintentar.manejar_evento(evento): return "reintentar_nivel" 
            if self.boton_salir_menu_gameover.manejar_evento(evento): return "ir_a_menu" 
        elif estado_actual_juego == VICTORIA_FINAL: 
            if self.boton_salir_menu_gameover.manejar_evento(evento): return "ir_a_menu" 
        elif estado_actual_juego == PAUSA: 
            if self.boton_reanudar_pausa.manejar_evento(evento): return "reanudar_juego" 
            if self.boton_reiniciar_pausa.manejar_evento(evento): return "reintentar_nivel_pausa" 
            if self.boton_salir_menu_pausa.manejar_evento(evento): return "ir_a_menu_pausa" 
        
        elif estado_actual_juego == EDITOR_NIVELES:
            if self.editor_manager: 
                resultado_editor = self.editor_manager.handle_event(evento)
                if resultado_editor == "operacion_archivo_terminada": 
                    pass 
            if self.boton_salir_editor_a_menu.manejar_evento(evento):
                if self.editor_manager:
                    autosave_path = os.path.join(EDITOR_NIVELES_PATH, DEFAULT_EDITOR_FILENAME + "_autosave.txt")
                    if self.editor_manager.save_map_to_file(autosave_path):
                        self.editor_manager.feedback_message = f"Autoguardado en {DEFAULT_EDITOR_FILENAME}_autosave.txt"
                        print(f"Editor: Autoguardado en {autosave_path}")
                    else:
                        print(f"Editor: Falló el autoguardado en {autosave_path}")
                return "ir_a_menu_desde_editor"
        return None

class ObjetoVisualSprite(pygame.sprite.Sprite): 
    def __init__(self, imagen_base):
        super().__init__(); self.imagen_original = imagen_base; self.image = self.imagen_original.copy()
        self.rect = self.image.get_rect(); self.angulo_actual = 0
    def rotar(self, nuevo_angulo): 
        if self.angulo_actual != nuevo_angulo:
            self.image = pygame.transform.rotate(self.imagen_original, nuevo_angulo)
            centro_anterior = self.rect.center; self.rect = self.image.get_rect(center=centro_anterior); self.angulo_actual = nuevo_angulo
    def update(self): pass