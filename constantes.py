# constantes.py

# Dimensiones de la pantalla y cuadrícula
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 40
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE

# Colores (pueden ser útiles para debug o elementos simples)
BLACK = (133, 162, 180)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)
GREY = (133, 162, 180)

# Direcciones (vectores para movimiento en la cuadrícula)
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = [UP, DOWN, LEFT, RIGHT]
STAY = (0,0) # Para cuando un tanque no se mueve

# Estados del Juego
MENU_INICIO = "menu_inicio"
CARGANDO_NIVEL = "cargando_nivel"
JUGANDO = "jugando"
NIVEL_COMPLETADO = "nivel_completado"
GAME_OVER = "game_over"
VICTORIA_FINAL = "victoria_final" # <--- AÑADE ESTA LÍNEA
PAUSA = "pausa" # <--- NUEVO ESTADO
EDITOR_NIVELES = "editor_niveles" # Para el futuro [32]

# Identificadores de tipo de objeto (para el modelo)
TIPO_JUGADOR = "jugador"
TIPO_ENEMIGO_NORMAL = "enemigo_normal"
TIPO_ENEMIGO_RAPIDO = "enemigo_rapido"
TIPO_ENEMIGO_FUERTE = "enemigo_fuerte"
TIPO_BALA = "bala"
TIPO_MURO = "muro"
TIPO_OBJETIVO1 = "objetivo1"
TIPO_OBJETIVO2 = "objetivo2"

# Rutas a assets (ajusta según tus nombres de archivo)
ASSETS_PATH = "frontend/assets/" # Asegúrate que esta ruta sea correcta desde donde ejecutas main.py
PLAYER_TANK_IMG = ASSETS_PATH + "player_tank.png"
ENEMY_NORMAL_IMG = ASSETS_PATH + "enemy_tank_normal.png"
ENEMY_RAPIDO_IMG = ASSETS_PATH + "enemy_tank_rapido.png" # Crea esta imagen
ENEMY_FUERTE_IMG = ASSETS_PATH + "enemy_tank_fuerte.png" # Crea esta imagen
BULLET_IMG = ASSETS_PATH + "bullet.png"
WALL_IMG = ASSETS_PATH + "wall.png"
TARGET1_IMG = ASSETS_PATH + "target_tipo1.png"
TARGET2_IMG = ASSETS_PATH + "target_tipo2.png" # Crea esta imagen

# CONSTANTE PARA LA MÚSICA DEL MENÚ
# Si menu_music.mp3 está directamente en frontend/assets/
MENU_MUSIC_PATH = ASSETS_PATH + "menu_music.mp3" # Ajustado para estar al mismo nivel que las imágenes
# Música ambiental durante el juego
AMBIENT_LEVEL_MUSIC_PATH = ASSETS_PATH + "ambient_level_music.mp3" # Si está en frontend/assets/
# Sonido genérico de tanques en movimiento
GENERAL_TANK_MOVING_SOUND_PATH = ASSETS_PATH + "tanks_moving_loop.mp3" # Si está en frontend/assets/
# NUEVA CONSTANTE PARA SONIDO DE DISPARO DEL JUGADOR
PLAYER_SHOOT_SOUND_PATH = ASSETS_PATH + "player_shoot.mp3" # Ajusta el nombre/extensión si es necesario
# NUEVAS CONSTANTES PARA SONIDOS DE GAME OVER
PLAYER_FINAL_DESTRUCTION_SOUND_PATH = ASSETS_PATH + "player_explosion_final.mp3"
GAME_OVER_SCREEN_MUSIC_PATH = ASSETS_PATH + "game_over_screen_music.mp3"
# NUEVAS CONSTANTES PARA MÚSICA DE VICTORIA DE NIVEL Y FINAL
LEVEL_COMPLETE_MUSIC_PATH = ASSETS_PATH + "level_complete_jingle.mp3" # Para niveles 1 y 2
FINAL_VICTORY_MUSIC_PATH = ASSETS_PATH + "final_victory_music.mp3"    # Para el último nivel
# NUEVA CONSTANTE PARA LA IMAGEN DE DESTRUCCIÓN ENEMIGA
ENEMY_DESTRUCTION_IMAGE_PATH = ASSETS_PATH + "explosion_enemigo.png"

# Parámetros de juego
VIDAS_INICIALES_JUGADOR = 3
CADENCIA_DISPARO_JUGADOR = 200 #ms
VELOCIDAD_BALA = 0.3 # Tiles por tick de lógica (no píxeles por frame)
MAX_NIVELES = 3

# Nombres de eventos personalizados (si los usas con Pygame)
EVENTO_SIGUIENTE_NIVEL = None # Se definirá en main.py

# Constantes para el Editor de Niveles
EDITOR_NIVELES_PATH = "niveles_editados/" # Carpeta para guardar/cargar niveles
DEFAULT_EDITOR_FILENAME = "nivel_editado"
EDITOR_CHAR_VACIO = ' '
EDITOR_CHAR_MURO = 'W'
EDITOR_CHAR_JUGADOR = 'P'
EDITOR_CHAR_ENEMIGO_NORMAL = '1'
EDITOR_CHAR_ENEMIGO_RAPIDO = '2'
EDITOR_CHAR_ENEMIGO_FUERTE = '3'
EDITOR_CHAR_OBJETIVO1 = 'A'  # Por Alpha
EDITOR_CHAR_OBJETIVO2 = 'B'  # Por Bravo

# Para la visualización en el editor (puede ser diferente a TILE_SIZE si se desea)
EDITOR_DISPLAY_TILE_SIZE = 20 
EDITOR_GRID_WIDTH = SCREEN_WIDTH // EDITOR_DISPLAY_TILE_SIZE
EDITOR_GRID_HEIGHT = SCREEN_HEIGHT // EDITOR_DISPLAY_TILE_SIZE # Esto puede ser mucho si la pantalla es grande

# Ajustamos para que la cuadrícula del editor coincida con la del juego
# Si EDITOR_DISPLAY_TILE_SIZE es más pequeño, se mostrará una porción más grande del mapa
# o el mapa completo si GRID_WIDTH * EDITOR_DISPLAY_TILE_SIZE <= SCREEN_WIDTH
# Por simplicidad, mantendremos la misma cantidad de tiles que el juego.
# El editor mostrará la misma cantidad de celdas que el juego.
EDITOR_TILES_PER_SCREEN_WIDTH = GRID_WIDTH 
EDITOR_TILES_PER_SCREEN_HEIGHT = GRID_HEIGHT

# Mapeo de caracteres a tipos de objeto y viceversa (útil para el editor y carga)
EDITOR_CHAR_TO_TYPE = {
    EDITOR_CHAR_MURO: TIPO_MURO,
    EDITOR_CHAR_JUGADOR: TIPO_JUGADOR,
    EDITOR_CHAR_ENEMIGO_NORMAL: TIPO_ENEMIGO_NORMAL,
    EDITOR_CHAR_ENEMIGO_RAPIDO: TIPO_ENEMIGO_RAPIDO,
    EDITOR_CHAR_ENEMIGO_FUERTE: TIPO_ENEMIGO_FUERTE,
    EDITOR_CHAR_OBJETIVO1: TIPO_OBJETIVO1,
    EDITOR_CHAR_OBJETIVO2: TIPO_OBJETIVO2,
    EDITOR_CHAR_VACIO: None # Representa un espacio vacío
}

EDITOR_TYPE_TO_CHAR = {v: k for k, v in EDITOR_CHAR_TO_TYPE.items() if v is not None}
EDITOR_TYPE_TO_CHAR[None] = EDITOR_CHAR_VACIO # Asegurar que el vacío también tenga un char

# Lista de elementos que se pueden colocar con el editor
EDITOR_PLACABLE_CHARS = [
    EDITOR_CHAR_MURO, EDITOR_CHAR_JUGADOR, 
    EDITOR_CHAR_ENEMIGO_NORMAL, EDITOR_CHAR_ENEMIGO_RAPIDO, EDITOR_CHAR_ENEMIGO_FUERTE,
    EDITOR_CHAR_OBJETIVO1, EDITOR_CHAR_OBJETIVO2, EDITOR_CHAR_VACIO
]

# Colores para el editor
EDITOR_COLOR_CURSOR = (255, 255, 0) # Amarillo
EDITOR_COLOR_TEXTO_INFO = WHITE
EDITOR_COLOR_FONDO_INPUT = (50, 50, 50)
EDITOR_COLOR_TEXTO_INPUT = WHITE


# Constantes para la IA de enemigos y pathfinding
DFS_ACTIVATION_RANGE = 10  # Rango en tiles para que el enemigo intente usar DFS hacia el jugador
OBJECTIVE_PATROL_RADIUS = 5 # Radio de patrulla alrededor del objetivo primario
# Distancias al cuadrado para eficiencia
DFS_ACTIVATION_RANGE_SQ = DFS_ACTIVATION_RANGE * DFS_ACTIVATION_RANGE
OBJECTIVE_PATROL_MAX_DISTANCE_SQ = (OBJECTIVE_PATROL_RADIUS + 1) * (OBJECTIVE_PATROL_RADIUS + 1) # Un poco más para que intente entrar
OBJECTIVE_PATROL_MIN_DISTANCE_SQ = (OBJECTIVE_PATROL_RADIUS - 1) * (OBJECTIVE_PATROL_RADIUS - 1) # Un poco menos para que intente salir si está muy cerca
# constantes.py

# ... (todas tus constantes existentes) ...

# Constantes para el modo Online
WEBSOCKET_URL = "wss://battlecity-relay-544519459817.us-central1.run.app"

# constantes.py

# ... (todas tus constantes existentes) ...

# --- AÑADE ESTAS LÍNEAS AL FINAL ---

# Constantes de Movimiento Fluido (píxeles por segundo)
VELOCIDAD_JUGADOR_PX_S = 120  # Aprox. 3 casillas por segundo
VELOCIDAD_ENEMIGO_NORMAL_PX_S = 60
VELOCIDAD_ENEMIGO_RAPIDO_PX_S = 100
VELOCIDAD_ENEMIGO_FUERTE_PX_S = 50