# solvers/astar1solver.py

from solvers.BaseAStarSolver import BaseAStarSolver
from core.state import State

class AStar1Solver(BaseAStarSolver):
    """Calculate number of empty cells"""
    def calculate_heuristic(self, state: 'State') -> float:
        count = 0
        for r in range(state.N):
            for c in range(state.N):
                if state.grid[r][c] == 0:
                    count += 1

        return float(count)
    
