import time
from typing import Optional
from core.state import State
from core.fol_logic import Predicate
from solvers.futoshiki_kb import build_futoshiki_kb, assert_initial_clues


class ForwardChainingSolver:
    def __init__(self, initial_state: 'State', stop_event=None) -> None:
        self.initial_state: 'State' = initial_state
        self.stop_event = stop_event
        self.nodes_expanded: int = 0
        self.num_inferences: int = 0
        self.num_initial_clauses: int = 0
        self.total_number_of_clauses: int = 0
        self.elapsed: float = 0.0
        self.kb = build_futoshiki_kb(initial_state)

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        self.num_inferences = 0
        start = time.perf_counter()

        assert_initial_clues(self.kb, self.initial_state)

        # Đo lường số lượng initial clauses
        self.num_initial_clauses = self.kb.count_clauses()
        self.kb.inference_count = 0  # Reset bộ đếm

        result = self._sld_resolve(self.initial_state)

        self.total_number_of_clauses = self.kb.count_clauses()
        self.num_inferences = self.kb.inference_count
        self.elapsed = time.perf_counter() - start
        return result

    def _sld_resolve(self, current_state: 'State') -> Optional[State]:
        if self.stop_event and self.stop_event.is_set():
            return None

        self.nodes_expanded += 1
        if current_state.is_complete():
            return current_state

        empty_cells = current_state.get_empty_cells()
        if not empty_cells:
            return None

        r, c = empty_cells[0]
        domain = current_state.get_pruned_domain(r, c)
        if not domain:
            return None

        for v in domain:
            # FORWARD CHAINING: derive ground facts, check Conflict(r,c,v) emerges?
            query = Predicate("Conflict", [r, c, v])
            has_conflict = self.kb.fol_fc_ask(query)

            if not has_conflict:
                self.kb.add_fact(Predicate("Val", [r, c, v]))
                new_state = current_state.assign_value(r, c, v)

                # Forward Checking: prune domain sau khi gán
                if self._forward_check(new_state):
                    result = self._sld_resolve(new_state)
                    if result is not None:
                        return result

                self.kb.retract_fact("Val")

        return None
    
    def _forward_check(self, state: 'State') -> bool:
        """Prune domain tất cả ô trống. Trả False nếu có ô nào domain rỗng."""
        for r in range(state.N):
            for c in range(state.N):
                if state.grid[r][c] == 0:
                    new_domain = state.get_pruned_domain(r, c)
                    if not new_domain:
                        return False
                    state.domains[r][c] = new_domain
        return True