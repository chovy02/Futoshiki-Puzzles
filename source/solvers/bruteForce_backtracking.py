import time
from core.state import State
from typing import Optional, List, Tuple

class BruteForceBacktrackingSolver:
    def __init__(self, state: 'State', stop_event=None) -> None:
        self.initial_state: 'State' = state
        self.nodes_expanded: int = 0
        self.elapsed: float = 0.0
        self.stop_event = stop_event
        
        # --- CODE MỚI: Thêm mảng lịch sử ---
        self.history = []
        self.MAX_HISTORY = 500000000000  # Giới hạn để tránh tràn RAM với lưới quá lớn

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        start = time.perf_counter()

        init_state = self.initial_state.clone()
        
        # Ghi lại trạng thái ban đầu
        self.history.append([row[:] for row in init_state.grid])

        result = self._backtrack(init_state)
        
        self.elapsed = time.perf_counter() - start
        return result

    def _backtrack(self, current_state: 'State') -> Optional[State]:
        # Tăng nodes_expanded ngay khi bắt đầu xử lý một trạng thái (Visit-based)
        self.nodes_expanded += 1

        # Kiểm tra sự kiện dừng từ GUI (nếu có)
        if self.stop_event and self.stop_event.is_set():
            return None
            
        # Kiểm tra nếu trạng thái hiện tại đã hoàn thành lưới
        if current_state.is_complete():
            # Ghi lại trạng thái hoàn thành vào lịch sử
            if len(self.history) < self.MAX_HISTORY:
                self.history.append([row[:] for row in current_state.grid])
            return current_state
            
        # Chọn biến (ô trống) tiếp theo để gán giá trị
        coords = self._select_unassigned_variable(current_state)
        if coords is None:
            return None
        r, c = coords
        
        # Thử từng giá trị trong miền giá trị của ô đó
        for v in current_state.domains[r][c]:
            if current_state.is_valid_assignment(r, c, v):
                # Tạo trạng thái mới sau khi gán giá trị v vào ô (r, c)
                new_state = current_state.assign_value(r, c, v)
                
                # Ghi lại lịch sử phục vụ việc minh họa quá trình giải
                if len(self.history) < self.MAX_HISTORY:
                    self.history.append([row[:] for row in new_state.grid])
                    
                # Gọi đệ quy để tiếp tục giải các ô còn lại
                result = self._backtrack(new_state)
                if result is not None:
                    return result
                
                # Quay lui (Backtrack): Ghi lại lịch sử khi nhánh này không dẫn đến lời giải
                if len(self.history) < self.MAX_HISTORY:
                    self.history.append([row[:] for row in current_state.grid])
                    
        return None

    def _select_unassigned_variable(self, state: 'State') -> Tuple[int, int]:
        empty_cells = state.get_empty_cells()
        return empty_cells[0] if empty_cells else None