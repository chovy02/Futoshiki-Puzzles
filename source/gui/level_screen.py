"""Level selection screen - grid of level cards for the chosen difficulty."""
import os
import pygame
from . import theme as th
from .widgets import Button, draw_dotted_bg

SIZE_START_INDEX = {
    "4x4": 1,
    "5x5": 10,
    "6x6": 19,
    "7x7": 28,
    "9x9": 37
}

DIFFICULTY_INFO = {
    "easy":    {"name": "Easy",    "color": th.EASY,    "offset": 0, "count": 2},
    "medium":  {"name": "Medium",  "color": th.MEDIUM,  "offset": 2, "count": 3},
    "hard":    {"name": "Hard",    "color": th.HARD,    "offset": 5, "count": 2},
    "extreme": {"name": "Extreme", "color": th.EXTREME, "offset": 7, "count": 2},
}

def find_inputs_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in [
        os.path.join(here, "..", "inputs"),
        os.path.join(here, "..", "inputs"),
        os.path.abspath("inputs"),
    ]:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return os.path.abspath("inputs")


class LevelCard:
    def __init__(self, rect, level, color, callback, enabled=True):
        self.rect = pygame.Rect(rect)
        self.level = level
        self.color = color
        self.callback = callback
        self.enabled = enabled
        self.hover_t = 0.0
        self._was_pressed = False
        self.appear_t = 0.0
        self.appear_delay = 0.0

    def handle_event(self, event):
        if not self.enabled or self.appear_t < 0.5:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._was_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self._was_pressed
            self._was_pressed = False
            if was and self.rect.collidepoint(event.pos) and self.callback:
                self.callback()

    def update(self, dt, mouse_pos):
        if self.appear_delay > 0:
            self.appear_delay -= dt
            return
        self.appear_t = min(1.0, self.appear_t + dt * 4)
        target = 1.0 if (self.enabled and self.rect.collidepoint(mouse_pos)) else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 12)

    def draw(self, surface):
        if self.appear_t <= 0:
            return
        appear = th.ease_out_cubic(self.appear_t)
        offset_y = int((1 - appear) * 20)
        rect = self.rect.move(0, offset_y - int(self.hover_t * 5))
        alpha = int(255 * appear)

        if self.enabled:
            bg = th.lerp_color(th.BG_SECONDARY, th.BG_ELEVATED, self.hover_t)
            border = th.lerp_color(th.BORDER, self.color, self.hover_t * 0.9 + 0.1)
            bw = 1 + int(self.hover_t * 1.5)
        else:
            bg = th.BG_SECONDARY
            border = th.BORDER
            bw = 1

        temp = pygame.Surface(rect.size, pygame.SRCALPHA)
        tr = pygame.Rect(0, 0, rect.w, rect.h)
        pygame.draw.rect(temp, bg, tr, border_radius=14)
        pygame.draw.rect(temp, border, tr, width=bw, border_radius=14)

        num_color = th.TEXT_PRIMARY if self.enabled else th.TEXT_DISABLED
        if self.enabled:
            num_color = th.lerp_color(th.TEXT_PRIMARY, self.color, self.hover_t * 0.55)
        num_font = th.get_font(42, bold=True)
        num_surf = num_font.render(str(self.level), True, num_color)
        num_rect = num_surf.get_rect(center=(rect.w // 2, rect.h // 2 - 6))
        temp.blit(num_surf, num_rect)

        lbl_font = th.get_font(10, bold=True)
        lbl_color = th.TEXT_TERTIARY if self.enabled else th.TEXT_DISABLED
        lbl_surf = lbl_font.render("LEVEL", True, lbl_color)
        lbl_rect = lbl_surf.get_rect(center=(rect.w // 2, rect.h - 22))
        temp.blit(lbl_surf, lbl_rect)

        if alpha < 255:
            temp.set_alpha(alpha)
        surface.blit(temp, rect)


class LevelScreen:
    def __init__(self, app, size_name, difficulty):
        self.app = app
        self.size_name = size_name
        self.difficulty = difficulty
        self.info = DIFFICULTY_INFO[difficulty]
        self.title_t = 0.0

        base_idx = SIZE_START_INDEX[size_name]
        start_level = base_idx + self.info["offset"]
        end_level = start_level + self.info["count"] - 1

        inputs_dir = find_inputs_dir()

        card_w = 150
        card_h = 150
        gap = 22
        
        num_cards = self.info["count"]
        total_w = card_w * num_cards + gap * (num_cards - 1)
        start_x = (th.WINDOW_WIDTH - total_w) // 2
        start_y = (th.WINDOW_HEIGHT - card_h) // 2 + 30

        self.cards = []
        for i, real_lvl in enumerate(range(start_level, end_level + 1)):
            x = start_x + i * (card_w + gap)
            y = start_y
            path = os.path.join(inputs_dir, f"input-{real_lvl:02d}.txt")
            enabled = os.path.isfile(path)
            
            # CHỈNH SỬA Ở ĐÂY: Luôn đánh số bắt đầu từ 1, 2, 3... cho mỗi độ khó
            display_lvl = i + 1
            
            card = LevelCard((x, y, card_w, card_h), display_lvl, self.info["color"],
                             (lambda p=path, l=display_lvl: self._open(l, p)), enabled=enabled)
            card.appear_delay = 0.08 + i * 0.05
            self.cards.append(card)

        self.back_btn = Button((40, 32, 110, 38), "← Back", self._go_back, font_size=14)

    def _open(self, level, path):
        from .game_screen import GameScreen
        self.app.transition_to(GameScreen(self.app, self.size_name, self.difficulty, level, path))

    def _go_back(self):
        from .difficulty_screen import DifficultyScreen
        self.app.transition_to(DifficultyScreen(self.app, self.size_name))

    def handle_event(self, event):
        self.back_btn.handle_event(event)
        for card in self.cards:
            card.handle_event(event)

    def update(self, dt, mouse_pos):
        self.title_t = min(1.0, self.title_t + dt * 2.5)
        self.back_btn.update(dt, mouse_pos)
        for card in self.cards:
            card.update(dt, mouse_pos)

    def draw(self, surface):
        surface.fill(th.BG_PRIMARY)
        draw_dotted_bg(surface, alpha=8)

        appear = th.ease_out_cubic(self.title_t)
        alpha = int(255 * appear)
        offset = int((1 - appear) * 16)

        pill_font = th.get_font(12, bold=True)
        pill_txt = f"{self.size_name} - {self.info['name'].upper()}"
        pill_surf = pill_font.render(pill_txt, True, self.info["color"])
        pw = pill_surf.get_width() + 24
        ph = 26
        pill_bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(pill_bg, (*self.info["color"], 32), pill_bg.get_rect(), border_radius=13)
        pygame.draw.rect(pill_bg, (*self.info["color"], 140), pill_bg.get_rect(), width=1, border_radius=13)
        pill_bg.blit(pill_surf, (12, (ph - pill_surf.get_height()) // 2))
        pill_bg.set_alpha(alpha)
        pill_rect = pill_bg.get_rect(center=(th.WINDOW_WIDTH // 2, 120 - offset))
        surface.blit(pill_bg, pill_rect)

        title_font = th.get_font(48, bold=True)
        title_surf = title_font.render("Select a level", True, th.TEXT_PRIMARY)
        title_surf.set_alpha(alpha)
        title_rect = title_surf.get_rect(center=(th.WINDOW_WIDTH // 2, 170 - offset))
        surface.blit(title_surf, title_rect)

        if appear > 0.3:
            line_w = int(60 * appear)
            line_rect = pygame.Rect(0, 0, line_w, 3)
            line_rect.center = (th.WINDOW_WIDTH // 2, 205 - offset)
            pygame.draw.rect(surface, self.info["color"], line_rect, border_radius=2)

        for card in self.cards:
            card.draw(surface)

        self.back_btn.draw(surface)

        hint_font = th.get_font(12)
        hint_surf = hint_font.render("Click a level to start solving", True, th.TEXT_TERTIARY)
        hint_surf.set_alpha(alpha)
        hint_rect = hint_surf.get_rect(center=(th.WINDOW_WIDTH // 2, th.WINDOW_HEIGHT - 30))
        surface.blit(hint_surf, hint_rect)