from typing import List, Dict, Any, Generator, Optional
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
    
class Rule:
    def __init__(self, head: Predicate, body: List[Predicate]):
        self.head = head # Goal needs to be proved
        self.body = body # List of conditions

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
    
def unify(x: Any, y: Any, theta: Optional[Theta]) -> Optional[Theta]:
    if theta is None:
        return None
    elif x == y:
        return theta
    elif isinstance(x, str) and x.islower():  # Nếu x là Biến (viết thường)
        return unify_var(x, y, theta)
    elif isinstance(y, str) and y.islower():  # Nếu y là Biến
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
    elif isinstance(x, str) and x.islower() and x in theta:
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
        # Chuyển các fact thành Rule với body rỗng: Fact :- T
        for fact in self.facts.get(goal.name, []):
            matching_rules.append(Rule(fact, []))

        for rule in self.rules.get(goal.name, []):
            matching_rules.append(rule)
        return matching_rules

    # =========================================================
    # PSEUDO-CODE IMPLEMENTATION
    # =========================================================

    def fol_bc_ask(self, query: Predicate) -> Generator[Theta, None, None]:
        """function FOL-BC-ASK(KB,query) returns a generator of substitutions"""
        yield from self.fol_bc_or(query, {})

    def fol_bc_or(self, goal: Predicate, theta: Theta) -> Generator[Theta, None, None]:
        """generator FOL-BC-OR(KB,goal, θ) yields a substitution"""

        # [PRUNING TỐI ƯU]: Check Ground Goal Fail-fast
        # Nếu goal không có biến (tất cả args là số), và nó là một Static Fact (như Less), 
        # mà nó không nằm trong KB -> Cắt nhánh ngay lập tức!
        is_ground = all(not isinstance(arg, str) for arg in goal.args)
        if is_ground and goal.name in ["Less", "Constraint"]:
            # So sánh string trực tiếp cho lẹ, bỏ qua Unify đắt đỏ
            found = any(goal.args == fact.args for fact in self.facts.get(goal.name, []))
            if not found:
                return # Cắt nhánh (Pruned!)
            
        for rule in self.fetch_rules_for_goal(goal):
            # (lhs, rhs) <- STANDARDIZE-VARIABLES((lhs, rhs))
            self._standardize_counter += 1
            std_rule = rule.standardize_variables(self._standardize_counter)
            
            lhs = std_rule.body  # Body của Horn clause
            rhs = std_rule.head  # Head của Horn clause

            # for each θ’ in FOL-BC-AND(KB, lhs, UNIFY(rhs, goal, θ)) do
            unify_theta = unify(rhs, goal, theta)
            if unify_theta is not None:
                yield from self.fol_bc_and(lhs, unify_theta)

    def fol_bc_and(self, goals: List[Predicate], theta: Optional[Theta]) -> Generator[Theta, None, None]:
        """generator FOL-BC-AND(KB,goals, θ) yields a substitution"""
        if theta is None:  # if θ = failure then return
            return
        elif len(goals) == 0:  # else if LENGTH(goals) = 0 then yield θ
            yield theta
        else:  # else do
            first = goals[0]
            rest = goals[1:]
            
            # for each θ’ in FOL-BC-OR(KB, SUBST(θ, first), θ) do
            subst_first = first.substitute(theta)
            for theta_prime in self.fol_bc_or(subst_first, theta):
                # for each θ’’ in FOL-BC-AND(KB, rest, θ’) do
                yield from self.fol_bc_and(rest, theta_prime)