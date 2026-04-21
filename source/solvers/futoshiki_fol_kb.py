"""
futoshiki_fol_kb.py
───────────────────
FOL Knowledge Base cho Futoshiki, xây dựng theo đúng các axioms FOL
được đặc tả trong đề bài CSC14003 Project 2.

AXIOMS ĐÃ CHO:
  A1  (At-least-one)        : ∀i∀j ∃v Val(i,j,v)
  A2  (At-most-one)         : ∀i∀j ∀v1∀v2  Val(i,j,v1) ∧ Val(i,j,v2) ⇒ v1=v2
  A3  (Row-uniqueness)      : ∀i∀j1∀j2∀v  Val(i,j1,v) ∧ Val(i,j2,v) ∧ j1≠j2 ⇒ ⊥
  A4  (H-less-than)         : ∀i∀j∀v1∀v2  LessH(i,j) ∧ Val(i,j,v1) ∧ Val(i,j+1,v2) ⇒ Less(v1,v2)
  A5  (Given-clues)         : ∀i∀j∀v  Given(i,j,v) ⇒ Val(i,j,v)

AXIOMS TỰ SUY:
  A6  (Column-uniqueness)   : ∀j∀i1∀i2∀v  Val(i1,j,v) ∧ Val(i2,j,v) ∧ i1≠i2 ⇒ ⊥
  A7  (V-less-than)         : ∀i∀j∀v1∀v2  LessV(i,j) ∧ Val(i,j,v1) ∧ Val(i+1,j,v2) ⇒ Less(v1,v2)
  A8  (Domain-bound)        : ∀i∀j∀v  Val(i,j,v) ⇒ InRange(v)
                              i.e. v ∈ {1,...,N}  (làm rõ miền giá trị hợp lệ)

CÁCH BIỂU DIỄN "XÂU ĐÁU" (CONFLICT):
  Để tích hợp với thuật toán Backward/Forward Chaining hiện tại,
  KB vẫn dùng predicate Conflict(r,c,v) — được suy dẫn từ các axioms trên.
  Conflict(r,c,v) = "Đặt v vào ô (r,c) vi phạm ít nhất một axiom".

PREDICATES ĐƯỢC DÙNG:
  - Cell(r, c)              : (r,c) là ô hợp lệ trên bảng  (range-restrict cho FC)
  - InRange(v)              : v thuộc [1,N]                  (A8 – domain bound)
  - Less(v1, v2)            : v1 < v2  (dữ liệu số học)
  - LessH(r, c)             : ô (r,c) phải < ô (r,c+1)      (A4 encoding)
  - LessV(r, c)             : ô (r,c) phải < ô (r+1,c)      (A7 encoding)
  - Given(r, c, v)          : ô (r,c) có clue = v            (A5 encoding)
  - Val(r, c, v)            : ô (r,c) hiện được gán giá trị v  (assert/retract khi search)
  - Conflict(r, c, v)       : đặt v vào (r,c) vi phạm ít nhất 1 axiom
"""

from core.fol_logic import FOLKnowledgeBase, Predicate, Rule
from core.state import State


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_futoshiki_kb(initial_state: "State") -> FOLKnowledgeBase:
    """
    Xây dựng KB đầy đủ từ trạng thái ban đầu.
    Bao gồm: facts cấu trúc bảng + tất cả rules Conflict suy từ A1–A8.
    KHÔNG nạp các Val clue ban đầu — gọi assert_initial_clues() riêng.
    """
    kb = FOLKnowledgeBase()
    N = initial_state.N

    _add_structural_facts(kb, N, initial_state)
    _add_conflict_rules(kb)

    return kb


def assert_initial_clues(kb: FOLKnowledgeBase, initial_state: "State") -> None:
    """
    Nạp các giá trị clue đã cho vào KB dưới dạng Val facts  (A5: Given ⇒ Val).
    Gọi hàm này SAU khi build_futoshiki_kb() và TRƯỚC khi chạy solver.
    """
    for r in range(initial_state.N):
        for c in range(initial_state.N):
            v = initial_state.grid[r][c]
            if v != 0:
                # A5: Given(r,c,v) ⇒ Val(r,c,v)
                # Ở đây ta assert thẳng Val vì Given là fact đơn giản
                kb.add_fact(Predicate("Val", [r, c, v]))


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _add_structural_facts(kb: FOLKnowledgeBase, N: int, state: "State") -> None:
    """
    Thêm tất cả facts mô tả cấu trúc bài toán:
      - Cell(r,c)     — mọi ô hợp lệ  (range-restriction cho FC)
      - InRange(v)    — v ∈ {1,...,N}  (A8)
      - Less(v1,v2)   — quan hệ thứ tự số học
      - LessH(r,c)    — bất đẳng thức ngang từ input  (A4)
      - LessV(r,c)    — bất đẳng thức dọc từ input    (A7)
    """

    # ── Cell(r, c): A1 range-restriction ─────────────────────────────────────
    # Cần để FC có thể sinh ground facts (head phải có biến xuất hiện ở body)
    for r in range(N):
        for c in range(N):
            kb.add_fact(Predicate("Cell", [r, c]))

    # ── InRange(v): A8 – domain bound ────────────────────────────────────────
    # ∀i∀j∀v  Val(i,j,v) ⇒ InRange(v)
    # Ta encode mặt thuận: liệt kê mọi v hợp lệ
    for v in range(1, N + 1):
        kb.add_fact(Predicate("InRange", [v]))

    # ── Less(v1, v2): quan hệ thứ tự ─────────────────────────────────────────
    # Dùng bởi A4/A7 để kiểm tra bất đẳng thức
    for v1 in range(1, N + 1):
        for v2 in range(1, N + 1):
            if v1 < v2:
                kb.add_fact(Predicate("Less", [v1, v2]))

    # ── LessH(r, c): A4 – horizontal inequality ──────────────────────────────
    # LessH(r,c) = "ô (r,c) phải nhỏ hơn ô (r,c+1)"
    # h_constraints[r][c] == 1  →  cell(r,c) < cell(r,c+1)
    # h_constraints[r][c] == -1 →  cell(r,c) > cell(r,c+1)  ≡  cell(r,c+1) < cell(r,c)
    for r in range(N):
        for c in range(N - 1):
            val = state.h_constraints[r][c]
            if val == 1:
                # A4 trực tiếp: LessH(r,c) → (r,c) < (r,c+1)
                kb.add_fact(Predicate("LessH", [r, c, r, c + 1]))
            elif val == -1:
                # Đổi chiều: (r,c+1) < (r,c)
                kb.add_fact(Predicate("LessH", [r, c + 1, r, c]))

    # ── LessV(r, c): A7 – vertical inequality ────────────────────────────────
    # LessV(r,c) = "ô (r,c) phải nhỏ hơn ô (r+1,c)"
    for r in range(N - 1):
        for c in range(N):
            val = state.v_constraints[r][c]
            if val == 1:
                # A7 trực tiếp: (r,c) < (r+1,c)
                kb.add_fact(Predicate("LessV", [r, c, r + 1, c]))
            elif val == -1:
                # Đổi chiều: (r+1,c) < (r,c)
                kb.add_fact(Predicate("LessV", [r + 1, c, r, c]))


def _add_conflict_rules(kb: FOLKnowledgeBase) -> None:
    """
    Thêm các rules suy dẫn Conflict(r,c,v) từ A2, A3, A4, A6, A7, A8.

    ─── Nhóm 1: Vi phạm A2 (At-most-one) ───────────────────────────────────────
      A2 nói mỗi ô chỉ được có 1 giá trị. Nếu KB đã có Val(r,c,v2) với v2≠v
      thì đặt v vào (r,c) tạo mâu thuẫn.

    ─── Nhóm 2: Vi phạm A3 (Row-uniqueness) ────────────────────────────────────
      Nếu Val(r,c_other,v) đã tồn tại trong cùng hàng → Conflict.

    ─── Nhóm 3: Vi phạm A6 (Column-uniqueness) ─────────────────────────────────
      Nếu Val(r_other,c,v) đã tồn tại trong cùng cột → Conflict.

    ─── Nhóm 4: Vi phạm A4 (Horizontal inequality) ─────────────────────────────
      LessH(r,c,r2,c2) nói ô (r,c) < ô (r2,c2).
        Case 4a: ta đang đặt v vào ô TRÁI (r,c), ô PHẢI (r2,c2) đã có v2.
                 Vi phạm khi ¬Less(v, v2) tức v >= v2:
                   • Less(v2, v)  →  v2 < v  →  v không < v2  → Conflict
                   • v == v2      →  không Less  → Conflict (dùng rule riêng)
        Case 4b: ta đang đặt v vào ô PHẢI (r2,c2), ô TRÁI (r,c) đã có v1.
                 Vi phạm khi ¬Less(v1, v) tức v1 >= v:
                   • Less(v, v1)  →  v < v1  → Conflict
                   • v == v1      → Conflict

    ─── Nhóm 5: Vi phạm A7 (Vertical inequality) ───────────────────────────────
      Tương tự A4 nhưng dọc.

    ─── Nhóm 6: Vi phạm A8 (Domain-bound) ──────────────────────────────────────
      Nếu v ∉ {1,...,N} thì Conflict ngay. Trong thực tế solver luôn chọn v từ
      domain nên A8 ít khi kích hoạt, nhưng ta vẫn encode để KB đầy đủ.
    """

    # ════════════════════════════════════════════════════════════════════════
    # NHÓM 1 – Vi phạm A2: At-most-one (mỗi ô chỉ một giá trị)
    # ════════════════════════════════════════════════════════════════════════
    # Nếu KB đã biết Val(r,c,v_old) với v_old ≠ v thì thêm v tạo ô có 2 giá trị.
    # Ta không thể kiểm tra v_old ≠ v bằng FOL thuần túy nếu không có predicate
    # NotEqual; thay vào đó ta dùng: nếu Val(r,c,v_old) tồn tại (bất kỳ v_old)
    # AND v_old ≠ v về mặt số thì Conflict. Vì solver KHÔNG bao giờ gán lại
    # ô đã có giá trị, A2 ở đây chủ yếu bảo vệ tính nhất quán KB:
    #
    #   Conflict(r,c,v) :- Cell(r,c), Val(r,c,v_old), Less(v,v_old).
    #   Conflict(r,c,v) :- Cell(r,c), Val(r,c,v_old), Less(v_old,v).
    #
    # (Hai rules trên cover v < v_old và v > v_old, tức v_old ≠ v)
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Cell", ["r", "c"]),
            Predicate("Val", ["r", "c", "v_old"]),   # ô này đã có giá trị
            Predicate("Less", ["v", "v_old"]),         # v < v_old  ⇒ v ≠ v_old
        ]
    ))
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Cell", ["r", "c"]),
            Predicate("Val", ["r", "c", "v_old"]),
            Predicate("Less", ["v_old", "v"]),         # v_old < v  ⇒ v ≠ v_old
        ]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # NHÓM 2 – Vi phạm A3: Row-uniqueness
    # ════════════════════════════════════════════════════════════════════════
    # A3: Val(r,c1,v) ∧ Val(r,c2,v) ∧ c1≠c2 ⇒ ⊥
    # ↔  Conflict(r,c,v) :- Cell(r,c), Val(r,c_other,v).
    #    (c_other là ô khác trong cùng hàng đã có giá trị v)
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Cell", ["r", "c"]),
            Predicate("Val", ["r", "c_other", "v"]),   # cùng hàng, cùng giá trị
        ]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # NHÓM 3 – Vi phạm A6: Column-uniqueness
    # ════════════════════════════════════════════════════════════════════════
    # A6: Val(r1,c,v) ∧ Val(r2,c,v) ∧ r1≠r2 ⇒ ⊥
    # ↔  Conflict(r,c,v) :- Cell(r,c), Val(r_other,c,v).
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("Cell", ["r", "c"]),
            Predicate("Val", ["r_other", "c", "v"]),   # cùng cột, cùng giá trị
        ]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # NHÓM 4 – Vi phạm A4: Horizontal inequality  LessH(r,c,r2,c2)
    # ════════════════════════════════════════════════════════════════════════

    # Case 4a – ta đặt v vào ô TRÁI (r,c); ô PHẢI (r2,c2) đã có v2.
    # A4 yêu cầu v < v2. Vi phạm khi v >= v2:
    #   sub-case v > v2:  Less(v2, v)  tồn tại
    #   sub-case v == v2: được xử lý bởi rule A3/A6 (cùng giá trị trong hàng)
    #                     HOẶC rule riêng dưới đây dùng Val(r2,c2,v) trực tiếp

    kb.add_rule(Rule(
        # v > v2:  Less(v2, v) & Val(r2,c2,v2) & LessH(r,c,r2,c2)
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessH", ["r", "c", "r2", "c2"]),   # (r,c) phải < (r2,c2)
            Predicate("Val", ["r2", "c2", "v2"]),           # ô phải đã có v2
            Predicate("Less", ["v2", "v"]),                  # v2 < v  ⇒ v ≥ v2, vi phạm
        ]
    ))
    kb.add_rule(Rule(
        # v == v2:  Val(r2,c2,v) – ô phải đã có đúng v
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessH", ["r", "c", "r2", "c2"]),
            Predicate("Val", ["r2", "c2", "v"]),            # ô phải cũng có v → v không < v
        ]
    ))

    # Case 4b – ta đặt v vào ô PHẢI (r,c) trong ràng buộc LessH(r1,c1,r,c);
    # ô TRÁI (r1,c1) đã có v1. A4 yêu cầu v1 < v. Vi phạm khi v <= v1:
    #   sub-case v < v1:  Less(v, v1) tồn tại
    #   sub-case v == v1: Val(r1,c1,v)
    kb.add_rule(Rule(
        # v < v1
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessH", ["r1", "c1", "r", "c"]),    # (r1,c1) phải < (r,c)
            Predicate("Val", ["r1", "c1", "v1"]),            # ô trái đã có v1
            Predicate("Less", ["v", "v1"]),                  # v < v1  ⇒ v1 không < v, vi phạm
        ]
    ))
    kb.add_rule(Rule(
        # v == v1
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessH", ["r1", "c1", "r", "c"]),
            Predicate("Val", ["r1", "c1", "v"]),             # ô trái cũng có v → v1 không < v
        ]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # NHÓM 5 – Vi phạm A7: Vertical inequality  LessV(r,c,r2,c2)
    # ════════════════════════════════════════════════════════════════════════
    # Đối xứng hoàn toàn với A4 nhưng theo chiều dọc.

    # Case 5a – ta đặt v vào ô TRÊN (r,c); ô DƯỚI (r2,c2) đã có v2.
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessV", ["r", "c", "r2", "c2"]),
            Predicate("Val", ["r2", "c2", "v2"]),
            Predicate("Less", ["v2", "v"]),
        ]
    ))
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessV", ["r", "c", "r2", "c2"]),
            Predicate("Val", ["r2", "c2", "v"]),
        ]
    ))

    # Case 5b – ta đặt v vào ô DƯỚI (r,c); ô TRÊN (r1,c1) đã có v1.
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessV", ["r1", "c1", "r", "c"]),
            Predicate("Val", ["r1", "c1", "v1"]),
            Predicate("Less", ["v", "v1"]),
        ]
    ))
    kb.add_rule(Rule(
        Predicate("Conflict", ["r", "c", "v"]),
        [
            Predicate("LessV", ["r1", "c1", "r", "c"]),
            Predicate("Val", ["r1", "c1", "v"]),
        ]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # NHÓM 6 – Vi phạm A8: Domain-bound  (v ∉ {1,...,N})
    # ════════════════════════════════════════════════════════════════════════
    # A8: Val(r,c,v) ⇒ InRange(v).  Phủ định: ¬InRange(v) ⇒ Conflict.
    # Ta encode: Conflict(r,c,v) :- Cell(r,c), NOT InRange(v).
    # Vì FOL-BC/FC thuần túy không hỗ trợ negation-as-failure trực tiếp,
    # ta dùng trick: liệt kê mọi v ngoài [1,N] là Conflict bằng cách
    # KHÔNG thêm InRange cho chúng → khi BC query InRange(v) sẽ fail.
    # Rule dưới thực ra là placeholder; solver luôn chọn v từ InRange nên
    # A8 ít khi kích hoạt, nhưng để KB ngữ nghĩa đầy đủ ta vẫn ghi chú.
    #
    # NOTE: Với FOL-BC/FC hiện tại (closed-world assumption), nếu v không
    # có fact InRange(v) thì query InRange(v) tự động fail → KB ngầm định
    # đúng A8 mà không cần rule bổ sung.