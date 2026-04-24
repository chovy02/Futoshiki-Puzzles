import time
from typing import Optional
from core.state import State
from core.fol_logic import Predicate
from solvers.futoshiki_kb import build_futoshiki_kb, assert_initial_clues


class BackwardChainingSolver:
    def __init__(self, initial_state: 'State', stop_event=None) -> None:
        self.initial_state: 'State' = initial_state
        self.stop_event = stop_event
        self.nodes_expanded: int = 0
        self.num_inferences: int = 0
        self.num_initial_clauses: int = 0
        self.total_number_of_clauses: int = 0
        self.elapsed: float = 0.0
        self.kb = build_futoshiki_kb(initial_state)

<<<<<<< HEAD
        # KB log — GUI reads this list to display
        self.kb_log_lines: List[str] = []

    def _log(self, line: str) -> None:
        self.kb_log_lines.append(line)

=======
>>>>>>> parent of 0af4fe7 (log bc)
    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        self.num_inferences = 0
        start = time.perf_counter()

        assert_initial_clues(self.kb, self.initial_state)
        self.num_initial_clauses = self.kb.count_clauses()
        self.kb.inference_count = 0

<<<<<<< HEAD
        # Log KB ban đầu 1 lần
        self._log("=== INITIAL KB ===")
        for name, fact_list in sorted(self.kb.facts.items()):
            if fact_list:
                self._log(f"[{name}] ({len(fact_list)})")
                for f in fact_list:
                    self._log(f"  {f}")
        self._log("")

=======
        # Chạy thuật toán Duyệt SLD
>>>>>>> parent of 0af4fe7 (log bc)
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
<<<<<<< HEAD

=======
        # Chọn biến (Lấy ô trống đầu tiên)
>>>>>>> parent of 0af4fe7 (log bc)
        empty_cells = current_state.get_empty_cells()
        if not empty_cells:
            return None

        r, c = empty_cells[0]
        new_domain = current_state.get_pruned_domain(r, c)
        if not new_domain:
            return None
<<<<<<< HEAD

=======
        # Duyệt qua các giá trị khả dĩ
>>>>>>> parent of 0af4fe7 (log bc)
        for v in new_domain:
            query = Predicate("Conflict", [r, c, v])
            has_conflict = False
            for _ in self.kb.fol_bc_ask(query):
                has_conflict = True
<<<<<<< HEAD
                break

            if has_conflict:
                self._log(f"! CONFLICT Val({r},{c},{v}) — skipped")
                continue

            fact = Predicate("Val", [r, c, v])
            self.kb.add_fact(fact)
            new_state = current_state.assign_value(r, c, v)

            # Log fact mới được thêm
            self._log(f"+ ASSERT  {fact}")

            if self._forward_check(new_state):
                result = self._sld_resolve(new_state)
                if result is not None:
                    return result

            # Log backtrack
            self._log(f"- RETRACT {fact}")
            self.kb.retract_fact("Val")

        return None
=======
                break  # Phát hiện 1 mâu thuẫn là đủ để chặt nhánh này
            # Nếu KHÔNG CÓ mâu thuẫn nào -> Điền số an toàn!
            if not has_conflict:
                self.kb.add_fact(Predicate("Val", [r, c, v]))
                new_state = current_state.assign_value(r, c, v)

                if self._forward_check(new_state):
                    result = self._sld_resolve(new_state)
                    if result is not None:
                        return result
                # 3. Rút lui (Retract) - Tháo sự thật ra khỏi KB để quay lui (Backtracking)
                self.kb.retract_fact("Val")
>>>>>>> parent of 0af4fe7 (log bc)

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