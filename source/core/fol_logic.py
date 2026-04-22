from typing import List, Dict, Any, Generator, Optional, Tuple
from collections import defaultdict

# Substitution Theta is a dictionary mapping Variable -> Value
Theta = Dict[str, Any]

class Predicate:
    def __init__(self, name: str, args: List[Any]):
        self.name = name
        self.args = args

    def __repr__(self):
        args_str = ", ".join(map(str, self.args))
        return f"{self.name}({args_str})"

    def substitute(self, theta: Theta) -> 'Predicate':
        """Subtitution to generate a new sentence"""
        new_args = [theta.get(arg, arg) if isinstance(arg, str) else arg for arg in self.args]
        return Predicate(self.name, new_args)

    def to_key(self) -> Tuple:
        """Hashable identity key for a ground predicate. Used by TMS."""
        return (self.name, tuple(self.args))


class Rule:
    def __init__(self, head: Predicate, body: List[Predicate]):
        self.head = head
        self.body = body

    def standardize_variables(self, suffix: int) -> 'Rule':
        """Rename variables to avoid collision"""
        theta = {arg: f"{arg}_{suffix}" for arg in self.head.args if isinstance(arg, str)}
        for b in self.body:
            for arg in b.args:
                if isinstance(arg, str) and arg not in theta:
                    theta[arg] = f"{arg}_{suffix}"
        new_head = self.head.substitute(theta)
        new_body = [b.substitute(theta) for b in self.body]
        return Rule(new_head, new_body)

    def __repr__(self):
        body_str = " ^ ".join(map(str, self.body))
        if not body_str:
            return str(self.head)
        return f"{self.head} :- {body_str}"


def _is_variable(x: Any) -> bool:
    """A variable is a non-empty lowercase string."""
    return isinstance(x, str) and len(x) > 0 and x[0].islower()


def unify(x: Any, y: Any, theta: Optional[Theta]) -> Optional[Theta]:
    if theta is None:
        return None
    elif x == y:
        return theta
    elif _is_variable(x):
        return unify_var(x, y, theta)
    elif _is_variable(y):
        return unify_var(y, x, theta)
    elif isinstance(x, Predicate) and isinstance(y, Predicate):
        if x.name != y.name or len(x.args) != len(y.args):
            return None
        return unify(x.args, y.args, theta)
    elif isinstance(x, list) and isinstance(y, list):
        if not x and not y:
            return theta
        return unify(x[1:], y[1:], unify(x[0], y[0], theta))
    else:
        return None


def unify_var(var: str, x: Any, theta: Theta) -> Optional[Theta]:
    if var in theta:
        return unify(theta[var], x, theta)
    elif _is_variable(x) and x in theta:
        return unify(var, theta[x], theta)
    else:
        new_theta = theta.copy()
        new_theta[var] = x
        return new_theta


class FOLKnowledgeBase:
    def __init__(self):
        self.facts: Dict[str, List[Predicate]] = defaultdict(list)
        self.rules: Dict[str, List[Rule]] = defaultdict(list)
        self._standardize_counter = 0
        self.inference_count = 0

    def add_fact(self, fact: Predicate):
        self.facts[fact.name].append(fact)

    def add_rule(self, rule: Rule):
        self.rules[rule.head.name].append(rule)

    def retract_fact(self, fact_name: str):
        """Rút lui (Backtrack) một sự thật dựa trên tên Index của nó."""
        if self.facts[fact_name]:
            self.facts[fact_name].pop()

    def fetch_rules_for_goal(self, goal: Predicate) -> List[Rule]:
        """Lấy tất cả các luật và facts có Head khớp với tên của Goal."""
        matching_rules = []
        for fact in self.facts.get(goal.name, []):
            matching_rules.append(Rule(fact, []))
        for rule in self.rules.get(goal.name, []):
            matching_rules.append(rule)
        return matching_rules

    def count_clauses(self) -> int:
        """Return the total number of facts and rules in KB."""
        fact_count = sum(len(f_list) for f_list in self.facts.values())
        rule_count = sum(len(r_list) for r_list in self.rules.values())
        return fact_count + rule_count

    # =========================================================
    # BACKWARD CHAINING (giữ nguyên)
    # =========================================================

    def fol_bc_ask(self, query: Predicate) -> Generator[Theta, None, None]:
        """function FOL-BC-ASK(KB,query) returns a generator of substitutions"""
        yield from self.fol_bc_or(query, {})

    def fol_bc_or(self, goal: Predicate, theta: Theta) -> Generator[Theta, None, None]:
        is_ground = all(not isinstance(arg, str) for arg in goal.args)
        if is_ground and goal.name in ["Less", "Constraint"]:
            self.inference_count += 1
            found = any(goal.args == fact.args for fact in self.facts.get(goal.name, []))
            if found:
                yield theta
                return
            else:
                return

        for rule in self.fetch_rules_for_goal(goal):
            self.inference_count += 1
            self._standardize_counter += 1
            std_rule = rule.standardize_variables(self._standardize_counter)
            lhs = std_rule.body
            rhs = std_rule.head
            unify_theta = unify(rhs, goal, theta)
            if unify_theta is not None:
                yield from self.fol_bc_and(lhs, unify_theta)

    def fol_bc_and(self, goals: List[Predicate], theta: Optional[Theta]) -> Generator[Theta, None, None]:
        if theta is None:
            return
        elif len(goals) == 0:
            yield theta
        else:
            first = goals[0]
            rest = goals[1:]
            subst_first = first.substitute(theta)
            for theta_prime in self.fol_bc_or(subst_first, theta):
                yield from self.fol_bc_and(rest, theta_prime)

    # =========================================================
    # FORWARD CHAINING (snapshot/restore — giữ nguyên)
    # =========================================================

    def fol_fc_ask(self, query: Predicate, max_iter: int = 50) -> bool:
        """
        FOL-FC-ASK (AIMA): Suy dẫn tiến với snapshot/restore.
        KB được snapshot trước khi chạy và khôi phục sau khi xong.
        Xem forward_chaining_tms.py để dùng phiên bản TMS không snapshot.
        """
        snapshot = {k: list(v) for k, v in self.facts.items()}

        try:
            self.inference_count += 1
            for fact in self.facts.get(query.name, []):
                if unify(query, fact, {}) is not None:
                    return True

            for _ in range(max_iter):
                new_facts: List[Predicate] = []

                for rules_list in list(self.rules.values()):
                    for rule in rules_list:
                        self._standardize_counter += 1
                        std_rule = rule.standardize_variables(self._standardize_counter)

                        for theta in self._satisfy_body(std_rule.body, {}):
                            self.inference_count += 1
                            q_prime = std_rule.head.substitute(theta)

                            if not self._is_ground(q_prime):
                                continue
                            if self._fact_exists(q_prime):
                                continue
                            if self._fact_in_list(q_prime, new_facts):
                                continue

                            new_facts.append(q_prime)

                            if unify(q_prime, query, {}) is not None:
                                for f in new_facts:
                                    self.add_fact(f)
                                return True

                if not new_facts:
                    return False

                for f in new_facts:
                    self.add_fact(f)

            return False
        finally:
            self.facts = defaultdict(list)
            for k, v in snapshot.items():
                self.facts[k] = v

    def _satisfy_body(self, body: List[Predicate], theta: Theta) -> Generator[Theta, None, None]:
        if not body:
            yield theta
            return
        first = body[0].substitute(theta)
        for fact in self.facts.get(first.name, []):
            new_theta = unify(first, fact, dict(theta))
            if new_theta is not None:
                yield from self._satisfy_body(body[1:], new_theta)

    def _is_ground(self, pred: Predicate) -> bool:
        for arg in pred.args:
            if _is_variable(arg):
                return False
        return True

    def _fact_exists(self, pred: Predicate) -> bool:
        for f in self.facts.get(pred.name, []):
            if pred.args == f.args:
                return True
        return False

    def _fact_in_list(self, pred: Predicate, fact_list: List[Predicate]) -> bool:
        for f in fact_list:
            if pred.name == f.name and pred.args == f.args:
                return True
        return False