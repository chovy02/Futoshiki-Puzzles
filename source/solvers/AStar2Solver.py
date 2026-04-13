# solvers/astar2solver.py

from solvers.BaseAStarSolver import BaseAStarSolver
from core.state import State

class AStar2Solver(BaseAStarSolver):
    """Number of empty cells related to inequality constraints"""
    def calculate_heuristic(self, state: 'State') -> float:
        count = 0
        penalty = 1
        N = state.N
        
        for r in range(N):
            for c in range(N):
                if state.grid[r][c] == 0:
                    count += 1
                    if c > 0 and state.h_constraints[r][c - 1] != 0: 
                        count += penalty
                    elif c < N - 1 and state.h_constraints[r][c] != 0: 
                        count += penalty
                    elif r > 0 and state.v_constraints[r - 1][c] != 0: 
                        count += penalty
                    elif r < N - 1 and state.v_constraints[r][c] != 0: 
                        count += penalty
                        
        return float(count)
    
