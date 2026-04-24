"""
forward_chaining_tms.py
───────────────────────
Forward Chaining Solver với TMS (Truth Maintenance System).

Khác biệt so với forward_chaining.py gốc:
  - Không dùng snapshot/restore KB sau mỗi fol_fc_ask().
  - Mỗi fact được suy ra (inferred) được lưu kèm tập parents (justifications)
    trong Dependency Graph.
  - Khi backtrack và retract_fact("Val"), hệ thống chỉ xóa đúng những
    inferred facts phụ thuộc vào Val đó — các inferences hợp lệ từ nhánh
    khác được giữ lại, tránh tái sinh trùng lặp.

Tất cả file khác (fol_logic.py, futoshiki_kb.py, forward_chaining.py)
giữ nguyên không thay đổi.
"""

import time
from typing import Optional, Dict, Set, List, Tuple, Generator
from collections import defaultdict

from core.state import State
from core.fol_logic import (
    FOLKnowledgeBase, Predicate, Rule,
    _is_variable, unify, Theta
)
from solvers.futoshiki_kb import build_futoshiki_kb, assert_initial_clues


# ─────────────────────────────────────────────────────────────────────────────
# TMS – Truth Maintenance System (Dependency Graph)
# ─────────────────────────────────────────────────────────────────────────────

class TMSNode:
    """
    Một node trong Dependency Graph, đại diện cho một ground fact.

    Attributes
    ----------
    pred_key : (name, args_tuple) — identity duy nhất của fact
    is_base  : True  → fact được assert trực tiếp (clue hoặc Val do solver gán).
                       Không bao giờ bị cascade-delete.
               False → fact được suy ra bởi FC.
                       Bị xóa khi toàn bộ justifications của nó bị mất.
    parents  : set pred_key mà fact này được suy ra TỪ ĐÓ (justification set).
    children : set pred_key được suy ra TỪ fact này (dependants).
               Dùng để cascade deletion nhanh O(children).
    """
    __slots__ = ("pred_key", "is_base", "parents", "children")

    def __init__(self, pred_key: Tuple, is_base: bool,
                 parents: Optional[Set[Tuple]] = None):
        self.pred_key: Tuple      = pred_key
        self.is_base:  bool       = is_base
        self.parents:  Set[Tuple] = parents if parents is not None else set()
        self.children: Set[Tuple] = set()


class TMSKnowledgeBase(FOLKnowledgeBase):
    """
    Mở rộng FOLKnowledgeBase với Dependency Graph để quản lý
    vòng đời của các inferred facts.

    Override:
      - add_fact()     → đăng ký node vào TMS
      - retract_fact() → cascade delete thay vì pop()
      - fol_fc_ask()   → không snapshot/restore, dùng TMS

    Giữ nguyên hoàn toàn:
      - fol_bc_ask(), fol_bc_or(), fol_bc_and() — BC không thay đổi
      - fetch_rules_for_goal(), count_clauses(), v.v.
    """

    def __init__(self):
        super().__init__()
        # Dependency Graph: pred_key -> TMSNode
        self._tms: Dict[Tuple, TMSNode] = {}
        self.log_func = None

    # ── Fact management ───────────────────────────────────────────────────

    def add_fact(self, fact: Predicate, is_base: bool = True,
                 parents: Optional[Set[Tuple]] = None) -> None:
        """
        Thêm fact vào KB và đăng ký vào TMS.

        Parameters
        ----------
        is_base : True  → base fact (clue / Val do solver gán).
                          Không bị cascade-delete.
                  False → inferred fact do FC sinh ra.
                          Bị cascade-delete khi parents bị retract.
        parents : set pred_key của các facts tạo ra fact này.
        """
        key = fact.to_key()

        if key in self._tms:
            # Promote inferred → base nếu cần
            node = self._tms[key]
            if is_base and not node.is_base:
                node.is_base = True
                node.parents.clear()
            return

        node = TMSNode(key, is_base, parents or set())
        self._tms[key] = node

        # Đăng ký cạnh parent → child
        if parents:
            for p_key in parents:
                if p_key in self._tms:
                    self._tms[p_key].children.add(key)

        self.facts[fact.name].append(fact)
        if not is_base and self.log_func:
            self.log_func(f"+ ASSERT  {fact}")

    def retract_fact(self, fact_name: str) -> None:
        """
        Retract base fact gần nhất có tên fact_name, sau đó
        cascade-delete tất cả inferred facts phụ thuộc vào nó.

        Các inferred facts còn ít nhất một parent sống sót
        (justification khác) sẽ được GIỮ LẠI.
        """
        candidates = [
            f for f in self.facts.get(fact_name, [])
            if self._tms.get(f.to_key(), TMSNode(f.to_key(), True)).is_base
        ]
        if not candidates:
            return
        self._cascade_delete(candidates[-1].to_key())

    def _cascade_delete(self, root_key: Tuple) -> None:
        """
        BFS trên Dependency Graph:
        Xóa root_key và mọi inferred descendant có ít nhất
        một parent nằm trong tập bị xóa.

        Lý do dùng ANY thay vì ALL:
        Trong Futoshiki KB, mỗi Conflict fact được derive từ
        body gồm cả Cell(r,c) (base fact, không bao giờ bị xóa)
        lẫn Val(r,c,v) (base fact, bị retract khi backtrack).
        Nếu dùng ALL → Conflict không bao giờ bị cascade vì Cell
        luôn sống sót → Conflict cũ từ nhánh trước bị giữ lại sai
        → solver trả False nhầm khi query Conflict(r,c,v) hợp lệ.
        Dùng ANY: hễ một Val parent bị retract → Conflict bị xóa,
        đảm bảo KB sạch sau mỗi backtrack.
        """
        to_delete: Set[Tuple] = set()
        stack = [root_key]

        while stack:
            cur = stack.pop()
            if cur in to_delete:
                continue
            to_delete.add(cur)

            node = self._tms.get(cur)
            if node is None:
                continue

            for child_key in list(node.children):
                child_node = self._tms.get(child_key)
                if child_node is None or child_node.is_base:
                    continue
                # Cascade nếu BẤT KỲ parent nào bị xóa
                if child_node.parents & to_delete:
                    stack.append(child_key)

        # Xóa khỏi TMS và facts storage
        for del_key in to_delete:
            node = self._tms.pop(del_key, None)
            if node is None:
                continue
            # Dọn cạnh parent → child
            for p_key in node.parents:
                p_node = self._tms.get(p_key)
                if p_node:
                    p_node.children.discard(del_key)
            # Xóa khỏi facts list
            name = del_key[0]
            self.facts[name] = [
                f for f in self.facts.get(name, [])
                if f.to_key() != del_key
            ]
            if self.log_func and del_key != root_key:
                args_str = ", ".join(map(str, del_key[1]))
                self.log_func(f"- RETRACT {name}({args_str})")

    # ── Forward Chaining với TMS ──────────────────────────────────────────

    def fol_fc_ask(self, query: Predicate, max_iter: int = 50) -> bool:
        """
        FOL-FC-ASK với TMS Dependency Graph.

        Thay vì snapshot/restore toàn bộ KB sau mỗi query, mỗi
        inferred fact được lưu cùng parents vào TMS. Khi solver
        backtrack và gọi retract_fact("Val"), chỉ các facts phụ
        thuộc trực tiếp vào Val đó bị xóa — các inferences hợp lệ
        từ các Val khác được bảo toàn để tái sử dụng.
        """
        # Fast path: query đã có trong KB
        self.inference_count += 1
        for fact in self.facts.get(query.name, []):
            if unify(query, fact, {}) is not None:
                return True

        for _ in range(max_iter):
            new_facts: List[Tuple[Predicate, Set[Tuple]]] = []

            for rules_list in list(self.rules.values()):
                for rule in rules_list:
                    self._standardize_counter += 1
                    std_rule = rule.standardize_variables(self._standardize_counter)

                    for theta, used_keys in self._satisfy_body_tms(std_rule.body, {}, frozenset()):
                        self.inference_count += 1
                        q_prime = std_rule.head.substitute(theta)

                        # Chỉ giữ ground facts (range restriction)
                        if not self._is_ground(q_prime):
                            continue

                        key = q_prime.to_key()
                        if key in self._tms:
                            continue
                        if any(f.to_key() == key for f, _ in new_facts):
                            continue

                        new_facts.append((q_prime, set(used_keys)))

                        # Early exit: query được thỏa
                        if unify(q_prime, query, {}) is not None:
                            for nf, parents in new_facts:
                                if nf.to_key() not in self._tms:
                                    self.add_fact(nf, is_base=False, parents=parents)
                            return True

            if not new_facts:
                return False

            # Nạp facts mới vào TMS kèm parents
            for nf, parents in new_facts:
                if nf.to_key() not in self._tms:
                    self.add_fact(nf, is_base=False, parents=parents)

        return False

    def _satisfy_body_tms(
        self,
        body: List[Predicate],
        theta: Theta,
        used_keys: frozenset,
    ) -> Generator[Tuple[Theta, frozenset], None, None]:
        """
        Match body với KB, đồng thời thu thập pred_key của mọi
        fact được dùng → trở thành parents của head trong TMS.
        """
        if not body:
            yield theta, used_keys
            return

        first = body[0].substitute(theta)
        for fact in self.facts.get(first.name, []):
            new_theta = unify(first, fact, dict(theta))
            if new_theta is not None:
                new_used = used_keys | {fact.to_key()}
                yield from self._satisfy_body_tms(body[1:], new_theta, new_used)

    def _fact_exists(self, pred: Predicate) -> bool:
        return pred.to_key() in self._tms


# ─────────────────────────────────────────────────────────────────────────────
# Solver
# ─────────────────────────────────────────────────────────────────────────────

class ForwardChainingTMSSolver:
    """
    Forward Chaining Solver dùng TMSKnowledgeBase.
    Interface giống hệt ForwardChainingSolver — dùng thay thế trực tiếp.
    """

    def __init__(self, initial_state: 'State', stop_event=None) -> None:
        self.initial_state: 'State'       = initial_state
        self.stop_event                   = stop_event
        self.nodes_expanded:          int = 0
        self.num_inferences:          int = 0
        self.num_initial_clauses:     int = 0
        self.total_number_of_clauses: int = 0
        self.elapsed:               float = 0.0
        self.kb: TMSKnowledgeBase         = self._build_kb(initial_state)

        # KB log — GUI reads this list to display
        self.kb_log_lines: List[str] = []

    # Logging helpers
    def _log(self, line: str) -> None:
        self.kb_log_lines.append(line)

    def _log_initial_kb(self) -> None:
        """Log KB ban đầu 1 lần duy nhất trước khi bắt đầu tìm kiếm."""
        self._log("=== INITIAL KB ===")
        for name, fact_list in sorted(self.kb.facts.items()):
            if fact_list:
                self._log(f"[{name}] ({len(fact_list)})")
                for f in fact_list:
                    self._log(f"  {f}")
        self._log("")

    # KB wrappers
    def _assert_fact(self, fact: Predicate) -> None:
        """Assert Val fact vào KB (is_base=True) và log."""
        self.kb.add_fact(fact, is_base=True)
        self._log(f"+ ASSERT  {fact}")

    def _retract_fact(self, fact_name: str, fact: Predicate) -> None:
        """Retract fact khỏi KB (cascade TMS) và log."""
        self.kb.retract_fact(fact_name)
        self._log(f"- RETRACT {fact}")

    # Build KB
    def _build_kb(self, initial_state: 'State') -> TMSKnowledgeBase:
        """
        Tái dùng build_futoshiki_kb() để lấy rules/facts,
        rồi inject vào TMSKnowledgeBase.
        """
        base_kb = build_futoshiki_kb(initial_state)

        tms_kb = TMSKnowledgeBase()
        tms_kb._standardize_counter = base_kb._standardize_counter
        tms_kb.log_func = self._log

        # Copy rules
        for rule_list in base_kb.rules.values():
            for rule in rule_list:
                tms_kb.add_rule(rule)

        # Copy base facts (Cell, Less, Constraint) với is_base=True
        for fact_list in base_kb.facts.values():
            for fact in fact_list:
                tms_kb.add_fact(fact, is_base=True)

        return tms_kb

    # Solve 
    def solve(self) -> Optional[State]:
        self.nodes_expanded  = 0
        self.num_inferences  = 0
        start = time.perf_counter()

        assert_initial_clues(self.kb, self.initial_state)

        self.num_initial_clauses = self.kb.count_clauses()
        self.kb.inference_count  = 0

        result = self._sld_resolve(self.initial_state)

        self.total_number_of_clauses = self.kb.count_clauses()
        self.num_inferences          = self.kb.inference_count
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
            query = Predicate("Conflict", [r, c, v])
            has_conflict = self.kb.fol_fc_ask(query)

            if not has_conflict:
                # Assert Val(r,c,v) là base fact
                fact = Predicate("Val", [r, c, v])
                self._assert_fact(fact)
                new_state = current_state.assign_value(r, c, v)

                if self._forward_check(new_state):
                    result = self._sld_resolve(new_state)
                    if result is not None:
                        return result

                # Backtrack: cascade-delete Val(r,c,v) và mọi
                # inferred fact phụ thuộc vào nó
                self._retract_fact("Val", fact)

        return None

    def _forward_check(self, state: 'State') -> bool:
        for r in range(state.N):
            for c in range(state.N):
                if state.grid[r][c] == 0:
                    new_domain = state.get_pruned_domain(r, c)
                    if not new_domain:
                        return False
                    state.domains[r][c] = new_domain
        return True