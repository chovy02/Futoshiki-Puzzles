"""Reusable UI widgets with smooth hover and press animations."""
import pygame
from . import theme as th


class Button:
    def __init__(self, rect, text, callback=None, *, primary=False,
                 font_size=16, danger=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.primary = primary
        self.danger = danger
        self.font_size = font_size
        self.hover_t = 0.0
        self.press_t = 0.0
        self._was_pressed = False
        self.disabled = False
        self.visible = True

    def handle_event(self, event):
        if not self.visible or self.disabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._was_pressed = True
                self.press_t = 1.0
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self._was_pressed
            self._was_pressed = False
            if was and self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def update(self, dt, mouse_pos):
        if not self.visible:
            self.hover_t = max(0.0, self.hover_t - dt * 8)
            return
        if self.disabled:
            self.hover_t = max(0.0, self.hover_t - dt * 8)
            return
        target = 1.0 if self.rect.collidepoint(mouse_pos) else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 14)
        self.press_t += (0.0 - self.press_t) * min(1.0, dt * 18)

    def draw(self, surface):
        if not self.visible:
            return

        if self.disabled:
            bg = th.BG_SECONDARY
            border = th.BORDER
            text_color = th.TEXT_DISABLED
        elif self.primary:
            bg = th.lerp_color(th.ACCENT_DARK, th.ACCENT_DIM, self.hover_t)
            border = th.lerp_color(th.ACCENT_DIM, th.ACCENT, self.hover_t)
            text_color = th.lerp_color(th.ACCENT, th.ACCENT_HOVER, self.hover_t)
        elif self.danger:
            bg = th.lerp_color(th.BG_SECONDARY, (60, 30, 35), self.hover_t)
            border = th.lerp_color(th.BORDER, th.ERROR, self.hover_t)
            text_color = th.lerp_color(th.TEXT_SECONDARY, th.ERROR, self.hover_t)
        else:
            bg = th.lerp_color(th.BG_SECONDARY, th.BG_ELEVATED, self.hover_t)
            border = th.lerp_color(th.BORDER, th.BORDER_HOVER, self.hover_t)
            text_color = th.lerp_color(th.TEXT_SECONDARY, th.TEXT_PRIMARY, self.hover_t)

        scale = 1.0 - self.press_t * 0.04
        rect = self.rect.copy()
        if scale < 1.0:
            new_w = int(rect.w * scale)
            new_h = int(rect.h * scale)
            rect = pygame.Rect(0, 0, new_w, new_h)
            rect.center = self.rect.center

        pygame.draw.rect(surface, bg, rect, border_radius=10)
        pygame.draw.rect(surface, border, rect, width=1, border_radius=10)

        font = th.get_font(self.font_size, bold=self.primary)
        text_surf = font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)


def draw_dotted_bg(surface, color=(255, 255, 255), spacing=32, radius=1, alpha=10):
    """Draw a faint dot pattern over the entire surface."""
    w, h = surface.get_size()
    dot_layer = pygame.Surface((w, h), pygame.SRCALPHA)
    c = (*color, alpha)
    for y in range(0, h, spacing):
        for x in range(0, w, spacing):
            pygame.draw.circle(dot_layer, c, (x, y), radius)
    surface.blit(dot_layer, (0, 0))