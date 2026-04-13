import time
from collections import deque
from core.state import State
from typing import Optional, List, Tuple, Callable, Deque


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
        ok = self._propagate(init_state)
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

        if current_state.is_complete():
            return current_state
        empty_cells: List[Tuple[int, int]] = current_state.get_empty_cells()
        r, c = empty_cells[0]
        for v in current_state.domains[r][c]:
            if self._is_proved(current_state, r, c, v):
                self.num_inferences += 1
                new_state = current_state.assign_value(r, c, v)

                # Forward inference theo PL-FC-ENTAILS
                ok = self._propagate(new_state)
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
            lambda: state.is_valid_v_constraints(r, c, v),
        ]
        for goal in sub_goals:
            if not goal():
                return False
        return True   
    
    def _propagate(self, state: 'State') -> bool:
        """
        Mô phỏng PL-FC-ENTAILS trên Futoshiki.

        agenda  : queue các fact Val(r,c,v) đã biết chắc chắn → cần lan truyền
        count   : count[r][c] = |domains[r][c]| — số value còn khả thi
                  (mỗi lần loại 1 value = decrement count; count = 1 ⇒ fact mới)
        inferred: state.grid (grid[r][c] != 0 ⇔ đã inferred)

        Trả về False nếu phát hiện mâu thuẫn (domain rỗng), True nếu OK.
        """
        N = state.N

        # Khởi tạo agenda = mọi fact Val(r,c,v) đã biết trong state
        agenda: Deque[Tuple[int, int, int]] = deque()
        for r in range(N):
            for c in range(N):
                if state.grid[r][c] != 0:
                    agenda.append((r, c, state.grid[r][c]))

        while agenda:
            r, c, v = agenda.popleft()

            # Lan truyền fact Val(r,c,v) tới các ô bị ảnh hưởng
            affected = self._get_affected_cells(state, r, c)

            for ar, ac in affected:
                if state.grid[ar][ac] != 0:
                    continue  # đã inferred, bỏ qua

                old_domain = state.domains[ar][ac]
                new_domain = state.get_pruned_domain(ar, ac)

                # Mâu thuẫn: domain rỗng
                if not new_domain:
                    return False

                # count giảm ⇔ có giá trị bị loại
                if len(new_domain) < len(old_domain):
                    state.domains[ar][ac] = new_domain

                    # count = 1 (chỉ còn 1 value) ⇒ fact mới được suy ra
                    if len(new_domain) == 1:
                        inferred_v = new_domain[0]
                        state.grid[ar][ac] = inferred_v
                        agenda.append((ar, ac, inferred_v))

        return True

    def _get_affected_cells(self, state: 'State', r: int, c: int) -> List[Tuple[int, int]]:
        N = state.N
        affected: List[Tuple[int, int]] = []

        for cc in range(N):
            if cc != c:
                affected.append((r, cc))
        for rr in range(N):
            if rr != r:
                affected.append((rr, c))

        return affected