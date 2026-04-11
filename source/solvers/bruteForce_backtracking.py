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
        self.MAX_HISTORY = 20000  # Giới hạn để tránh tràn RAM với lưới quá lớn

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        start = time.perf_counter()

        init_state = self.initial_state.clone()
        
        # Ghi lại trạng thái ban đầu
        self.history.append([row[:] for row in init_state.grid])

        ok, _ = init_state.propagate()
        if not ok:
            self.elapsed = time.perf_counter() - start
            return None

        result = self._backtrack(init_state)
        
        self.elapsed = time.perf_counter() - start
        return result

    def _backtrack(self, current_state: 'State') -> Optional[State]:
        if self.stop_event and self.stop_event.is_set():
            return None
            
        if current_state.is_complete():
            # Ghi lại trạng thái hoàn thành
            if len(self.history) < self.MAX_HISTORY:
                self.history.append([row[:] for row in current_state.grid])
            return current_state
            
        r, c = self._select_unassigned_variable(current_state)
        
        for v in current_state.domains[r][c]:
            if current_state.is_valid_assignment(r, c, v):
                self.nodes_expanded += 1
                
                new_state = current_state.assign_value(r, c, v)
                
                # --- CODE MỚI: Ghi lại lịch sử sau khi gán giá trị ---
                if len(self.history) < self.MAX_HISTORY:
                    self.history.append([row[:] for row in new_state.grid])
                
                ok, _ = new_state.propagate()
                if not ok:
                    # Nếu miền bị rỗng -> Cắt tỉa. Ghi lại lưới cũ để thể hiện bước lùi.
                    if len(self.history) < self.MAX_HISTORY:
                        self.history.append([row[:] for row in current_state.grid])
                    continue
                    
                result = self._backtrack(new_state)
                if result is not None:
                    return result
                
                # --- CODE MỚI: Ghi lại lịch sử quay lui (khi nhánh cụt) ---
                if len(self.history) < self.MAX_HISTORY:
                    self.history.append([row[:] for row in current_state.grid])
                    
        return None

    def _select_unassigned_variable(self, state: 'State') -> Tuple[int, int]:
        empty_cells = state.get_empty_cells()
        
        def mrv_degree_key(cell: Tuple[int, int]):
            r, c = cell
            domain_size = len(state.domains[r][c])
            degree = 0
            if c > 0 and state.h_constraints[r][c - 1] != 0: degree += 1
            if c < state.N - 1 and state.h_constraints[r][c] != 0: degree += 1
            if r > 0 and state.v_constraints[r - 1][c] != 0: degree += 1
            if r < state.N - 1 and state.v_constraints[r][c] != 0: degree += 1
            
            return (domain_size, -degree)

        return min(empty_cells, key=mrv_degree_key)