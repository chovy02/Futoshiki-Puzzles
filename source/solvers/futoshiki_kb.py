"""
Shared KB builder cho Futoshiki - dùng chung bởi BC2 và FC2.

Định nghĩa các facts/rules FOL mô tả luật Futoshiki:
    - Cell(r, c)                : mọi ô trên bảng (dùng range-restrict cho FC)
    - Less(v1, v2)              : v1 < v2
    - Constraint(r1,c1,r2,c2)   : ô (r1,c1) phải < ô (r2,c2) theo bất đẳng thức
    - Val(r, c, v)              : ô (r,c) đang có giá trị v   (assert/retract khi search)
    - Conflict(r, c, v)         : đặt v vào (r,c) sẽ vi phạm luật

KB này range-restricted (mọi biến ở head đều xuất hiện ở body) nên hoạt
động được với CẢ Backward Chaining lẫn Forward Chaining.
"""

from core.fol_logic import FOLKnowledgeBase, Predicate, Rule
from core.state import State


def build_futoshiki_kb(initial_state: 'State') -> FOLKnowledgeBase:
    kb = FOLKnowledgeBase()
    N = initial_state.N

    # ----- FACTS -----

    # Cell(r,c) — range-restriction cho FC
    for r in range(N):
        for c in range(N):
            kb.add_fact(Predicate("Cell", [r, c]))

    # Less(v1, v2)
    for v1 in range(1, N + 1):
        for v2 in range(1, N + 1):
            if v1 < v2:
                kb.add_fact(Predicate("Less", [v1, v2]))

    # Constraint(r1,c1,r2,c2): cell (r1,c1) < cell (r2,c2)
    for r in range(N):
        for c in range(N - 1):
            val = initial_state.h_constraints[r][c]
            if val == 1:
                kb.add_fact(Predicate("Constraint", [r, c, r, c + 1]))
            elif val == -1:
                kb.add_fact(Predicate("Constraint", [r, c + 1, r, c]))

    for r in range(N - 1):
        for c in range(N):
            val = initial_state.v_constraints[r][c]
            if val == 1:
                kb.add_fact(Predicate("Constraint", [r, c, r + 1, c]))
            elif val == -1:
                kb.add_fact(Predicate("Constraint", [r + 1, c, r, c]))

    # ----- RULES (Conflict) -----

    # Row conflict
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Cell", ["r", "c"]),
            Predicate("Val", ["r", "c_other", "v"]),
        ]
    ))

    # Column conflict
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Cell", ["r", "c"]),
            Predicate("Val", ["r_other", "c", "v"]),
        ]
    ))

    # Bất đẳng thức - phía nhỏ hơn (ta < neighbor v2): vi phạm khi v >= v2
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Constraint", ["r", "c", "r2", "c2"]),
            Predicate("Val", ["r2", "c2", "v2"]),
            Predicate("Less", ["v2", "v"]),
        ]
    ))
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Constraint", ["r", "c", "r2", "c2"]),
            Predicate("Val", ["r2", "c2", "v"]),
        ]
    ))

    # Bất đẳng thức - phía lớn hơn (neighbor v1 < ta): vi phạm khi v <= v1
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Constraint", ["r1", "c1", "r", "c"]),
            Predicate("Val", ["r1", "c1", "v1"]),
            Predicate("Less", ["v", "v1"]),
        ]
    ))
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Constraint", ["r1", "c1", "r", "c"]),
            Predicate("Val", ["r1", "c1", "v"]),
        ]
    ))

    return kb


def assert_initial_clues(kb: FOLKnowledgeBase, initial_state: 'State') -> None:
    """Nạp các giá trị clue ban đầu thành Val facts."""
    for r in range(initial_state.N):
        for c in range(initial_state.N):
            v = initial_state.grid[r][c]
            if v != 0:
                kb.add_fact(Predicate("Val", [r, c, v]))