from core.state import State
from typing import Optional, List, Tuple, Callable

class BackwardChainingSolver:
    def __init__(self, state: 'State') -> None:
        self.initial_state: 'State' = state
        self.nodes_expanded: int = 0

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        return self._sld_resolve(self.initial_state)
    
    def _sld_resolve(self, current_state: 'State') -> Optional[State]:
        self.nodes_expanded += 1

        # Base case
        if current_state.is_complete():
            return current_state
        
        # Choose an empty cell to make query
        empty_cells: List[Tuple[int, int]] = current_state.get_empty_cells()
        r, c = empty_cells[0] # First empty cell

        # Try assigning value to cell (r, c)
        for v in current_state.domains[r][c]:
            # Make query 
            if self._is_proved(current_state, r, c, v):
                new_state = current_state.assign_value(r, c, v)

                # Recursion
                result = self._sld_resolve(new_state)
                
                if result is not None:
                    return result
                
        return None
    
    def _is_proved(self, state: 'State', r: int, c: int, v: int) -> bool:
        """Val(r, c, v) :- ValidRow, ValidCol, ValidH, ValidV"""
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
        
