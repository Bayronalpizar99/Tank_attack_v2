# frontend/ui_elementos.py
import pygame
from constantes import WHITE, BLACK, GREEN, GREY

class Boton(pygame.sprite.Sprite):
    def __init__(self, texto, x, y, ancho, alto, color_fondo=GREEN, color_texto=BLACK, color_borde=WHITE, fuente_tam=30):
        super().__init__()
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color_fondo = color_fondo
        self.color_texto = color_texto
        self.color_borde = color_borde
        self.fuente_tam = fuente_tam
        self.fuente = pygame.font.Font(None, self.fuente_tam) # Fuente por defecto
        self.activo = True # Si el botón es visible y clickeable
        self.presionado = False

        self._render_text()

    def _render_text(self):
        self.imagen_texto = self.fuente.render(self.texto, True, self.color_texto)
        self.rect_texto = self.imagen_texto.get_rect(center=self.rect.center)

    def dibujar(self, screen):
        if not self.activo:
            return

        color_actual_fondo = GREY if self.presionado else self.color_fondo
        pygame.draw.rect(screen, color_actual_fondo, self.rect)
        if self.color_borde:
            pygame.draw.rect(screen, self.color_borde, self.rect, 2) # Borde de 2px
        screen.blit(self.imagen_texto, self.rect_texto)

    def manejar_evento(self, evento):
        if not self.activo:
            return False

        if evento.type == pygame.MOUSEBUTTONDOWN:
            if evento.button == 1 and self.rect.collidepoint(evento.pos):
                self.presionado = True
                return False # No es una acción final aún, solo visual
        elif evento.type == pygame.MOUSEBUTTONUP:
            if evento.button == 1 and self.presionado and self.rect.collidepoint(evento.pos):
                self.presionado = False
                return True # ¡Acción!
            self.presionado = False
        return False

    def update_texto(self, nuevo_texto):
        self.texto = nuevo_texto
        self._render_text()