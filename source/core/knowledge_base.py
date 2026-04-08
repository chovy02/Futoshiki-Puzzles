#core/knowledge_base.py

import itertools
from typing import List
from state import State

class KnowledgeBase:
    def __init__(self, N: int) -> None:
        self.N: int = N
        self.clauses: List[List[int]] = []

    def encode_var(self, r: int, c: int, value: int) -> int:
        """Encode clause Val(r, c, v) into a unique ID"""
        return r * (self.N * self.N) + c * self.N + value

    def generate_base_rules(self) -> None:
        """
        Four base rules:
        1. Every cell has at least one value ∀i∀j ∃v Val(i,j,v)
        2. Every cell has at most one value ∀i∀j ∀v1 ∀v2 Val(i,j,v1) ∧ Val(i,j,v2) ⇒ v1 = v2
        3. Row uniqueness ∀i∀j1 ∀j2 ∀v Val(i,j1,v) ∧ Val(i,j2,v) ∧ j1 ̸ = j2 ⇒ ⊥
        4. Column uniqueness ∀j∀i1 ∀i2 ∀v Val(i1,j,v) ∧ Val(i2,j,v) ∧ i1 ̸ = i2 ⇒ ⊥
        """ 

        N = self.N

        # Rule 1: Every cell has at least one value
        for r in range(N):
            for c in range(N):
                # (Val(r, c, 1) V Val(r, c, 2) V ... V Val(r, c, N))
                clause: List[int] = [self.encode_var(r, c, v) for v in range(1, N + 1)]
                self.clauses.append(clause)

        # Rule 2: Every cell has at most one value
        for r in range(N):
            for c in range(N):
                for v1, v2 in itertools.combinations(range(1, N + 1), 2):
                    # (-Val(r,c,v1) V -Val(r,c,v2))
                    self.clauses.append([-self.encode_var(r, c, v1), -self.encode_var(r, c, v2)])

        # Rule 3: Row uniqueness
        for r in range(N):
            for v in range(1, N + 1):
                for c1, c2 in itertools.combinations(range(N), 2):
                    # (-Val(r,c1,v) V -Val(r,c2,v))
                    self.clauses.append([-self.encode_var(r, c1, v), -self.encode_var(r, c2, v)])

        # Rule 4: Column uniqueness
        for c in range(N):
            for v in range(1, N + 1):
                for r1, r2 in itertools.combinations(range(N), 2):
                    # (-Val(r1,c,v) V -Val(r2,c,v))
                    self.clauses.append([-self.encode_var(r1, c, v), -self.encode_var(r2, c, v)])

    def generate_given_clues(self, grid: List[List[int]]) -> None:
        # Rule 5: Given clues are enforced ∀i∀j ∀v Given(i,j,v) ⇒ Val(i,j,v)
        for r in range(self.N):
            for c in range(self.N):
                val = grid[r][c]
                if val != 0:
                    # Val(i, j, v)
                    self.clauses.append([self.encode_var(r, c, val)])

    def generate_horizontal_constraints(self, h_constraints: List[List[int]]) -> None:
        # Rule 6: Horizontal inequality constraints ∀i∀j ∀v1 ∀v2 LessH(i,j) ∧ Val(i,j,v1) ∧ Val(i,j+1,v2) ⇒ Less(v1,v2)
        for r in range(self.N):
            for c in range(self.N - 1):
                if h_constraints[r][c] == 1:  # Left Cell < Right Cell
                    for v1 in range(1, self.N + 1):
                        for v2 in range(1, self.N + 1):
                            if v1 >= v2:
                                # (-Val(r, c, v1) V -Val(r, c + 1, v2))
                                self.clauses.append([-self.encode_var(r, c, v1), -self.encode_var(r, c + 1, v2)])
                
                elif h_constraints[r][c] == -1: # Left Cell < Right Cell
                    for v1 in range(1, self.N + 1):
                        for v2 in range(1, self.N + 1):
                            if v1 <= v2:
                                # (-Val(r, c, v1) V -Val(r, c + 1, v2))
                                self.clauses.append([-self.encode_var(r, c, v1), -self.encode_var(r, c + 1, v2)])

    def generate_vertical_constraints(self, v_constraints: List[List[int]]) -> None:
        # Rule 7: Vertical inequality constraints ∀i∀j ∀v1 ∀v2 LessV(i,j) ∧ Val(i, j, v1) ∧ Val(i + 1, j, v2) ⇒ Less(v1, v2)
        for r in range(self.N - 1):
            for c in range(self.N):
                if v_constraints[r][c] == 1:  # Top Cell < Bottom Cell
                    for v1 in range(1, self.N + 1):
                        for v2 in range(1, self.N + 1):
                            if v1 >= v2:
                                # (-Val(r, c, v1) V -Val(r + 1, c, v2))
                                self.clauses.append([-self.encode_var(r, c, v1), -self.encode_var(r + 1, c, v2)])
                
                elif v_constraints[r][c] == -1: # Ô Trên > Ô Dưới
                    for v1 in range(1, self.N + 1):
                        for v2 in range(1, self.N + 1):
                            if v1 <= v2:
                                # (-Val(r, c, v1) V -Val(r + 1, c, v2))
                                self.clauses.append([-self.encode_var(r, c, v1), -self.encode_var(r + 1, c, v2)])

    def generate_all_clauses(self, state: 'State') -> List[List[int]]:
        self.clauses = []
        self.generate_base_rules()
        self.generate_given_clues(state.grid)
        self.generate_horizontal_constraints(state.h_constraints)
        self.generate_vertical_constraints(state.v_constraints)
        return self.clauses

    

        