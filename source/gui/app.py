"""Main App: window, screen management, fade transitions, resizable window."""
import sys
import pygame
from . import theme as th


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Futoshiki")
        self.render_w = th.WINDOW_WIDTH
        self.render_h = th.WINDOW_HEIGHT
        self.render_surface = pygame.Surface((self.render_w, self.render_h))

        self.screen = pygame.display.set_mode(
            (th.WINDOW_WIDTH, th.WINDOW_HEIGHT),
            pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()

        self.current_screen = None
        self.next_screen = None
        self.transition_t = 0.0
        self.transitioning = False
        self.running = True
        self._update_scale()

    def _update_scale(self):
        win_w, win_h = self.screen.get_size()
        scale_x = win_w / self.render_w
        scale_y = win_h / self.render_h
        self.scale = min(scale_x, scale_y)
        scaled_w = int(self.render_w * self.scale)
        scaled_h = int(self.render_h * self.scale)
        self.offset_x = (win_w - scaled_w) // 2
        self.offset_y = (win_h - scaled_h) // 2

    def _map_mouse(self, pos):
        x = (pos[0] - self.offset_x) / self.scale
        y = (pos[1] - self.offset_y) / self.scale
        x = max(0, min(self.render_w - 1, x))
        y = max(0, min(self.render_h - 1, y))
        return (int(x), int(y))

    def transition_to(self, screen):
        if self.current_screen is None:
            self.current_screen = screen
            return
        self.next_screen = screen
        self.transitioning = True
        self.transition_t = 0.0

    def run(self):
        from .size_screen import SizeScreen
        self.transition_to(SizeScreen(self))

        while self.running:
            dt = self.clock.tick(th.FPS) / 1000.0
            raw_mouse = pygame.mouse.get_pos()
            mouse_pos = self._map_mouse(raw_mouse)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE
                    )
                    self._update_scale()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                elif not self.transitioning and self.current_screen:
                    mapped_event = self._remap_event(event)
                    self.current_screen.handle_event(mapped_event)

            if self.transitioning:
                self.transition_t += dt * 3.5
                if self.transition_t >= 0.5 and self.next_screen is not None:
                    self.current_screen = self.next_screen
                    self.next_screen = None
                if self.transition_t >= 1.0:
                    self.transitioning = False
                    self.transition_t = 0.0

            if self.current_screen:
                self.current_screen.update(dt, mouse_pos)
                self.current_screen.draw(self.render_surface)

            if self.transitioning:
                t = self.transition_t
                if t < 0.5:
                    alpha = int(t * 2 * 255)
                else:
                    alpha = int((1 - (t - 0.5) * 2) * 255)
                overlay = pygame.Surface((self.render_w, self.render_h))
                overlay.fill(th.BG_PRIMARY)
                overlay.set_alpha(alpha)
                self.render_surface.blit(overlay, (0, 0))

            # Letterbox matches background color
            self.screen.fill(th.BG_PRIMARY)
            scaled_w = int(self.render_w * self.scale)
            scaled_h = int(self.render_h * self.scale)
            scaled = pygame.transform.smoothscale(
                self.render_surface, (scaled_w, scaled_h)
            )
            self.screen.blit(scaled, (self.offset_x, self.offset_y))
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _remap_event(self, event):
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            mapped = self._map_mouse(event.pos)
            return pygame.event.Event(event.type, {
                'pos': mapped, 'button': event.button,
            })
        elif event.type == pygame.MOUSEMOTION:
            mapped = self._map_mouse(event.pos)
            return pygame.event.Event(event.type, {
                'pos': mapped, 'rel': event.rel, 'buttons': event.buttons,
            })
        return event