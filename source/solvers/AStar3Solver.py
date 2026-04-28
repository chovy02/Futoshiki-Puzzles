# solvers/AStar3Solver.py

import math
from solvers.BaseAStarSolver import BaseAStarSolver
from core.state import State
from typing import List, Tuple, Optional
from collections import deque

class AStar3Solver(BaseAStarSolver):
    def _get_neighbors(self, N: int, r: int, c: int) -> List[Tuple[int, int]]:
        """Get all cells on the same row and column"""
        neighbors = []
        for i in range(N):
            if i != c: 
                neighbors.append((r, i))
            if i !=r:
                neighbors.append((i, c))
        return neighbors
    
    def _satisfy_constraints(self, state: 'State', r1: int, c1: int, v1: int, r2: int, c2: int, v2: int) -> bool:
        """Check whether value v1, v2 can satisfy constraints between two cells (r1, c1) and (r2, c2)"""
        if v1 == v2:
            return False

        if r1 == r2:
            if c1 == c2 - 1: 
                rule = state.h_constraints[r1][c1]
                if rule == 1 and not (v1 < v2): return False
                if rule == -1 and not (v1 > v2): return False
            elif c1 == c2 + 1: 
                rule = state.h_constraints[r2][c2]
                if rule == 1 and not (v1 > v2): return False
                if rule == -1 and not (v1 < v2): return False

        elif c1 == c2:
            if r1 == r2 - 1:
                rule = state.v_constraints[r1][c1]
                if rule == 1 and not (v1 < v2): return False
                if rule == -1 and not (v1 > v2): return False
            elif r1 == r2 + 1:
                rule = state.v_constraints[r2][c2]
                if rule == 1 and not (v1 > v2): return False
                if rule == -1 and not (v1 < v2): return False

        return True
    
    def revise(self, state: 'State', r1: int, c1: int, r2: int, c2: int) -> bool:
        """Delete unsatisfied values from the domains"""
        revised = False
        new_domain = []

        # With each x of D[r1][c1]
        for v1 in state.domains[r1][c1]:
            has_support = False
            # Check whether each y of D[r2][c2] satisfies
            for v2 in state.domains[r2][c2]:
                if self._satisfy_constraints(state, r1, c1, v1, r2, c2, v2):
                    has_support = True
                    break  
            
            if has_support:
                new_domain.append(v1)
            else:
                revised = True  # No y satisfies -> Delete x from D[r1][c1]

        if revised:
            state.domains[r1][c1] = new_domain

        return revised
    
    def ac3(self, state: 'State') -> bool:
        """AC-3: Return false if there is an empty domain"""
        queue = deque()

        # Initialize a queue of arcs
        N = state.N
        for r in range(N):
            for c in range(N):
                neighbors = self._get_neighbors(N, r, c)
                for nr, nc in neighbors:
                    queue.append(((r, c), (nr, nc)))

        # Propagation
        while queue:
            (r1, c1), (r2, c2) = queue.popleft()

            if self.revise(state, r1, c1, r2, c2):
                # If there is an empty domain, return false
                if len(state.domains[r1][c1]) == 0:
                    return False
                
                # Add arcs propagated from (r1, c1) into queue
                neighbors = self._get_neighbors(N, r1, c1)
                for nr, nc in neighbors:
                    if (nr, nc) != (r2, c2):
                        queue.append(((nr, nc), (r1, c1)))

        return True
    
    def calculate_heuristic(self, state: 'State') -> float:
        """Đánh giá trạng thái bằng cách chạy AC-3 làm cận dưới."""
        # Run AC-3
        is_consistent = self.ac3(state)
        
        # If there is an empty domain, prune the branch
        if not is_consistent:
            return math.inf
            
        # Otherwise, return the number of empty cells
        count = sum(1 for r in range(state.N) for c in range(state.N) if state.grid[r][c] == 0)
        return float(count)

    def _get_next_cell(self, state: 'State') -> Optional[Tuple[int, int]]:
        """
        Inherited from parent class, with a view to removing Forward Checking part
        """
        best_cell = None
        min_value = float('inf')

        for r in range(state.N):
            for c in range(state.N):
                if state.grid[r][c] == 0:
                    valid_count = len(state.domains[r][c])

                    if valid_count < min_value:
                        min_value = valid_count
                        best_cell = (r, c)

                    if min_value == 0:
                        return best_cell

        return best_cell
