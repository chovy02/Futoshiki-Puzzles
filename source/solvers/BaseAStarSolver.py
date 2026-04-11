# solvers/baseastarsolver.py

import heapq
import math
from typing import Optional, List, Tuple
from core.state import State

class BaseAStarSolver:
    def __init__(self, initial_state: 'State') -> None:
        self.initial_state: 'State' = initial_state
        self.nodes_expanded: int = 0

    def calculate_heuristic(self, state: 'State') -> float:
        """Abstract method"""
        raise NotImplementedError("Child class must define this method")
    
    def _get_next_cell(self, state: 'State') -> Optional[Tuple[int, int]]:
        """Use Forward Checking and MRV to select the next cell to generate successors"""
        best_cell = None
        min_value = float('inf')

        for r in range(state.N):
            for c in range(state.N):
                if state.grid[r][c] == 0:
                    # Forward Checking
                    valid_values = []
                    for v in state.domains[r][c]:
                        if state.is_valid_assignment(r, c, v):
                            valid_values.append(v)

                    state.domains[r][c] = valid_values
                    valid_count = len(valid_values)

                    # MRV
                    if valid_count < min_value:
                        min_value = valid_count
                        best_cell = (r, c)

                    if min_value == 0:
                        return best_cell
        return best_cell            

                        

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0

        # Priority queue (Min-heap), store (f(n), tie_breaker, g(n), state)
        pq = []
        tie_breaker = 0 # Used when f(n) is equal

        # Initialize root
        h_initial = self.calculate_heuristic(self.initial_state)
        heapq.heappush(pq, (h_initial, tie_breaker, 0, self.initial_state))

        while pq:
            f, _, g, current_state = heapq.heappop(pq)
            self.nodes_expanded += 1

            # Base case
            if current_state.is_complete():
                return current_state
            
            # Apply MRV to get next cell
            next_cell = self._get_next_cell(current_state)
            if next_cell is None:
                continue

            r, c = next_cell

            for v in current_state.domains[r][c]:
                if current_state.is_valid_assignment(r, c, v):
                    new_state = current_state.assign_value(r, c, v)
                    g_new = g + 1
                    h_new = self.calculate_heuristic(new_state)
                    
                    if h_new != math.inf:
                        f_new = g_new + h_new
                        tie_breaker += 1
                        heapq.heappush(pq, (f_new, tie_breaker, g_new, new_state))

        return None