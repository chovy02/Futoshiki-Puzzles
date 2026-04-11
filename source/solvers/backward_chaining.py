import time
from core.state import State
from typing import Optional, List, Tuple, Callable


class BackwardChainingSolver:
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
        result = self._sld_resolve(self.initial_state)
        self.elapsed = time.perf_counter() - start
        return result

    def _sld_resolve(self, current_state: 'State') -> Optional[State]:
        if self.stop_event and self.stop_event.is_set():
            return None
        self.nodes_expanded += 1
        if current_state.is_complete():
            return current_state
        # Choose an empty cell to make query
        empty_cells: List[Tuple[int, int]] = current_state.get_empty_cells()
        # Try assigning value to cell (r, c)
        r, c = empty_cells[0]
        for v in current_state.domains[r][c]:
            if self._is_proved(current_state, r, c, v):
                self.num_inferences += 1
                new_state = current_state.assign_value(r, c, v)
                # Recursion
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