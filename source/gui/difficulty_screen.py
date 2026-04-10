"""Difficulty selection screen - 4 cards (Easy/Medium/Hard/Extreme)."""
import pygame
from . import theme as th
from .widgets import Button, draw_dotted_bg


class DifficultyCard:
    def __init__(self, rect, name, range_text, color, callback, enabled=True):
        self.rect = pygame.Rect(rect)
        self.name = name
        self.range_text = range_text
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
        self.appear_t = min(1.0, self.appear_t + dt * 3)
        target = 1.0 if (self.enabled and self.rect.collidepoint(mouse_pos)) else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 11)

    def draw(self, surface):
        if self.appear_t <= 0:
            return
        appear = th.ease_out_cubic(self.appear_t)
        offset_y = int((1 - appear) * 30)
        rect = self.rect.move(0, offset_y - int(self.hover_t * 6))
        alpha = int(255 * appear)

        if self.enabled:
            bg_color = th.lerp_color(th.BG_SECONDARY, th.BG_ELEVATED, self.hover_t)
            border_color = th.lerp_color(th.BORDER, self.color, self.hover_t * 0.85 + 0.15)
            border_width = 1 + int(self.hover_t * 1.5)
        else:
            bg_color = th.BG_SECONDARY
            border_color = th.BORDER
            border_width = 1

        temp = pygame.Surface(rect.size, pygame.SRCALPHA)
        temp_rect = pygame.Rect(0, 0, rect.w, rect.h)
        pygame.draw.rect(temp, bg_color, temp_rect, border_radius=18)
        pygame.draw.rect(temp, border_color, temp_rect, width=border_width, border_radius=18)

        badge_radius = 38
        badge_center = (rect.w // 2, 95)
        if self.enabled:
            inner = th.lerp_color(th.BG_TERTIARY, th.BG_ELEVATED, self.hover_t)
            ring = th.lerp_color(self.color, (255, 255, 255), self.hover_t * 0.3)
            pygame.draw.circle(temp, inner, badge_center, badge_radius)
            pygame.draw.circle(temp, ring, badge_center, badge_radius, width=2)
        else:
            pygame.draw.circle(temp, th.BG_TERTIARY, badge_center, badge_radius)
            pygame.draw.circle(temp, th.BORDER, badge_center, badge_radius, width=1)

        badge_font = th.get_font(36, bold=True)
        letter = self.name[0]
        letter_color = self.color if self.enabled else th.TEXT_DISABLED
        letter_surf = badge_font.render(letter, True, letter_color)
        letter_rect = letter_surf.get_rect(center=badge_center)
        temp.blit(letter_surf, letter_rect)

        name_color = th.TEXT_PRIMARY if self.enabled else th.TEXT_DISABLED
        if self.enabled:
            name_color = th.lerp_color(th.TEXT_PRIMARY, self.color, self.hover_t * 0.5)
        name_font = th.get_font(35, bold=True)
        name_surf = name_font.render(self.name, True, name_color)
        name_rect = name_surf.get_rect(center=(rect.w // 2, 175))
        temp.blit(name_surf, name_rect)

        range_color = th.TEXT_TERTIARY if self.enabled else th.TEXT_DISABLED
        range_font = th.get_font(13)
        range_surf = range_font.render(self.range_text, True, range_color)
        range_rect = range_surf.get_rect(center=(rect.w // 2, 205))
        temp.blit(range_surf, range_rect)

        if not self.enabled:
            cs_font = th.get_font(11)
            cs_surf = cs_font.render("COMING SOON", True, th.TEXT_DISABLED)
            cs_rect = cs_surf.get_rect(center=(rect.w // 2, rect.h - 22))
            temp.blit(cs_surf, cs_rect)

        if alpha < 255:
            temp.set_alpha(alpha)
        surface.blit(temp, rect)


class DifficultyScreen:
    def __init__(self, app, size_name):
        self.app = app
        self.size_name = size_name
        self.title_t = 0.0

        card_w = 230
        card_h = 280
        gap = 28
        total_w = card_w * 4 + gap * 3
        start_x = (th.WINDOW_WIDTH - total_w) // 2
        center_y = th.WINDOW_HEIGHT // 2 + 30
        y = center_y - card_h // 2

        self.cards = [
            DifficultyCard((start_x + 0 * (card_w + gap), y, card_w, card_h),
                           "Easy", "2 Levels", th.EASY,
                           lambda: self._open("easy"), enabled=True),
            DifficultyCard((start_x + 1 * (card_w + gap), y, card_w, card_h),
                           "Medium", "3 Levels", th.MEDIUM,
                           lambda: self._open("medium"), enabled=True),
            DifficultyCard((start_x + 2 * (card_w + gap), y, card_w, card_h),
                           "Hard", "2 Levels", th.HARD,
                           lambda: self._open("hard"), enabled=True),
            DifficultyCard((start_x + 3 * (card_w + gap), y, card_w, card_h),
                           "Extreme", "2 Levels", th.EXTREME,
                           lambda: self._open("extreme"), enabled=True),
        ]
        for i, card in enumerate(self.cards):
            card.appear_delay = 0.15 + i * 0.09
            
        self.back_btn = Button((40, 32, 110, 38), "← Back", self._go_back, font_size=14)

    def _open(self, difficulty):
        from .level_screen import LevelScreen
        self.app.transition_to(LevelScreen(self.app, self.size_name, difficulty))
        
    def _go_back(self):
        from .size_screen import SizeScreen
        self.app.transition_to(SizeScreen(self.app))

    def handle_event(self, event):
        self.back_btn.handle_event(event)
        for card in self.cards:
            card.handle_event(event)

    def update(self, dt, mouse_pos):
        self.title_t = min(1.0, self.title_t + dt * 2)
        self.back_btn.update(dt, mouse_pos)
        for card in self.cards:
            card.update(dt, mouse_pos)

    def draw(self, surface):
        surface.fill(th.BG_PRIMARY)
        draw_dotted_bg(surface, alpha=8)

        title_appear = th.ease_out_cubic(self.title_t)
        title_alpha = int(255 * title_appear)
        title_offset = int((1 - title_appear) * 18)

        label_font = th.get_font(20, bold=True)
        label_surf = label_font.render(f"SIZE: {self.size_name}", True, th.ACCENT)
        label_surf.set_alpha(title_alpha)
        label_rect = label_surf.get_rect(center=(th.WINDOW_WIDTH // 2, 130 - title_offset))
        surface.blit(label_surf, label_rect)

        title_font = th.get_font(40, bold=True)
        title_surf = title_font.render("Select Difficulty", True, th.TEXT_PRIMARY)
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
            
        self.back_btn.draw(surface)