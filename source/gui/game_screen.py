"""Game screen - board + side panel with algorithm selection and controls."""
import os
import threading
import tracemalloc
import pygame
from . import theme as th
from .widgets import Button, draw_dotted_bg
from utils.file_io import read_input_file
from solvers.forward_chaining import ForwardChainingSolver
from solvers.backward_chaining import BackwardChainingSolver
from solvers.bruteForce_backtracking import BruteForceBacktrackingSolver
from solvers.forward_chaining_tms import ForwardChainingTMSSolver


def find_outputs_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.dirname(here)
    return os.path.join(source_dir, "outputs")


def _fmt_memory(peak_bytes: int) -> str:
    if peak_bytes < 1024:
        return f"{peak_bytes} B"
    elif peak_bytes < 1024 * 1024:
        return f"{peak_bytes / 1024:.1f} KB"
    else:
        return f"{peak_bytes / 1024 / 1024:.1f} MB"


# Algorithms that produce a KB log
_LOG_ALGOS = ("Forward chaining", "Forward chaining (TMS)", "Backward chaining")


class GameScreen:
    ALGORITHMS = [
    "Forward chaining",
    "Forward chaining (TMS)",
    "Backward chaining",
    "PySAT",
    "Brute-force backtracking",
    "A* (h1: empty cells)",
    "A* (h2: empty + chains)",
    "A* (h3: AC-3)",
    ]

    # Height of KB log area (pixels)
    _KB_LOG_H = 200

    def __init__(self, app, size_name, difficulty, level, input_path):
        self.app = app
        self.size_name = size_name
        self.difficulty = difficulty
        self.level = level
        self.input_path = input_path

        self.original_state = read_input_file(input_path)
        self.state = self.original_state.clone()
        self.N = self.state.N

        self.solver = None
        self.is_solved = False
        self.solve_time = 0.0
        self.nodes_expanded = 0
        self.memory_peak = 0
        self.num_inferences = None
        self.num_initial_clauses = None
        self.total_number_of_clauses = None
        self.cell_anim = {}

        # Threading
        self.is_solving = False
        self.solve_thread = None
        self.thread_result = None
        self.stop_event = threading.Event()
        self.solve_gen = 0

        # Algorithm dropdown
        self.algo_index = 0
        self.algo = self.ALGORITHMS[self.algo_index]
        self.dropdown_open = False
        self.dropdown_hover = -1

        self.status_msg = ""
        self.status_color = th.TEXT_SECONDARY
        self.title_t = 0.0

        self.board_area = pygame.Rect(60, 110, 720, 640)
        self._compute_board_layout()

        panel_x = 820
        panel_w = 400
        self.panel_rect = pygame.Rect(panel_x, 110, panel_w, 640)

        self.back_btn = Button((40, 32, 110, 38), "← Back", self._go_back, font_size=14)

        bx = panel_x + 20
        gap = 10
        btn_h = 42
        bw3 = (panel_w - 40 - gap * 2) // 3
        by = self.panel_rect.bottom - 24 - btn_h

        self.solve_btn = Button((bx, by, bw3, btn_h), "Solve", self._solve, primary=True, font_size=15)
        self.reset_btn = Button((bx + bw3 + gap, by, bw3, btn_h), "Reset", self._reset, font_size=15)
        self.menu_btn  = Button((bx + 2*(bw3+gap), by, bw3, btn_h), "Menu", self._go_to_menu, font_size=14)

        self.buttons = [self.back_btn, self.solve_btn, self.reset_btn, self.menu_btn]
        self.algo_rect = pygame.Rect(panel_x + 20, self.panel_rect.y + 42, panel_w - 40, 46)

        # --- TÍNH NĂNG STEP-BY-STEP ---
        self.history_grids = []
        self.step_idx = 0
        self.is_stepping = False

        btn_w = (panel_w - 40 - 10) // 2
        self.prev_btn = Button((bx, by - btn_h - 15, btn_w, btn_h), "← Prev Step", self._step_prev, font_size=14)
        self.next_btn = Button((bx + btn_w + 10, by - btn_h - 15, btn_w, btn_h), "Next Step →", self._step_next, font_size=14, primary=True)

        # --- KB LOG (FC / FC-TMS / BC) ---
        self.kb_log_scroll = 0         # scroll offset in lines
        self._kb_log_cache: list = []  # snapshot read from solver each frame

    def _step_prev(self):
        if self.is_stepping and self.step_idx > 0:
            self.step_idx -= 1
            self.state.grid = [row[:] for row in self.history_grids[self.step_idx]]
            self.cell_anim = {}

    def _step_next(self):
        if self.is_stepping and self.step_idx < len(self.history_grids) - 1:
            self.step_idx += 1
            self.state.grid = [row[:] for row in self.history_grids[self.step_idx]]
            self.cell_anim = {}

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

    # ── Solver threading ──────────────────────────────────────────────────────

    def _make_solver(self):
        """Instantiate the correct solver. PySAT imported lazily."""
        if self.algo == "Forward chaining":
            return ForwardChainingSolver(self.original_state, stop_event=self.stop_event)
        elif self.algo == "Forward chaining (TMS)":
            return ForwardChainingTMSSolver(self.original_state, stop_event=self.stop_event)
        elif self.algo == "Backward chaining":
            return BackwardChainingSolver(self.original_state, stop_event=self.stop_event)
        elif self.algo == "Brute-force backtracking":
            return BruteForceBacktrackingSolver(self.original_state, stop_event=self.stop_event)
        elif self.algo == "A* (h1: empty cells)":
            from solvers.AStar1Solver import AStar1Solver
            return AStar1Solver(self.original_state, stop_event=self.stop_event)
        elif self.algo == "A* (h2: empty + chains)":
            from solvers.AStar2Solver import AStar2Solver
            return AStar2Solver(self.original_state, stop_event=self.stop_event)
        elif self.algo == "A* (h3: AC-3)":
            from solvers.AStar3Solver import AStar3Solver
            return AStar3Solver(self.original_state, stop_event=self.stop_event)
        else:  # PySAT — lazy import so missing file won't crash on startup
            from solvers.pysat_solver import PySATSolver
            return PySATSolver(self.original_state)

    def _run_solver_in_background(self, gen: int):
        tracemalloc.start()
        result = self.solver.solve()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed  = getattr(self.solver, 'elapsed', 0.0)
        nodes    = getattr(self.solver, 'nodes_expanded', 0)
        inferences = None
        num_initial_clauses = None
        total_number_of_clauses = None

        if self.algo in _LOG_ALGOS:
            inferences = getattr(self.solver, 'num_inferences', None)
            num_initial_clauses = getattr(self.solver, 'num_initial_clauses', None)
            total_number_of_clauses = getattr(self.solver, 'total_number_of_clauses', None)

        if gen == self.solve_gen:   # discard stale result if cancelled
            self.thread_result = {
                "result": result,
                "elapsed": elapsed,
                "nodes": nodes,
                "memory_peak": peak,
                "num_inferences": inferences,
                "num_initial_clauses": num_initial_clauses,
                "total_number_of_clauses": total_number_of_clauses,
                "history": getattr(self.solver, 'history', []),
                "kb_log": list(getattr(self.solver, 'kb_log_lines', [])),
            }

    def _solve(self):
        if self.is_solved or self.is_solving:
            return
        self.status_msg = "Solving..."
        self.status_color = th.TEXT_SECONDARY
        self.is_solving = True
        self.thread_result = None
        self.stop_event = threading.Event()
        self.solve_gen += 1
        self.solver = self._make_solver()
        self._kb_log_cache = []
        self.kb_log_scroll = 0
        self.solve_thread = threading.Thread(
            target=self._run_solver_in_background,
            args=(self.solve_gen,), daemon=True
        )
        self.solve_thread.start()

    def _cancel_solve(self):
        if self.is_solving:
            self.stop_event.set()
            self.solve_gen += 1
            self.is_solving = False
            self.thread_result = None
            self.status_msg = ""

    def _reset(self):
        self._cancel_solve()
        self.state = self.original_state.clone()
        self.is_solved = False
        self.solve_time = 0.0
        self.nodes_expanded = 0
        self.memory_peak = 0
        self.num_inferences = None
        self.cell_anim = {}
        self.status_msg = ""
        self.is_stepping = False
        self.history_grids = []
        self.num_initial_clauses = None
        self.total_number_of_clauses = None
        self._kb_log_cache = []
        self.kb_log_scroll = 0

    def _save_output(self):
        out_dir = find_outputs_dir()
        try:
            os.makedirs(out_dir, exist_ok=True)
            basename = os.path.basename(self.input_path)
            num = basename.replace("input-", "").replace(".txt", "")
            path = os.path.join(out_dir, f"output-{num}.txt")
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
                    if h == 1:    line += " < "
                    elif h == -1: line += " > "
                    else:          line += "   "
            f.write(line + "\n")
            if r < N - 1:
                vline = ""
                for c in range(N):
                    v = self.state.v_constraints[r][c]
                    if v == 1:    vline += "^   "
                    elif v == -1: vline += "v   "
                    else:          vline += "    "
                f.write(vline + "\n")

    def _go_back(self):
        self._cancel_solve()
        from .level_screen import LevelScreen
        self.app.transition_to(LevelScreen(self.app, self.size_name, self.difficulty))

    def _go_to_menu(self):
        self._cancel_solve()
        from .size_screen import SizeScreen
        self.app.transition_to(SizeScreen(self.app))

    # ── Event / Update / Draw ─────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse = event.pos

            if self.dropdown_open:
                for i, name in enumerate(self.ALGORITHMS):
                    item_rect = pygame.Rect(
                        self.algo_rect.x,
                        self.algo_rect.bottom + 4 + i * 44,
                        self.algo_rect.w, 44
                    )
                    if item_rect.collidepoint(mouse):
                        if i != self.algo_index:
                            self.algo_index = i
                            self.algo = self.ALGORITHMS[i]
                            self._reset()
                        break
                self.dropdown_open = False
                return

            if not self.is_solving and self.algo_rect.collidepoint(mouse):
                self.dropdown_open = True
                return

        # Mouse wheel — scroll KB log (FC / FC-TMS / BC)
        if event.type == pygame.MOUSEWHEEL:
            if self.algo in _LOG_ALGOS and self._kb_log_cache:
                self.kb_log_scroll = max(0, self.kb_log_scroll - event.y * 3)

        self.back_btn.handle_event(event)

        if not self.is_solving:
            self.solve_btn.handle_event(event)
            self.reset_btn.handle_event(event)
            self.menu_btn.handle_event(event)
            if getattr(self, 'is_stepping', False):
                self.prev_btn.handle_event(event)
                self.next_btn.handle_event(event)
        else:
            self.reset_btn.handle_event(event)
            self.menu_btn.handle_event(event)

    def update(self, dt, mouse_pos):
        self.title_t = min(1.0, self.title_t + dt * 3)
        for btn in self.buttons:
            btn.update(dt, mouse_pos)

        if getattr(self, 'is_stepping', False):
            self.prev_btn.update(dt, mouse_pos)
            self.next_btn.update(dt, mouse_pos)

        if self.dropdown_open:
            self.dropdown_hover = -1
            for i in range(len(self.ALGORITHMS)):
                item_rect = pygame.Rect(
                    self.algo_rect.x,
                    self.algo_rect.bottom + 4 + i * 44,
                    self.algo_rect.w, 44
                )
                if item_rect.collidepoint(mouse_pos):
                    self.dropdown_hover = i

        # Poll KB log while solving (FC / FC-TMS / BC)
        if self.is_solving and self.algo in _LOG_ALGOS and self.solver:
            self._kb_log_cache = list(getattr(self.solver, 'kb_log_lines', []))
            # Auto-scroll to bottom while solving
            self.kb_log_scroll = max(0, len(self._kb_log_cache) - 1)

        if self.is_solving and self.thread_result is not None:
            res = self.thread_result["result"]
            self.solve_time     = self.thread_result["elapsed"]
            self.nodes_expanded = self.thread_result["nodes"]
            self.memory_peak    = self.thread_result["memory_peak"]
            self.num_inferences = self.thread_result["num_inferences"]
            self.num_initial_clauses = self.thread_result.get("num_initial_clauses", None)
            self.total_number_of_clauses = self.thread_result.get("total_number_of_clauses", None)
            self.history_grids  = self.thread_result.get("history", [])
            self._kb_log_cache  = self.thread_result.get("kb_log", [])

            if res is None:
                self.status_msg   = "No solution found"
                self.status_color = th.ERROR
            else:
                self.state    = res
                self.is_solved = True
                self.status_msg   = f"Solved in {self.solve_time * 1000:.1f} ms"
                self.status_color = th.SUCCESS
                self._save_output()
                for r in range(self.N):
                    for c in range(self.N):
                        if self.original_state.grid[r][c] == 0 and self.state.grid[r][c] != 0:
                            self.cell_anim[(r, c)] = 0.0

            if self.history_grids and self.algo == "Brute-force backtracking":
                self.is_stepping = True
                self.step_idx = len(self.history_grids) - 1
                self.state.grid = [row[:] for row in self.history_grids[self.step_idx]]
            else:
                self.is_stepping = False

            self.is_solving    = False
            self.thread_result = None

        for k in list(self.cell_anim.keys()):
            self.cell_anim[k] = min(1.0, self.cell_anim[k] + dt * 5)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface):
        surface.fill(th.BG_PRIMARY)
        draw_dotted_bg(surface, alpha=8)
        self._draw_header(surface)

        board_bg = self.board_area.inflate(20, 20)
        pygame.draw.rect(surface, th.BG_SECONDARY, board_bg, border_radius=18)
        pygame.draw.rect(surface, th.BORDER, board_bg, width=1, border_radius=18)

        self._draw_board(surface)
        self._draw_panel(surface)
        for btn in self.buttons:
            btn.draw(surface)
        if self.dropdown_open:
            self._draw_dropdown(surface)

    def _draw_header(self, surface):
        from .level_screen import DIFFICULTY_INFO
        info = DIFFICULTY_INFO[self.difficulty]
        title_appear = th.ease_out_cubic(self.title_t)
        alpha  = int(255 * title_appear)
        offset = int((1 - title_appear) * 10)

        pill_text = f"{self.size_name} · {info['name'].upper()}"
        pill_font = th.get_font(12, bold=True)
        pill_surf = pill_font.render(pill_text, True, info["color"])
        pill_w, pill_h = pill_surf.get_width() + 22, 24
        pill_bg = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pygame.draw.rect(pill_bg, (*info["color"], 30), pill_bg.get_rect(), border_radius=12)
        pygame.draw.rect(pill_bg, (*info["color"], 130), pill_bg.get_rect(), width=1, border_radius=12)
        pill_bg.blit(pill_surf, (11, (pill_h - pill_surf.get_height()) // 2))
        pill_bg.set_alpha(alpha)
        pill_rect = pill_bg.get_rect(topleft=(170, 39 - offset))
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

        for r in range(N):
            for c in range(N):
                rect = self._cell_rect(r, c)
                val = self.state.grid[r][c]
                is_given = original_grid[r][c] != 0

                if is_given:
                    bg, border, text_col = th.CELL_GIVEN_BG, th.CELL_GIVEN_BORDER, th.CELL_GIVEN_TEXT
                elif val != 0:
                    bg, border, text_col = th.CELL_SOLVED_BG, th.CELL_SOLVED_BORDER, th.CELL_SOLVED_TEXT
                else:
                    bg, border, text_col = th.CELL_EMPTY_BG, th.CELL_EMPTY_BORDER, th.CELL_EMPTY_TEXT

                pygame.draw.rect(surface, bg, rect, border_radius=8)
                pygame.draw.rect(surface, border, rect, width=1, border_radius=8)

                if val != 0:
                    scale = 1.0
                    if (r, c) in self.cell_anim:
                        t = self.cell_anim[(r, c)]
                        if t < 1.0:
                            scale = 0.4 + 0.6 * th.ease_out_back(t)
                    font_size = max(12, int(cs * 0.55 * scale))
                    val_font = th.get_font(font_size, bold=True)
                    val_surf = val_font.render(str(val), True, text_col)
                    surface.blit(val_surf, val_surf.get_rect(center=rect.center))

        sign_font = th.get_font(max(12, int(cs * 0.32)), bold=True)
        for r in range(N):
            for c in range(N - 1):
                h = self.state.h_constraints[r][c]
                if h == 0: continue
                cx = self.board_x + c * (cs + ss) + cs + ss // 2
                cy = self.board_y + r * (cs + ss) + cs // 2
                s = sign_font.render("<" if h == 1 else ">", True, th.SIGN_COLOR)
                surface.blit(s, s.get_rect(center=(cx, cy)))
        for r in range(N - 1):
            for c in range(N):
                v = self.state.v_constraints[r][c]
                if v == 0: continue
                cx = self.board_x + c * (cs + ss) + cs // 2
                cy = self.board_y + r * (cs + ss) + cs + ss // 2
                s = sign_font.render("^" if v == 1 else "v", True, th.SIGN_COLOR)
                surface.blit(s, s.get_rect(center=(cx, cy)))

    def _draw_panel(self, surface):
        rect = self.panel_rect
        pygame.draw.rect(surface, th.BG_SECONDARY, rect, border_radius=18)
        pygame.draw.rect(surface, th.BORDER, rect, width=1, border_radius=18)

        font_sec = th.get_font(11, bold=True)
        font_lbl = th.get_font(11, bold=True)

        # ── Algorithm box ──────────────────────────────────────────────────
        y = rect.y + 22
        surface.blit(font_sec.render("ALGORITHM", True, th.TEXT_TERTIARY), (rect.x + 22, y))
        y += 20

        ar = self.algo_rect
        algo_bg = th.BG_TERTIARY if not self.is_solving else th.BG_SECONDARY
        pygame.draw.rect(surface, algo_bg, ar, border_radius=10)
        pygame.draw.rect(surface, th.BORDER_HOVER if not self.is_solving else th.BORDER,
                         ar, width=1, border_radius=10)

        algo_surf = th.get_font(15, bold=True).render(self.algo, True, th.TEXT_PRIMARY)
        surface.blit(algo_surf, (ar.x + 16, ar.centery - algo_surf.get_height() // 2))

        if not self.is_solving:
            chev = th.get_font(12).render("▾", True, th.TEXT_TERTIARY)
            surface.blit(chev, (ar.right - chev.get_width() - 12,
                                ar.centery - chev.get_height() // 2))

        # Status badge
        if self.is_solving:
            btxt, bcol = "SOLVING...", th.WARNING
        elif self.is_solved:
            btxt, bcol = "DONE", th.SUCCESS
        else:
            btxt, bcol = "ACTIVE", th.ACCENT

        badge_surf = th.get_font(10, bold=True).render(btxt, True, bcol)
        bw, bh = badge_surf.get_width() + 14, 20
        badge_rect = pygame.Rect(0, 0, bw, bh)
        badge_rect.right   = ar.right - (30 if not self.is_solving else 12)
        badge_rect.centery = ar.centery
        bl = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(bl, (*bcol, 32), bl.get_rect(), border_radius=10)
        surface.blit(bl, badge_rect)
        surface.blit(badge_surf, (badge_rect.x + 7, badge_rect.centery - badge_surf.get_height() // 2))

        # ── Statistics ─────────────────────────────────────────────────────
        y = ar.bottom + 22
        surface.blit(font_sec.render("STATISTICS", True, th.TEXT_TERTIARY), (rect.x + 22, y))
        y += 20

        bx  = rect.x + 20
        pw  = rect.w - 40
        gap = 8
        sh  = 58
        sw2 = (pw - gap) // 2

        # --- VẼ NÚT STEP-BY-STEP ---
        if getattr(self, 'is_stepping', False):
            self.prev_btn.draw(surface)
            self.next_btn.draw(surface)
            step_text = f"Step: {self.step_idx + 1} / {len(self.history_grids)}"
            if len(self.history_grids) >= getattr(self.solver, 'MAX_HISTORY', 20000):
                step_text += " (Maxed)"
            step_surf = th.get_font(12, bold=True).render(step_text, True, th.TEXT_SECONDARY)
            surface.blit(step_surf, (self.prev_btn.rect.x, self.prev_btn.rect.y - 20))

        def stat_box(x, y, w, label, value, color=None):
            sr = pygame.Rect(x, y, w, sh)
            pygame.draw.rect(surface, th.BG_TERTIARY, sr, border_radius=10)
            surface.blit(font_lbl.render(label, True, th.TEXT_TERTIARY), (sr.x + 12, sr.y + 10))
            vs = th.get_font(18, bold=True).render(value, True, color or th.TEXT_PRIMARY)
            surface.blit(vs, (sr.x + 12, sr.y + 26))

        time_txt  = f"{self.solve_time * 1000:.1f}ms" if self.solve_time > 0 else "—"
        nodes_txt = str(self.nodes_expanded) if self.nodes_expanded > 0 else "—"
        mem_txt   = _fmt_memory(self.memory_peak) if self.memory_peak > 0 else "—"
        inf_txt   = str(self.num_inferences) if self.num_inferences is not None else "—"
        steps_txt = str(len(getattr(self, 'history_grids', []))) if getattr(self, 'history_grids', []) else "—"

        # Row 1: TIME | EXPANDED
        stat_box(bx,         y, sw2, "TIME", time_txt, th.SUCCESS if self.is_solved else None)
        stat_box(bx+sw2+gap, y, sw2, "EXPANDED", nodes_txt)
        y += sh + gap

        # Row 2+
        if self.algo in _LOG_ALGOS:
            stat_box(bx,         y, sw2, "MEMORY", mem_txt, th.INFO if self.memory_peak else None)
            stat_box(bx+sw2+gap, y, sw2, "INFERENCES", inf_txt)
            y += sh + gap
            init_cl_txt  = str(self.num_initial_clauses)  if self.num_initial_clauses  is not None else "—"
            total_cl_txt = str(self.total_number_of_clauses) if self.total_number_of_clauses is not None else "—"
            stat_box(bx,         y, sw2, "INIT CLAUSES",  init_cl_txt)
            stat_box(bx+sw2+gap, y, sw2, "TOTAL CLAUSES", total_cl_txt)
            y += sh + gap
        elif self.algo == "Brute-force backtracking":
            stat_box(bx,         y, sw2, "MEMORY", mem_txt, th.INFO if self.memory_peak else None)
            stat_box(bx+sw2+gap, y, sw2, "STEPS", steps_txt)
            y += sh + gap
        else:
            stat_box(bx, y, pw, "MEMORY", mem_txt, th.INFO if self.memory_peak else None)
            y += sh + gap

        # ── KB Log (FC / FC-TMS / BC) ──────────────────────────────────────
        if self.algo in _LOG_ALGOS:
            self._draw_kb_log(surface, bx, y, pw)

    def _draw_kb_log(self, surface, x: int, y: int, w: int) -> None:
        """Vẽ hộp log KB có thể cuộn cho FC / FC-TMS / BC."""
        font_sec = th.get_font(11, bold=True)
        surface.blit(font_sec.render("KB LOG", True, th.TEXT_TERTIARY), (x, y))
        y += 16

        log_h = self._KB_LOG_H
        log_rect = pygame.Rect(x, y, w, log_h)

        # Background
        pygame.draw.rect(surface, th.BG_TERTIARY, log_rect, border_radius=8)
        pygame.draw.rect(surface, th.BORDER, log_rect, width=1, border_radius=8)

        lines = self._kb_log_cache
        if not lines:
            empty_surf = th.get_font(11).render(
                "No log yet — press Solve" if not self.is_solving else "Solving...",
                True, th.TEXT_DISABLED
            )
            surface.blit(empty_surf, (x + 10, y + log_h // 2 - empty_surf.get_height() // 2))
            return

        line_font = th.get_font(13)
        line_h    = line_font.get_height() + 4
        visible   = log_h // line_h

        # Clamp scroll
        max_scroll = max(0, len(lines) - visible)
        self.kb_log_scroll = min(self.kb_log_scroll, max_scroll)

        # Clip drawing to log_rect
        old_clip = surface.get_clip()
        surface.set_clip(log_rect.inflate(-4, -4))

        for i, line in enumerate(lines[self.kb_log_scroll: self.kb_log_scroll + visible]):
            # Color-code lines
            if line.startswith("="):
                color = th.ACCENT
            elif line.strip().startswith("[") and "]" in line:
                color = th.MEDIUM
            elif "ASSERT" in line:
                color = th.SUCCESS
            elif "RETRACT" in line:
                color = th.ERROR
            elif "Query" in line:
                color = th.TEXT_PRIMARY
            elif "Conflict" in line and "=" in line:
                color = th.WARNING
            else:
                color = th.TEXT_SECONDARY

            txt_surf = line_font.render(line, True, color)
            surface.blit(txt_surf, (x + 6, y + 4 + i * line_h))

        surface.set_clip(old_clip)

        # Scrollbar
        if len(lines) > visible:
            sb_x    = x + w - 6
            sb_h    = log_h - 8
            thumb_h = max(16, int(sb_h * visible / len(lines)))
            thumb_y = y + 4 + int((sb_h - thumb_h) * self.kb_log_scroll / max_scroll) if max_scroll else y + 4
            pygame.draw.rect(surface, th.BORDER,     pygame.Rect(sb_x, y + 4, 3, sb_h),    border_radius=2)
            pygame.draw.rect(surface, th.ACCENT_DIM, pygame.Rect(sb_x, thumb_y, 3, thumb_h), border_radius=2)

        # Hint
        hint = th.get_font(9).render("scroll to navigate", True, th.TEXT_DISABLED)
        surface.blit(hint, (x + w - hint.get_width() - 8, y + log_h - hint.get_height() - 4))

    def _draw_dropdown(self, surface):
        ar   = self.algo_rect
        n    = len(self.ALGORITHMS)
        item_h = 44
        dh   = item_h * n + 8

        shadow = pygame.Surface((ar.w + 8, dh + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0,0,0,60), shadow.get_rect(), border_radius=12)
        surface.blit(shadow, (ar.x - 4, ar.bottom + 4))

        dd = pygame.Rect(ar.x, ar.bottom + 4, ar.w, dh)
        pygame.draw.rect(surface, th.BG_ELEVATED, dd, border_radius=12)
        pygame.draw.rect(surface, th.BORDER_HOVER, dd, width=1, border_radius=12)

        for i, name in enumerate(self.ALGORITHMS):
            ir = pygame.Rect(ar.x + 4, dd.y + 4 + i * item_h, ar.w - 8, item_h - 4)
            is_cur = (i == self.algo_index)
            is_hov = (i == self.dropdown_hover)

            if is_cur:
                pygame.draw.rect(surface, th.BG_TERTIARY, ir, border_radius=8)
            elif is_hov:
                hs = pygame.Surface(ir.size, pygame.SRCALPHA)
                pygame.draw.rect(hs, (*th.ACCENT, 20), hs.get_rect(), border_radius=8)
                surface.blit(hs, ir)

            tc = th.ACCENT if is_cur else (th.TEXT_PRIMARY if is_hov else th.TEXT_SECONDARY)
            ts = th.get_font(14, bold=is_cur).render(name, True, tc)
            surface.blit(ts, (ir.x + 14, ir.centery - ts.get_height() // 2))

            if is_cur:
                dot = th.get_font(10).render("●", True, th.ACCENT)
                surface.blit(dot, (ir.right - dot.get_width() - 12,
                                   ir.centery - dot.get_height() // 2))