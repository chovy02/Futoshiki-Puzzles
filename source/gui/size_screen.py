"""Size selection screen - 5 cards (4x4, 5x5, 6x6, 7x7, 9x9)."""
import pygame
from . import theme as th
from .widgets import draw_dotted_bg
from .difficulty_screen import DifficultyCard

class SizeScreen:
    def __init__(self, app):
        self.app = app
        self.title_t = 0.0

        card_w = 180
        card_h = 260
        gap = 20
        total_w = card_w * 5 + gap * 4
        start_x = (th.WINDOW_WIDTH - total_w) // 2
        center_y = th.WINDOW_HEIGHT // 2 + 30
        y = center_y - card_h // 2

        sizes = [
            ("4x4", th.ACCENT, "9 Levels"),
            ("5x5", th.SUCCESS, "9 Levels"),
            ("6x6", th.MEDIUM, "9 Levels"),
            ("7x7", th.HARD, "9 Levels"),
            ("9x9", th.EXTREME, "9 Levels")
        ]

        self.cards = []
        for i, (name, color, desc) in enumerate(sizes):
            rect = (start_x + i * (card_w + gap), y, card_w, card_h)
            card = DifficultyCard(rect, name, desc, color, 
                                  lambda n=name: self._open(n), enabled=True)
            card.appear_delay = 0.1 + i * 0.08
            self.cards.append(card)

    def _open(self, size_name):
        from .difficulty_screen import DifficultyScreen
        self.app.transition_to(DifficultyScreen(self.app, size_name))

    def handle_event(self, event):
        for card in self.cards:
            card.handle_event(event)

    def update(self, dt, mouse_pos):
        self.title_t = min(1.0, self.title_t + dt * 2)
        for card in self.cards:
            card.update(dt, mouse_pos)

    def draw(self, surface):
        surface.fill(th.BG_PRIMARY)
        draw_dotted_bg(surface, alpha=8)

        title_appear = th.ease_out_cubic(self.title_t)
        title_alpha = int(255 * title_appear)
        title_offset = int((1 - title_appear) * 18)

        label_font = th.get_font(13, bold=True)
        label_surf = label_font.render("FUTOSHIKI SOLVER", True, th.ACCENT)
        label_surf.set_alpha(title_alpha)
        label_rect = label_surf.get_rect(center=(th.WINDOW_WIDTH // 2, 130 - title_offset))
        surface.blit(label_surf, label_rect)

        title_font = th.get_font(56, bold=True)
        title_surf = title_font.render("Select Board Size", True, th.TEXT_PRIMARY)
        title_surf.set_alpha(title_alpha)
        title_rect = title_surf.get_rect(center=(th.WINDOW_WIDTH // 2, 180 - title_offset))
        surface.blit(title_surf, title_rect)

        if title_appear > 0.3:
            line_w = int(60 * title_appear)
            line_rect = pygame.Rect(0, 0, line_w, 3)
            line_rect.center = (th.WINDOW_WIDTH // 2, 220 - title_offset)
            pygame.draw.rect(surface, th.ACCENT, line_rect, border_radius=2)

        for card in self.cards:
            card.draw(surface)

        hint_font = th.get_font(12)
        hint_surf = hint_font.render("Press ESC to exit", True, th.TEXT_TERTIARY)
        hint_surf.set_alpha(title_alpha)
        hint_rect = hint_surf.get_rect(center=(th.WINDOW_WIDTH // 2, th.WINDOW_HEIGHT - 30))
        surface.blit(hint_surf, hint_rect)