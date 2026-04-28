import time
from core.state import State
from typing import Optional, List, Tuple

class BruteForceBacktrackingSolver:
    def __init__(self, state: 'State', stop_event=None) -> None:
        self.initial_state: 'State' = state
        self.nodes_expanded: int = 0
        self.elapsed: float = 0.0
        self.stop_event = stop_event
    
        self.history = []
        self.MAX_HISTORY = 500000000000  
    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        start = time.perf_counter()

        init_state = self.initial_state.clone()
        self.history.append([row[:] for row in init_state.grid])

        result = self._backtrack(init_state)
        
        self.elapsed = time.perf_counter() - start
        return result

    def _backtrack(self, current_state: 'State') -> Optional[State]:
        self.nodes_expanded += 1
        if self.stop_event and self.stop_event.is_set():
            return None

        if current_state.is_complete():
            if len(self.history) < self.MAX_HISTORY:
                self.history.append([row[:] for row in current_state.grid])
            return current_state

        coords = self._select_unassigned_variable(current_state)
        if coords is None:
            return None
        r, c = coords
        
        for v in current_state.domains[r][c]:
            if current_state.is_valid_assignment(r, c, v):
                new_state = current_state.assign_value(r, c, v)
                
                if len(self.history) < self.MAX_HISTORY:
                    self.history.append([row[:] for row in new_state.grid])
                    
                result = self._backtrack(new_state)
                if result is not None:
                    return result
                
                if len(self.history) < self.MAX_HISTORY:
                    self.history.append([row[:] for row in current_state.grid])
                    
        return None

    def _select_unassigned_variable(self, state: 'State') -> Tuple[int, int]:
        empty_cells = state.get_empty_cells()
        return empty_cells[0] if empty_cells else None