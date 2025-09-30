# Proyecto2_Lenguajes/editor_manager.py
import pygame
import os
from constantes import (
    EDITOR_CHAR_VACIO, EDITOR_CHAR_MURO, EDITOR_CHAR_JUGADOR,
    EDITOR_CHAR_ENEMIGO_NORMAL, EDITOR_CHAR_ENEMIGO_RAPIDO, EDITOR_CHAR_ENEMIGO_FUERTE,
    EDITOR_CHAR_OBJETIVO1, EDITOR_CHAR_OBJETIVO2,
    EDITOR_DISPLAY_TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, # Usamos las dimensiones de la cuadrícula del juego
    EDITOR_COLOR_CURSOR, EDITOR_COLOR_TEXTO_INFO, EDITOR_COLOR_FONDO_INPUT, EDITOR_COLOR_TEXTO_INPUT,
    EDITOR_PLACABLE_CHARS, EDITOR_NIVELES_PATH, DEFAULT_EDITOR_FILENAME, SCREEN_HEIGHT, SCREEN_WIDTH
)

class EditorManager:
    def __init__(self, fuente_grande, fuente_pequena):
        self.fuente_grande = fuente_grande
        self.fuente_pequena = fuente_pequena
        
        self.grid_map_chars = [[EDITOR_CHAR_VACIO for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.cursor_pos = [0, 0]  # Fila, Columna
        
        self.placable_items = EDITOR_PLACABLE_CHARS
        self.current_item_idx = 0
        self.selected_char_to_place = self.placable_items[self.current_item_idx]
        
        self.feedback_message = "Editor de Niveles. Flechas: Mover. Espacio: Colocar. Tab: Cambiar Tile. S: Guardar. L: Cargar."
        self.is_typing_filename = False
        self.input_text = DEFAULT_EDITOR_FILENAME
        self.current_operation = None # "guardar" o "cargar"

        # Asegurarse de que el directorio de niveles exista
        if not os.path.exists(EDITOR_NIVELES_PATH):
            os.makedirs(EDITOR_NIVELES_PATH)

    def handle_input_filename(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_RETURN:
                filename = self.input_text.strip()
                if not filename:
                    self.feedback_message = "Nombre de archivo no puede estar vacío."
                    return None
                
                full_path = os.path.join(EDITOR_NIVELES_PATH, filename + ".txt")
                
                if self.current_operation == "guardar":
                    self.save_map_to_file(full_path)
                    self.feedback_message = f"Nivel guardado como {filename}.txt"
                elif self.current_operation == "cargar":
                    if self.load_map_from_file(full_path):
                        self.feedback_message = f"Nivel cargado desde {filename}.txt"
                    else:
                        self.feedback_message = f"Error al cargar {filename}.txt. ¿Existe?"
                
                self.is_typing_filename = False
                self.current_operation = None
                return "operacion_archivo_terminada"

            elif evento.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif evento.key == pygame.K_ESCAPE: # Cancelar input
                self.is_typing_filename = False
                self.current_operation = None
                self.feedback_message = "Operación cancelada."
            else:
                # Permitir solo caracteres alfanuméricos y guiones bajos/medios para nombres de archivo
                if evento.unicode.isalnum() or evento.unicode in ['_', '-']:
                    self.input_text += evento.unicode
        return None

    def handle_event(self, evento):
        if self.is_typing_filename:
            return self.handle_input_filename(evento)

        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_UP:
                self.cursor_pos[0] = max(0, self.cursor_pos[0] - 1)
            elif evento.key == pygame.K_DOWN:
                self.cursor_pos[0] = min(GRID_HEIGHT - 1, self.cursor_pos[0] + 1)
            elif evento.key == pygame.K_LEFT:
                self.cursor_pos[1] = max(0, self.cursor_pos[1] - 1)
            elif evento.key == pygame.K_RIGHT:
                self.cursor_pos[1] = min(GRID_WIDTH - 1, self.cursor_pos[1] + 1)
            
            elif evento.key == pygame.K_SPACE: # Colocar tile
                self.place_selected_char()
                self.feedback_message = f"Colocado '{self.selected_char_to_place}' en ({self.cursor_pos[0]}, {self.cursor_pos[1]})"

            elif evento.key == pygame.K_TAB: # Cambiar tile a colocar
                self.current_item_idx = (self.current_item_idx + 1) % len(self.placable_items)
                self.selected_char_to_place = self.placable_items[self.current_item_idx]
                self.feedback_message = f"Tile seleccionado: '{self.selected_char_to_place}'"
            
            elif evento.key == pygame.K_s: # Guardar
                self.is_typing_filename = True
                self.current_operation = "guardar"
                self.input_text = DEFAULT_EDITOR_FILENAME # Resetear a default o último usado
                self.feedback_message = "GUARDAR: Ingrese nombre de archivo y presione Enter (sin .txt)."
                return "iniciar_input_nombre_archivo"

            elif evento.key == pygame.K_l: # Cargar
                self.is_typing_filename = True
                self.current_operation = "cargar"
                self.input_text = DEFAULT_EDITOR_FILENAME
                self.feedback_message = "CARGAR: Ingrese nombre de archivo y presione Enter (sin .txt)."
                return "iniciar_input_nombre_archivo"
        return None

    def place_selected_char(self):
        row, col = self.cursor_pos
        # Si se coloca un jugador, asegurarse de que solo haya uno
        if self.selected_char_to_place == EDITOR_CHAR_JUGADOR:
            for r in range(GRID_HEIGHT):
                for c in range(GRID_WIDTH):
                    if self.grid_map_chars[r][c] == EDITOR_CHAR_JUGADOR:
                        self.grid_map_chars[r][c] = EDITOR_CHAR_VACIO # Borrar jugador anterior
        self.grid_map_chars[row][col] = self.selected_char_to_place

    def load_map_from_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                new_grid = [[EDITOR_CHAR_VACIO for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
                for r, line in enumerate(lines):
                    if r < GRID_HEIGHT:
                        for c, char_tile in enumerate(line.strip()):
                            if c < GRID_WIDTH:
                                if char_tile in EDITOR_PLACABLE_CHARS:
                                    new_grid[r][c] = char_tile
                                else: # Caracter desconocido, tratar como vacío
                                    new_grid[r][c] = EDITOR_CHAR_VACIO
                self.grid_map_chars = new_grid
                # Validar si hay un jugador, si no, colocar uno por defecto
                if not any(EDITOR_CHAR_JUGADOR in row for row in self.grid_map_chars):
                    self.grid_map_chars[GRID_HEIGHT // 2][GRID_WIDTH // 2] = EDITOR_CHAR_JUGADOR
                return True
        except FileNotFoundError:
            print(f"Editor: Archivo no encontrado {filepath}")
            # Se podría inicializar un mapa vacío si no se encuentra
            self.grid_map_chars = [[EDITOR_CHAR_VACIO for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
            # Colocar jugador por defecto si se crea un nivel vacío al no encontrar el archivo
            self.grid_map_chars[GRID_HEIGHT // 2][GRID_WIDTH // 2] = EDITOR_CHAR_JUGADOR

            return False
        except Exception as e:
            print(f"Editor: Error al cargar el mapa: {e}")
            return False

    def save_map_to_file(self, filepath):
        try:
            # Asegurar que haya al menos un jugador antes de guardar
            if not any(EDITOR_CHAR_JUGADOR in row for row in self.grid_map_chars):
                # Intentar colocar un jugador en el centro si no hay ninguno
                # Podrías hacer esto más inteligente, buscando un espacio vacío
                self.grid_map_chars[GRID_HEIGHT // 2][GRID_WIDTH // 2] = EDITOR_CHAR_JUGADOR
                print("Advertencia: No se encontró jugador en el mapa al guardar. Se añadió uno por defecto.")

            with open(filepath, 'w') as f:
                for r in range(GRID_HEIGHT):
                    f.write("".join(self.grid_map_chars[r]) + "\n")
            return True
        except Exception as e:
            print(f"Editor: Error al guardar el mapa: {e}")
            self.feedback_message = f"Error al guardar: {e}"
            return False
    def get_saved_levels(self):
        """
        Obtiene una lista de nombres de niveles guardados (sin extensión .txt)
        desde la carpeta EDITOR_NIVELES_PATH.
        """
        if not os.path.exists(EDITOR_NIVELES_PATH):
            return []
        
        niveles = []
        for filename in os.listdir(EDITOR_NIVELES_PATH):
            if filename.endswith(".txt"):
                niveles.append(filename[:-4]) # Quitar la extensión .txt
        niveles.sort() # Ordenar alfabéticamente
        return niveles
    def draw(self, screen):
        screen.fill((30, 30, 30)) # Fondo oscuro para el editor

        # Dibujar la cuadrícula del editor
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                char_tile = self.grid_map_chars[r][c]
                tile_rect = pygame.Rect(c * EDITOR_DISPLAY_TILE_SIZE, 
                                        r * EDITOR_DISPLAY_TILE_SIZE,
                                        EDITOR_DISPLAY_TILE_SIZE, EDITOR_DISPLAY_TILE_SIZE)
                
                # Color de fondo simple basado en el carácter (opcional)
                tile_color = (50,50,50) # Gris oscuro por defecto
                if char_tile == EDITOR_CHAR_MURO: tile_color = (100,100,100)
                elif char_tile == EDITOR_CHAR_JUGADOR: tile_color = (0,150,0)
                elif char_tile.isdigit(): tile_color = (150,0,0) # Enemigos
                elif char_tile in [EDITOR_CHAR_OBJETIVO1, EDITOR_CHAR_OBJETIVO2]: tile_color = (150,150,0) # Objetivos

                pygame.draw.rect(screen, tile_color, tile_rect)
                pygame.draw.rect(screen, (80,80,80), tile_rect, 1) # Borde de la celda

                if char_tile != EDITOR_CHAR_VACIO:
                    text_surf = self.fuente_pequena.render(char_tile, True, EDITOR_COLOR_TEXTO_INFO)
                    text_rect = text_surf.get_rect(center=tile_rect.center)
                    screen.blit(text_surf, text_rect)

        # Dibujar cursor
        cursor_screen_x = self.cursor_pos[1] * EDITOR_DISPLAY_TILE_SIZE
        cursor_screen_y = self.cursor_pos[0] * EDITOR_DISPLAY_TILE_SIZE
        pygame.draw.rect(screen, EDITOR_COLOR_CURSOR, 
                         (cursor_screen_x, cursor_screen_y, EDITOR_DISPLAY_TILE_SIZE, EDITOR_DISPLAY_TILE_SIZE), 2)

        # Información y Feedback
        # Posición para el feedback (abajo)
        feedback_y_pos = SCREEN_HEIGHT - 30
        input_prompt_y_pos = feedback_y_pos - 60 # Un poco más arriba para el prompt de input
        
        # Tile seleccionado
        selected_tile_text = f"Tile actual: [{self.selected_char_to_place}] (Tab para cambiar)"
        selected_surf = self.fuente_pequena.render(selected_tile_text, True, EDITOR_COLOR_TEXTO_INFO)
        screen.blit(selected_surf, (10, feedback_y_pos - 30))
        
        # Mensaje de feedback
        feedback_surf = self.fuente_pequena.render(self.feedback_message, True, EDITOR_COLOR_TEXTO_INFO)
        screen.blit(feedback_surf, (10, feedback_y_pos))

        if self.is_typing_filename:
            # Fondo para el campo de texto
            input_field_rect = pygame.Rect(10, input_prompt_y_pos, SCREEN_WIDTH - 20, 50)
            pygame.draw.rect(screen, EDITOR_COLOR_FONDO_INPUT, input_field_rect)
            pygame.draw.rect(screen, EDITOR_COLOR_TEXTO_INFO, input_field_rect, 1) # Borde

            # Texto de prompt + input
            prompt_text = f"{self.current_operation.upper()} como: {self.input_text}"
            if pygame.time.get_ticks() % 1000 < 500: # Cursor parpadeante simple
                prompt_text += "|"
            
            input_surf = self.fuente_pequena.render(prompt_text, True, EDITOR_COLOR_TEXTO_INPUT)
            input_rect = input_surf.get_rect(centery=input_field_rect.centery, left=input_field_rect.left + 10)
            screen.blit(input_surf, input_rect)