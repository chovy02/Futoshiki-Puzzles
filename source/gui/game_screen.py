"""Game screen - board + side panel with algorithm selection and controls."""
import os
import time
import threading
import pygame
from . import theme as th
from .widgets import Button, draw_dotted_bg
from utils.file_io import read_input_file
from solvers.forward_chaining import ForwardChainingSolver
from solvers.backward_chaining import BackwardChainingSolver


def find_outputs_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.dirname(here)
    return os.path.join(source_dir, "outputs")


class GameScreen:
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
        self.cell_anim = {}

        # Biến phục vụ chạy ngầm (Threading)
        self.is_solving = False
        self.solve_thread = None
        self.thread_result = None

        self.algorithms = ["Forward chaining", "Backward chaining"]
        self.algo_index = 0
        self.algo = self.algorithms[self.algo_index]
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
        self.menu_btn = Button((bx + 2 * (bw3 + gap), by, bw3, btn_h), "Menu", self._go_to_menu, font_size=14)

        self.buttons = [
            self.back_btn, self.solve_btn, self.reset_btn, self.menu_btn
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

    # ----- Solver Threading -----

    def _run_solver_in_background(self):
        """Hàm này sẽ chạy trên một luồng riêng biệt."""
        start_time = time.perf_counter()
        
        # Gọi hàm solve của thuật toán
        result = self.solver.solve()
        
        elapsed = time.perf_counter() - start_time
        nodes = getattr(self.solver, 'nodes_expanded', 0)
        
        # Lưu kết quả vào biến tạm để luồng chính xử lý
        self.thread_result = {
            "result": result,
            "elapsed": elapsed,
            "nodes": nodes
        }

    def _solve(self):
        if self.is_solved or self.is_solving:
            return

        self.status_msg = "Solving..."
        self.status_color = th.TEXT_SECONDARY
        self.is_solving = True
        self.thread_result = None
        
        # Khởi tạo solver dựa trên thuật toán đã chọn
        if self.algo == "Forward chaining":
            self.solver = ForwardChainingSolver(self.original_state)
        elif self.algo == "Backward chaining":
            self.solver = BackwardChainingSolver(self.original_state)
            
        # Tạo và bắt đầu luồng chạy ngầm
        self.solve_thread = threading.Thread(target=self._run_solver_in_background)
        self.solve_thread.daemon = True # Tự động đóng thread khi tắt app
        self.solve_thread.start()

    def _reset(self):
        # Nếu đang giải thì không cho reset (để tránh xung đột thread)
        if self.is_solving:
            return
            
        self.state = self.original_state.clone()
        self.is_solved = False
        self.solve_time = 0.0
        self.nodes_expanded = 0
        self.cell_anim = {}
        self.status_msg = ""

    # ... (Các hàm _save_output, _write_state, _go_back giữ nguyên) ...

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
                    if h == 1: line += " < "
                    elif h == -1: line += " > "
                    else: line += "   "
            f.write(line + "\n")
            if r < N - 1:
                vline = ""
                for c in range(N):
                    v = self.state.v_constraints[r][c]
                    if v == 1: vline += "^   "
                    elif v == -1: vline += "v   "
                    else: vline += "    "
                f.write(vline + "\n")

    def _go_back(self):
        from .level_screen import LevelScreen
        self.app.transition_to(LevelScreen(self.app, self.size_name, self.difficulty))

    def _go_to_menu(self):
        from .size_screen import SizeScreen
        self.app.transition_to(SizeScreen(self.app))

    # ----- Loop -----

    def handle_event(self, event):
        # Chỉ nhận sự kiện nút bấm khi không đang giải
        if not self.is_solving:
            for btn in self.buttons:
                btn.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse = event.pos
                algo_rect = pygame.Rect(self.panel_rect.x + 20, self.panel_rect.y + 42, self.panel_rect.w - 40, 46)
                if algo_rect.collidepoint(mouse):
                    self.algo_index = (self.algo_index + 1) % len(self.algorithms)
                    self.algo = self.algorithms[self.algo_index]
                    self._reset()

    def update(self, dt, mouse_pos):
        self.title_t = min(1.0, self.title_t + dt * 3)
        
        # Update nút (nếu không đang giải)
        for btn in self.buttons:
            btn.update(dt, mouse_pos)
            
        # Kiểm tra xem luồng chạy ngầm đã xong chưa
        if self.is_solving and self.thread_result is not None:
            res = self.thread_result["result"]
            self.solve_time = self.thread_result["elapsed"]
            self.nodes_expanded = self.thread_result["nodes"]
            
            if res is None:
                self.status_msg = "No solution found"
                self.status_color = th.ERROR
            else:
                self.state = res
                self.is_solved = True
                self.status_msg = f"Solved in {self.solve_time * 1000:.1f} ms"
                self.status_color = th.SUCCESS
                self._save_output()
                # Kích hoạt hiệu ứng số hiện lên
                for r in range(self.N):
                    for c in range(self.N):
                        if self.original_state.grid[r][c] == 0 and self.state.grid[r][c] != 0:
                            self.cell_anim[(r, c)] = 0.0
            
            self.is_solving = False # Kết thúc trạng thái đang giải
            self.thread_result = None

        # Hiệu ứng animation
        for k in list(self.cell_anim.keys()):
            self.cell_anim[k] = min(1.0, self.cell_anim[k] + dt * 5)

    # ----- Draw -----

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
            # Làm mờ nút Solve/Reset/Menu khi đang tính toán
            if self.is_solving and btn != self.back_btn:
                btn.draw(surface) # Bạn có thể chỉnh sửa class Button để hỗ trợ disable/fade nếu muốn
            else:
                btn.draw(surface)

    def _draw_header(self, surface):
        from .level_screen import DIFFICULTY_INFO
        info = DIFFICULTY_INFO[self.difficulty]
        title_appear = th.ease_out_cubic(self.title_t)
        alpha = int(255 * title_appear)
        offset = int((1 - title_appear) * 10)

        pill_text = f"{self.size_name} · {info['name'].upper()}"
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
                        anim_t = self.cell_anim[(r, c)]
                        if anim_t < 1.0:
                            scale = 0.4 + 0.6 * th.ease_out_back(anim_t)
                    font_size = max(12, int(cs * 0.55 * scale))
                    val_font = th.get_font(font_size, bold=True)
                    val_surf = val_font.render(str(val), True, text_col)
                    val_rect = val_surf.get_rect(center=rect.center)
                    surface.blit(val_surf, val_rect)

        # Draw constraints... (phần vẽ dấu < > ^ v giữ nguyên)
        sign_font = th.get_font(max(12, int(cs * 0.32)), bold=True)
        for r in range(N):
            for c in range(N - 1):
                h = self.state.h_constraints[r][c]
                if h == 0: continue
                ch = "<" if h == 1 else ">"
                cx = self.board_x + c * (cs + ss) + cs + ss // 2
                cy = self.board_y + r * (cs + ss) + cs // 2
                ssurf = sign_font.render(ch, True, th.SIGN_COLOR)
                surface.blit(ssurf, ssurf.get_rect(center=(cx, cy)))
        for r in range(N - 1):
            for c in range(N):
                v = self.state.v_constraints[r][c]
                if v == 0: continue
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
        sec = font_section.render("ALGORITHM", True, th.TEXT_TERTIARY)
        surface.blit(sec, (rect.x + 22, y))
        y += 20

        algo_rect = pygame.Rect(rect.x + 20, y, rect.w - 40, 46)
        pygame.draw.rect(surface, th.BG_TERTIARY, algo_rect, border_radius=10)
        pygame.draw.rect(surface, th.BORDER, algo_rect, width=1, border_radius=10)
        algo_font = th.get_font(15, bold=True)
        algo_surf = algo_font.render(self.algo, True, th.TEXT_PRIMARY)
        surface.blit(algo_surf, (algo_rect.x + 16, algo_rect.centery - algo_surf.get_height() // 2))

        # Badge hiển thị trạng thái giải
        badge_text = "SOLVING..." if self.is_solving else ("ACTIVE" if not self.is_solved else "DONE")
        badge_color = th.ACCENT if self.is_solving else (th.SUCCESS if self.is_solved else th.ACCENT)
        badge_font = th.get_font(10, bold=True)
        badge_surf = badge_font.render(badge_text, True, badge_color)
        bw, bh = badge_surf.get_width() + 14, 20
        badge_rect = pygame.Rect(0, 0, bw, bh)
        badge_rect.right, badge_rect.centery = algo_rect.right - 12, algo_rect.centery
        badge_layer = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(badge_layer, (*badge_color, 32), badge_layer.get_rect(), border_radius=10)
        surface.blit(badge_layer, badge_rect)
        surface.blit(badge_surf, (badge_rect.x + 7, badge_rect.centery - badge_surf.get_height() // 2))

        y = algo_rect.bottom + 22
        sec = font_section.render("STATISTICS", True, th.TEXT_TERTIARY)
        surface.blit(sec, (rect.x + 22, y))
        y += 20

        stat_w, stat_h = (rect.w - 40 - 10) // 2, 64
        def draw_stat(x, y, label, value, color=None):
            srect = pygame.Rect(x, y, stat_w, stat_h)
            pygame.draw.rect(surface, th.BG_TERTIARY, srect, border_radius=10)
            lab_surf = font_label.render(label, True, th.TEXT_TERTIARY)
            surface.blit(lab_surf, (srect.x + 14, srect.y + 12))
            val_font = th.get_font(20, bold=True)
            val_surf = val_font.render(value, True, color or th.TEXT_PRIMARY)
            surface.blit(val_surf, (srect.x + 14, srect.y + 28))

        cells_filled = sum(1 for r in range(self.N) for c in range(self.N) if self.state.grid[r][c] != 0)
        time_text = f"{self.solve_time * 1000:.1f}ms" if self.solve_time > 0 else "—"
        draw_stat(rect.x + 20, y, "TIME", time_text, th.SUCCESS if self.is_solved else None)
        draw_stat(rect.x + 20 + stat_w + 10, y, "EXPANDED", str(self.nodes_expanded) if self.nodes_expanded > 0 else "—")
        y += stat_h + 10
        draw_stat(rect.x + 20, y, "FILLED", f"{cells_filled}/{self.N*self.N}")
        
        y += stat_h + 20
        if self.is_solved:
            label_surf = font_section.render("AUTO SAVED", True, th.TEXT_TERTIARY)
            surface.blit(label_surf, (rect.x + 22, y))
            y += 18
            basename = os.path.basename(self.input_path)
            num = basename.replace("input-", "").replace(".txt", "")
            path_surf = th.get_mono(11).render(f"outputs/output-{num}.txt", True, th.SUCCESS)
            surface.blit(path_surf, (rect.x + 22, y))
        elif self.status_msg:
            status_surf = th.get_font(13).render(self.status_msg, True, self.status_color)
            surface.blit(status_surf, (rect.x + 22, y))