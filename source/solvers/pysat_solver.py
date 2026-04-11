import time
from typing import Optional, List
from pysat.solvers import Glucose3
from core.knowledge_base import KnowledgeBase
from core.state import State


class PySATSolver:
    def __init__(self, initial_state: State):
        self.initial_state = initial_state
        self.elapsed = 0.0

    def solve(self) -> Optional[State]:
        state = self.initial_state.clone()

        # Generate CNF
        kb = KnowledgeBase(state.N)
        clauses: List[List[int]] = kb.generate_all_clauses(state)
        self.nodes_expanded = len(clauses)

        # SAT Solver
        solver = Glucose3()
        for clause in clauses:
            solver.add_clause(clause)

        start = time.perf_counter()
        is_solvable: bool = solver.solve()
        self.elapsed = time.perf_counter() - start

        if is_solvable:
            model: List[int] = solver.get_model()
            for ID in model:
                if ID > 0:
                    r, c, v = kb.decode_var(ID)
                    state.grid[r][c] = v
            solver.delete()
            return state

        solver.delete()
        return None