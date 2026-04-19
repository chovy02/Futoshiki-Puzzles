import time
from core.state import State
from typing import Optional, List, Tuple, Callable


class ForwardChainingSolver:
    def __init__(self, state: 'State', stop_event=None) -> None:
        self.initial_state: 'State' = state
        self.nodes_expanded: int = 0
        self.num_inferences: int = 0
        self.elapsed: float = 0.0
        self.stop_event = stop_event

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        self.num_inferences = 0
        start = time.perf_counter()

        init_state = self.initial_state.clone()
        ok, _ = self._propagate(init_state)
        if not ok:
            self.elapsed = time.perf_counter() - start
            return None

        result = self._sld_resolve(init_state)
        self.elapsed = time.perf_counter() - start
        return result

    def _sld_resolve(self, current_state: 'State') -> Optional[State]:
        if self.stop_event and self.stop_event.is_set():
            return None
        self.nodes_expanded += 1

        # [LOG 1]: In tiến độ mỗi 1000 nodes để biết code vẫn đang chạy, không bị treo cứng.
        if self.nodes_expanded % 1000 == 0:
            empty_count = len(current_state.get_empty_cells())
            print(f"[SLD_Resolve] Đang tìm kiếm... Đã mở rộng: {self.nodes_expanded} nodes | Số ô trống hiện tại: {empty_count}")

        if current_state.is_complete():
            return current_state
        
        empty_cells: List[Tuple[int, int]] = current_state.get_empty_cells()
        r, c = empty_cells[0]
        for v in current_state.domains[r][c]:
            if self._is_proved(current_state, r, c, v):
                self.num_inferences += 1
                new_state = current_state.assign_value(r, c, v)

                ok, _ = self._propagate(new_state)
                if not ok:
                    continue

                result = self._sld_resolve(new_state)
                if result is not None:
                    return result
        return None

    def _is_proved(self, state: 'State', r: int, c: int, v: int) -> bool:
        sub_goals: List[Callable[[], bool]] = [
            lambda: state.is_valid_row(r, v),
            lambda: state.is_valid_col(c, v),
            lambda: state.is_valid_h_constraints(r, c, v),
            lambda: state.is_valid_v_constraints(r, c, v)
        ]
        for goal in sub_goals:
            if not goal():
                return False
        return True

    def _propagate(self, state: 'State') -> Tuple[bool, List[Tuple[int, int, int]]]:
        """Forward chaining: prune + unit-propagate until fixed point."""
        derived: List[Tuple[int, int, int]] = []
        changed = True
        pass_count = 0  # Thêm biến đếm số vòng lặp
        while changed:
            pass_count += 1
            # [LOG 2]: Nếu lặp quá 50 lần cho 1 state thì chắc chắn có vấn đề logic ở get_pruned_domain
            if pass_count > 50:
                print(f"[CẢNH BÁO] Propagate bị lặp {pass_count} vòng! Buộc dừng để chống treo máy.")
            changed = False
            for r in range(state.N):
                for c in range(state.N):
                    if state.grid[r][c] != 0:
                        continue
                    new_domain = state.get_pruned_domain(r, c)
                    if not new_domain:
                        return False, derived
                    if len(new_domain) < len(state.domains[r][c]):
                        state.domains[r][c] = new_domain
                        changed = True
                    if len(new_domain) == 1:
                        state.grid[r][c] = new_domain[0]
                        derived.append((r, c, new_domain[0]))
                        changed = True
        return True, derived