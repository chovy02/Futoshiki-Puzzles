"""Game screen - board + side panel with algorithm selection and controls."""
import os
import pygame
from . import theme as th
from .widgets import Button, draw_dotted_bg
from utils.file_io import read_input_file
from solvers.forward_chaining import ForwardChainingSolver


def find_outputs_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "..", "outputs"),
        os.path.join(here, "..", "outputs"),
        os.path.abspath("outputs"),
    ]
    for c in candidates:
        parent = os.path.dirname(c)
        if os.path.isdir(parent):
            return os.path.abspath(c)
    return os.path.abspath("outputs")


class GameScreen:
    def __init__(self, app, difficulty, level, input_path):
        self.app = app
        self.difficulty = difficulty
        self.level = level
        self.input_path = input_path

        self.original_state = read_input_file(input_path)
        self.state = self.original_state.clone()
        self.N = self.state.N

        self.solver = None
        self.steps = []
        self.step_idx = 0
        self.is_solved = False
        self.solve_time = 0.0
        self.nodes_expanded = 0
        self.last_step = None
        self.cell_anim = {}

        self.auto_play = False
        self.auto_speed = 6.0
        self.auto_accum = 0.0

        self.algo = "Forward chaining"
        self.status_msg = ""
        self.status_color = th.TEXT_SECONDARY
        self.title_t = 0.0

        # Layout
        self.board_area = pygame.Rect(60, 110, 720, 640)
        self._compute_board_layout()

        panel_x = 820
        panel_w = 400
        self.panel_rect = pygame.Rect(panel_x, 110, panel_w, 640)

        # Buttons
        self.back_btn = Button((40, 32, 110, 38), "← Back", self._go_back, font_size=14)

        bx = panel_x + 20
        gap = 10
        bw = (panel_w - 40 - gap) // 2
        btn_h = 42

        by = self.panel_rect.bottom - 24 - (btn_h * 3 + gap * 2)
        self.solve_btn = Button((bx, by, bw, btn_h), "Solve", self._solve, primary=True, font_size=15)
        self.step_btn = Button((bx + bw + gap, by, bw, btn_h), "Step", self._step, font_size=15)
        by += btn_h + gap
        self.auto_btn = Button((bx, by, bw, btn_h), "Auto play", self._toggle_auto, font_size=15)
        self.reset_btn = Button((bx + bw + gap, by, bw, btn_h), "Reset", self._reset, font_size=15)
        by += btn_h + gap
        bw3 = (panel_w - 40 - gap * 2) // 3
        self.prev_btn = Button((bx, by, bw3, btn_h), "‹ Prev", self._prev, font_size=14)
        self.next_btn = Button((bx + bw3 + gap, by, bw3, btn_h), "Next ›", self._step, font_size=14)
        self.menu_btn = Button((bx + 2 * (bw3 + gap), by, bw3, btn_h), "Menu", self._go_to_menu, font_size=14)

        self.buttons = [
            self.back_btn, self.solve_btn, self.step_btn, self.auto_btn,
            self.reset_btn, self.prev_btn, self.next_btn, self.menu_btn,
        ]

    def _compute_board_layout(self):
        N = self.N
        sign_size = 24
        avail = min(self.board_area.w, self.board_area.h) - sign_size * (N - 1) - 60
        cell = max(40, min(110, avail // N))
        self.cell_size = cell
        self.sign_size = sign_size
        total = cell * N + sign_size * (N - 1)
        self.board_x = self.board_area.x + (self.board_area.w - total) // 2
        self.board_y = self.board_area.y + (self.board_area.h - total) // 2

    def _cell_rect(self, r, c):
        x = self.board_x + c * (self.cell_size + self.sign_size)
        y = self.board_y + r * (self.cell_size + self.sign_size)
        return pygame.Rect(x, y, self.cell_size, self.cell_size)

    # ----- Solver actions -----

    def _ensure_steps(self):
        """Run the solver if we haven't yet, populate self.steps."""
        if self.steps:
            return True
        self.solver = ForwardChainingSolver(self.original_state)
        result = self.solver.solve()
        self.steps = list(self.solver.steps)
        self.solve_time = self.solver.elapsed
        self.nodes_expanded = self.solver.nodes_expanded
        if result is None:
            self.status_msg = "No solution found"
            self.status_color = th.ERROR
            return False
        return True

    def _solve(self):
        if not self._ensure_steps():
            return
        # Jump immediately to fully solved
        self.step_idx = len(self.steps)
        self._rebuild_state_from_steps()
        if self.steps:
            r, c, v = self.steps[-1]
            self.last_step = (r, c, v)
        self.is_solved = True
        self._save_output()
        self.status_msg = f"Solved in {self.solve_time * 1000:.1f} ms"
        self.status_color = th.SUCCESS

    def _step(self):
        if not self._ensure_steps():
            return
        if self.step_idx < len(self.steps):
            r, c, v = self.steps[self.step_idx]
            self.state.grid[r][c] = v
            self.cell_anim[(r, c)] = 0.0
            self.last_step = (r, c, v)
            self.step_idx += 1
            if self.step_idx == len(self.steps):
                self.is_solved = True
                self._save_output()
                self.status_msg = f"Solved in {self.solve_time * 1000:.1f} ms"
                self.status_color = th.SUCCESS

    def _toggle_auto(self):
        if not self._ensure_steps():
            return
        self.auto_play = not self.auto_play
        self.auto_btn.text = "Pause" if self.auto_play else "Auto play"

    def _reset(self):
        self.state = self.original_state.clone()
        self.steps = []
        self.step_idx = 0
        self.is_solved = False
        self.solve_time = 0.0
        self.nodes_expanded = 0
        self.last_step = None
        self.cell_anim = {}
        self.auto_play = False
        self.auto_btn.text = "Auto play"
        self.status_msg = ""

    def _prev(self):
        if self.step_idx > 0:
            self.step_idx -= 1
            self._rebuild_state_from_steps()
            self.last_step = self.steps[self.step_idx - 1] if self.step_idx > 0 else None
            self.is_solved = False
            self.auto_play = False
            self.auto_btn.text = "Auto play"

    def _rebuild_state_from_steps(self):
        self.state = self.original_state.clone()
        self.cell_anim = {}
        for i in range(self.step_idx):
            r, c, v = self.steps[i]
            self.state.grid[r][c] = v
            self.cell_anim[(r, c)] = 1.0
        if self.step_idx > 0:
            r, c, _ = self.steps[self.step_idx - 1]
            self.cell_anim[(r, c)] = 0.0

    def _save_output(self):
        out_dir = find_outputs_dir()
        try:
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"output-{self.level:02d}.txt")
            with open(path, "w", encoding="utf-8") as f:
                self._write_state(f)
            self.output_path = path
        except Exception as e:
            print(f"[warn] cannot save output: {e}")

    def _write_state(self, f):
        N = self.N
        for r in range(N):
            line = ""
            for c in range(N):
                line += str(self.state.grid[r][c])
                if c < N - 1:
                    h = self.state.h_constraints[r][c]
                    if h == 1:
                        line += " < "
                    elif h == -1:
                        line += " > "
                    else:
                        line += "   "
            f.write(line + "\n")
            if r < N - 1:
                vline = ""
                for c in range(N):
                    v = self.state.v_constraints[r][c]
                    if v == 1:
                        vline += "^   "
                    elif v == -1:
                        vline += "v   "
                    else:
                        vline += "    "
                f.write(vline + "\n")

    def _go_back(self):
        from .level_screen import LevelScreen
        self.app.transition_to(LevelScreen(self.app, self.difficulty))

    def _go_to_menu(self):
        from .difficulty_screen import DifficultyScreen
        self.app.transition_to(DifficultyScreen(self.app))

    # ----- Loop -----

    def handle_event(self, event):
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt, mouse_pos):
        self.title_t = min(1.0, self.title_t + dt * 3)
        for btn in self.buttons:
            btn.update(dt, mouse_pos)

        for k in list(self.cell_anim.keys()):
            self.cell_anim[k] = min(1.0, self.cell_anim[k] + dt * 5)

        if self.auto_play and self.steps:
            self.auto_accum += dt * self.auto_speed
            while self.auto_accum >= 1.0 and self.step_idx < len(self.steps):
                self.auto_accum -= 1.0
                r, c, v = self.steps[self.step_idx]
                self.state.grid[r][c] = v
                self.cell_anim[(r, c)] = 0.0
                self.last_step = (r, c, v)
                self.step_idx += 1
            if self.step_idx >= len(self.steps):
                self.auto_play = False
                self.auto_btn.text = "Auto play"
                if not self.is_solved:
                    self.is_solved = True
                    self._save_output()
                    self.status_msg = f"Solved in {self.solve_time * 1000:.1f} ms"
                    self.status_color = th.SUCCESS

    # ----- Draw -----

    def draw(self, surface):
        surface.fill(th.BG_PRIMARY)
        draw_dotted_bg(surface, alpha=8)

        self._draw_header(surface)

        # Board container
        board_bg = self.board_area.inflate(20, 20)
        pygame.draw.rect(surface, th.BG_SECONDARY, board_bg, border_radius=18)
        pygame.draw.rect(surface, th.BORDER, board_bg, width=1, border_radius=18)

        self._draw_board(surface)
        self._draw_panel(surface)

        for btn in self.buttons:
            btn.draw(surface)

    def _draw_header(self, surface):
        from .level_screen import DIFFICULTY_INFO
        info = DIFFICULTY_INFO[self.difficulty]
        title_appear = th.ease_out_cubic(self.title_t)
        alpha = int(255 * title_appear)
        offset = int((1 - title_appear) * 10)

        pill_text = info["name"].upper()
        pill_font = th.get_font(12, bold=True)
        pill_surf = pill_font.render(pill_text, True, info["color"])
        pill_w = pill_surf.get_width() + 22
        pill_h = 24
        pill_bg = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pygame.draw.rect(pill_bg, (*info["color"], 30), pill_bg.get_rect(), border_radius=12)
        pygame.draw.rect(pill_bg, (*info["color"], 130), pill_bg.get_rect(), width=1, border_radius=12)
        pill_bg.blit(pill_surf, (11, (pill_h - pill_surf.get_height()) // 2))
        pill_bg.set_alpha(alpha)
        pill_rect = pill_bg.get_rect()
        pill_rect.topleft = (170, 39 - offset)
        surface.blit(pill_bg, pill_rect)

        info_font = th.get_font(15)
        info_text = f"Level {self.level}  ·  {self.N}×{self.N}  ·  {self.algo}"
        info_surf = info_font.render(info_text, True, th.TEXT_SECONDARY)
        info_surf.set_alpha(alpha)
        surface.blit(info_surf, (pill_rect.right + 14, pill_rect.centery - info_surf.get_height() // 2))

    def _draw_board(self, surface):
        N = self.N
        cs = self.cell_size
        ss = self.sign_size
        original_grid = self.original_state.grid
        last_rc = (self.last_step[0], self.last_step[1]) if self.last_step else None

        for r in range(N):
            for c in range(N):
                rect = self._cell_rect(r, c)
                val = self.state.grid[r][c]
                is_given = original_grid[r][c] != 0
                is_current = last_rc == (r, c)

                if is_given:
                    bg, border, text_col = th.CELL_GIVEN_BG, th.CELL_GIVEN_BORDER, th.CELL_GIVEN_TEXT
                elif val != 0:
                    if is_current:
                        bg, border, text_col = th.CELL_CURRENT_BG, th.CELL_CURRENT_BORDER, th.CELL_CURRENT_TEXT
                    else:
                        bg, border, text_col = th.CELL_SOLVED_BG, th.CELL_SOLVED_BORDER, th.CELL_SOLVED_TEXT
                else:
                    bg, border, text_col = th.CELL_EMPTY_BG, th.CELL_EMPTY_BORDER, th.CELL_EMPTY_TEXT

                pygame.draw.rect(surface, bg, rect, border_radius=8)
                pygame.draw.rect(surface, border, rect, width=2 if is_current else 1, border_radius=8)

                if is_current:
                    t = (pygame.time.get_ticks() % 1500) / 1500.0
                    pulse = 1 - abs(t * 2 - 1)
                    glow_alpha = int(70 * pulse)
                    glow_pad = int(2 + pulse * 5)
                    glow_rect = rect.inflate(glow_pad * 2, glow_pad * 2)
                    glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(glow, (*border, glow_alpha), glow.get_rect(),
                                     width=2, border_radius=10)
                    surface.blit(glow, glow_rect)

                if val != 0:
                    scale = 1.0
                    if (r, c) in self.cell_anim:
                        anim_t = self.cell_anim[(r, c)]
                        if anim_t < 1.0:
                            scale = 0.4 + 0.6 * th.ease_out_back(anim_t)
                    font_size = max(12, int(cs * 0.55 * scale))
                    val_font = th.get_font(font_size, bold=True)
                    val_surf = val_font.render(str(val), True, text_col)
                    val_rect = val_surf.get_rect(center=rect.center)
                    surface.blit(val_surf, val_rect)

        sign_font = th.get_font(max(12, int(cs * 0.32)), bold=True)
        for r in range(N):
            for c in range(N - 1):
                h = self.state.h_constraints[r][c]
                if h == 0:
                    continue
                ch = "<" if h == 1 else ">"
                cx = self.board_x + c * (cs + ss) + cs + ss // 2
                cy = self.board_y + r * (cs + ss) + cs // 2
                ssurf = sign_font.render(ch, True, th.SIGN_COLOR)
                surface.blit(ssurf, ssurf.get_rect(center=(cx, cy)))
        for r in range(N - 1):
            for c in range(N):
                v = self.state.v_constraints[r][c]
                if v == 0:
                    continue
                ch = "^" if v == 1 else "v"
                cx = self.board_x + c * (cs + ss) + cs // 2
                cy = self.board_y + r * (cs + ss) + cs + ss // 2
                ssurf = sign_font.render(ch, True, th.SIGN_COLOR)
                surface.blit(ssurf, ssurf.get_rect(center=(cx, cy)))

    def _draw_panel(self, surface):
        rect = self.panel_rect
        pygame.draw.rect(surface, th.BG_SECONDARY, rect, border_radius=18)
        pygame.draw.rect(surface, th.BORDER, rect, width=1, border_radius=18)

        font_section = th.get_font(11, bold=True)
        font_label = th.get_font(11, bold=True)

        y = rect.y + 22

        # Section: Algorithm
        sec = font_section.render("ALGORITHM", True, th.TEXT_TERTIARY)
        surface.blit(sec, (rect.x + 22, y))
        y += 20

        algo_rect = pygame.Rect(rect.x + 20, y, rect.w - 40, 46)
        pygame.draw.rect(surface, th.BG_TERTIARY, algo_rect, border_radius=10)
        pygame.draw.rect(surface, th.BORDER, algo_rect, width=1, border_radius=10)

        algo_font = th.get_font(15, bold=True)
        algo_surf = algo_font.render(self.algo, True, th.TEXT_PRIMARY)
        surface.blit(algo_surf, (algo_rect.x + 16,
                                 algo_rect.centery - algo_surf.get_height() // 2))

        # "Active" badge on the right
        badge_font = th.get_font(10, bold=True)
        badge_surf = badge_font.render("ACTIVE", True, th.ACCENT)
        bw = badge_surf.get_width() + 14
        bh = 20
        badge_rect = pygame.Rect(0, 0, bw, bh)
        badge_rect.right = algo_rect.right - 12
        badge_rect.centery = algo_rect.centery
        badge_layer = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(badge_layer, (*th.ACCENT, 32), badge_layer.get_rect(), border_radius=10)
        pygame.draw.rect(badge_layer, th.ACCENT_DIM, badge_layer.get_rect(), width=1, border_radius=10)
        surface.blit(badge_layer, badge_rect)
        surface.blit(badge_surf, (badge_rect.x + 7,
                                  badge_rect.centery - badge_surf.get_height() // 2))

        y = algo_rect.bottom + 22

        # Section: Stats (4 cards, 2x2)
        sec = font_section.render("STATISTICS", True, th.TEXT_TERTIARY)
        surface.blit(sec, (rect.x + 22, y))
        y += 20

        stat_w = (rect.w - 40 - 10) // 2
        stat_h = 64

        def draw_stat(x, y, label, value, color=None):
            srect = pygame.Rect(x, y, stat_w, stat_h)
            pygame.draw.rect(surface, th.BG_TERTIARY, srect, border_radius=10)
            lab_surf = font_label.render(label, True, th.TEXT_TERTIARY)
            surface.blit(lab_surf, (srect.x + 14, srect.y + 12))
            val_font = th.get_font(20, bold=True)
            val_surf = val_font.render(value, True, color or th.TEXT_PRIMARY)
            surface.blit(val_surf, (srect.x + 14, srect.y + 28))

        cells_filled = sum(1 for r in range(self.N) for c in range(self.N)
                           if self.state.grid[r][c] != 0)
        total = self.N * self.N

        time_text = f"{self.solve_time * 1000:.1f}ms" if self.solve_time > 0 else "—"
        draw_stat(rect.x + 20, y, "TIME", time_text,
                  th.SUCCESS if self.is_solved else None)
        draw_stat(rect.x + 20 + stat_w + 10, y, "EXPANDED",
                  str(self.nodes_expanded) if self.nodes_expanded > 0 else "—")
        y += stat_h + 10
        steps_text = f"{self.step_idx}/{len(self.steps)}" if self.steps else "—"
        draw_stat(rect.x + 20, y, "STEPS", steps_text)
        draw_stat(rect.x + 20 + stat_w + 10, y, "FILLED", f"{cells_filled}/{total}")
        y += stat_h + 18

        # Section: Current step
        sec = font_section.render("CURRENT STEP", True, th.TEXT_TERTIARY)
        surface.blit(sec, (rect.x + 22, y))
        y += 20

        step_rect = pygame.Rect(rect.x + 20, y, rect.w - 40, 46)
        pygame.draw.rect(surface, th.BG_TERTIARY, step_rect, border_radius=10)

        if self.last_step:
            r, c, v = self.last_step
            step_text = f"Val({r + 1}, {c + 1}, {v})"
            step_color = th.ACCENT
        else:
            step_text = "—"
            step_color = th.TEXT_TERTIARY
        step_font = th.get_mono(15, bold=True)
        step_surf = step_font.render(step_text, True, step_color)
        surface.blit(step_surf, (step_rect.x + 16,
                                 step_rect.centery - step_surf.get_height() // 2))
        y = step_rect.bottom + 14

        # Section: Output info / status
        if self.is_solved:
            mono = th.get_mono(11)
            label_surf = font_section.render("AUTO SAVED", True, th.TEXT_TERTIARY)
            surface.blit(label_surf, (rect.x + 22, y))
            y += 18
            path_surf = mono.render(f"outputs/output-{self.level:02d}.txt", True, th.SUCCESS)
            surface.blit(path_surf, (rect.x + 22, y))
        elif self.status_msg:
            status_font = th.get_font(13)
            status_surf = status_font.render(self.status_msg, True, self.status_color)
            surface.blit(status_surf, (rect.x + 22, y))