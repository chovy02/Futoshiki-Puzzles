"""Main App: window, screen management, fade transitions."""
import sys
import pygame
from . import theme as th


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Futoshiki Solver")
        self.screen = pygame.display.set_mode((th.WINDOW_WIDTH, th.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.current_screen = None
        self.next_screen = None
        self.transition_t = 0.0
        self.transitioning = False
        self.running = True

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
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                elif not self.transitioning and self.current_screen:
                    self.current_screen.handle_event(event)

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
                self.current_screen.draw(self.screen)

            if self.transitioning:
                t = self.transition_t
                if t < 0.5:
                    alpha = int(t * 2 * 255)
                else:
                    alpha = int((1 - (t - 0.5) * 2) * 255)
                overlay = pygame.Surface((th.WINDOW_WIDTH, th.WINDOW_HEIGHT))
                overlay.fill(th.BG_PRIMARY)
                overlay.set_alpha(alpha)
                self.screen.blit(overlay, (0, 0))

            pygame.display.flip()

        pygame.quit()
        sys.exit()