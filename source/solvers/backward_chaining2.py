import time
from typing import Optional
from core.state import State
from core.fol_logic import FOLKnowledgeBase, Predicate, Rule # Đảm bảo bạn đã lưu file fol_logic.py

class BackwardChainingSolver2:
    def __init__(self, initial_state: 'State', stop_event=None) -> None:
        self.initial_state: 'State' = initial_state
        self.stop_event = stop_event
        self.nodes_expanded: int = 0
        self.elapsed: float = 0.0
        
        # 1. Khởi tạo Động cơ Suy diễn Logic (FOL Engine)
        self.kb = FOLKnowledgeBase()
        self._setup_knowledge_base()

    def _setup_knowledge_base(self):
        """Dịch toàn bộ luật chơi Futoshiki thành FOL Horn Clauses."""
        N = self.initial_state.N

        # Hằng số: Định nghĩa quan hệ "Nhỏ hơn" (Less)
        for v1 in range(1, N + 1):
            for v2 in range(1, N + 1):
                if v1 < v2:
                    self.kb.add_fact(Predicate("Less", [v1, v2]))

        # Các luật bất đẳng thức trên bảng: Biến thành Fact Constraint(r1, c1, r2, c2)
        # Nghĩa là: Ô (r1, c1) phải nhỏ hơn Ô (r2, c2)
        for r in range(N):
            for c in range(N - 1):
                val = self.initial_state.h_constraints[r][c]
                if val == 1:   # Trái < Phải
                    self.kb.add_fact(Predicate("Constraint", [r, c, r, c + 1]))
                elif val == -1: # Trái > Phải -> Phải < Trái
                    self.kb.add_fact(Predicate("Constraint", [r, c + 1, r, c]))

        for r in range(N - 1):
            for c in range(N):
                val = self.initial_state.v_constraints[r][c]
                if val == 1:   # Trên < Dưới
                    self.kb.add_fact(Predicate("Constraint", [r, c, r + 1, c]))
                elif val == -1: # Trên > Dưới -> Dưới < Trên
                    self.kb.add_fact(Predicate("Constraint", [r + 1, c, r, c]))

        # ==========================================
        # ĐỊNH NGHĨA CÁC HORN CLAUSE CHO "CONFLICT"
        # ==========================================
        
        # Luật 1: Xung đột Hàng (Row) -> Có 1 ô (c_other) trên cùng hàng r đã điền số v.
        self.kb.add_rule(Rule(
            Predicate("Conflict", ["r", "c", "v"]),
            [Predicate("Val", ["r", "c_other", "v"])]
        ))

        # Luật 2: Xung đột Cột (Col) -> Có 1 ô (r_other) trên cùng cột c đã điền số v.
        self.kb.add_rule(Rule(
            Predicate("Conflict", ["r", "c", "v"]),
            [Predicate("Val", ["r_other", "c", "v"])]
        ))

        # Luật 3: Xung đột Bất đẳng thức (Khi ô đang xét nằm ở vế NHỎ HƠN)
        # Constraint(r,c < r2,c2) VÀ Val(r2,c2 = v2) VÀ Less(v2, v) (Tức là v > v2 -> Vi phạm!)
        self.kb.add_rule(Rule(
            Predicate("Conflict", ["r", "c", "v"]),
            [
                Predicate("Constraint", ["r", "c", "r2", "c2"]),
                Predicate("Val", ["r2", "c2", "v2"]),
                Predicate("Less", ["v2", "v"]) 
            ]
        ))
        
        # Luật 3b: Xung đột bằng nhau (v == v2)
        self.kb.add_rule(Rule(
            Predicate("Conflict", ["r", "c", "v"]),
            [
                Predicate("Constraint", ["r", "c", "r2", "c2"]),
                Predicate("Val", ["r2", "c2", "v"])
            ]
        ))

        # Luật 4: Xung đột Bất đẳng thức (Khi ô đang xét nằm ở vế LỚN HƠN)
        # Constraint(r1,c1 < r,c) VÀ Val(r1,c1 = v1) VÀ Less(v, v1) (Tức là v < v1 -> Vi phạm!)
        self.kb.add_rule(Rule(
            Predicate("Conflict", ["r", "c", "v"]),
            [
                Predicate("Constraint", ["r1", "c1", "r", "c"]),
                Predicate("Val", ["r1", "c1", "v1"]),
                Predicate("Less", ["v", "v1"])
            ]
        ))

        # Luật 4b: Xung đột bằng nhau (v == v1)
        self.kb.add_rule(Rule(
            Predicate("Conflict", ["r", "c", "v"]),
            [
                Predicate("Constraint", ["r1", "c1", "r", "c"]),
                Predicate("Val", ["r1", "c1", "v"])
            ]
        ))

    def solve(self) -> Optional[State]:
        self.nodes_expanded = 0
        start = time.perf_counter()

        # Nạp các Sự thật ban đầu (Clues) vào Knowledge Base
        for r in range(self.initial_state.N):
            for c in range(self.initial_state.N):
                v = self.initial_state.grid[r][c]
                if v != 0:
                    self.kb.add_fact(Predicate("Val", [r, c, v]))

        # Chạy thuật toán Duyệt SLD
        result = self._sld_resolve(self.initial_state)

        self.elapsed = time.perf_counter() - start
        return result

    def _sld_resolve(self, current_state: 'State') -> Optional[State]:
        if self.stop_event and self.stop_event.is_set():
            return None
            
        self.nodes_expanded += 1

        if current_state.is_complete():
            return current_state

        # Chọn biến (Lấy ô trống đầu tiên)
        empty_cells = current_state.get_empty_cells()
        if not empty_cells:
            return None
            
        r, c = empty_cells[0]

        new_domain = current_state.get_pruned_domain(r, c)

        if not new_domain:
            return None
        
        # Duyệt qua các giá trị khả dĩ
        for v in new_domain:
            
            # ĐÂY LÀ ĐỈNH CAO CỦA BACKWARD CHAINING!
            # Truy vấn Knowledge Base: "Liệu có bằng chứng nào cho thấy điền v vào (r,c) là Xung đột không?"
            query = Predicate("Conflict", [r, c, v])
            has_conflict = False
            
            # Hàm fol_bc_ask sẽ đệ quy cây SLD. Nếu yield ra kết quả, tức là bị mâu thuẫn (Conflict).
            for substitution in self.kb.fol_bc_ask(query):
                has_conflict = True
                break  # Phát hiện 1 mâu thuẫn là đủ để chặt nhánh này

            # Nếu KHÔNG CÓ mâu thuẫn nào -> Điền số an toàn!
            if not has_conflict:
                # 1. Thêm Sự thật mới vào KB (Assert)
                new_fact = Predicate("Val", [r, c, v])
                self.kb.add_fact(new_fact)

                # 2. Sinh trạng thái mới và đi tiếp
                new_state = current_state.assign_value(r, c, v)
                result = self._sld_resolve(new_state)

                if result is not None:
                    return result

                # 3. Rút lui (Retract) - Tháo sự thật ra khỏi KB để quay lui (Backtracking)
                self.kb.retract_fact("Val")

        return None