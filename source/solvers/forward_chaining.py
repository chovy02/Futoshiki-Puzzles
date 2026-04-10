"""Forward chaining solver for Futoshiki.

Implements forward chaining as constraint propagation:
  1. Start with given clues as facts.
  2. Derive new Val(i,j,v) facts via row/column uniqueness and inequality
     constraint propagation until fixed point.
  3. If pure propagation cannot complete the puzzle, fall back to
     backtracking search where each branch re-runs full propagation.

Each derived Val(i,j,v) is recorded in self.steps in the order it was
inferred, so the GUI can replay the inference chain step by step.
"""
import time
from typing import List, Tuple, Optional, Set
from core.state import State


class ForwardChainingSolver:
    def __init__(self, initial_state: State):
        self.initial_state = initial_state
        self.N = initial_state.N
        self.steps: List[Tuple[int, int, int]] = []
        self.nodes_expanded = 0
        self.elapsed = 0.0

    def solve(self) -> Optional[State]:
        start = time.perf_counter()
        state = self.initial_state.clone()
        # Re-init domains based on current grid (in case clone copied stale data).
        for r in range(self.N):
            for c in range(self.N):
                if state.grid[r][c] != 0:
                    state.domains[r][c] = [state.grid[r][c]]
                else:
                    state.domains[r][c] = list(range(1, self.N + 1))

        ok, prop_steps = self._propagate(state)
        if not ok:
            self.elapsed = time.perf_counter() - start
            return None

        if state.is_complete():
            self.steps = prop_steps
            self.elapsed = time.perf_counter() - start
            return state

        result = self._backtrack(state, prop_steps)
        self.elapsed = time.perf_counter() - start
        if result is None:
            return None
        solved_state, path = result
        self.steps = path
        return solved_state

    def _propagate(self, state: State) -> Tuple[bool, List[Tuple[int, int, int]]]:
        """Forward chaining: prune domains and unit-propagate until fixed point."""
        N = self.N
        derived: List[Tuple[int, int, int]] = []
        changed = True
        while changed:
            changed = False
            for r in range(N):
                for c in range(N):
                    if state.grid[r][c] != 0:
                        continue
                    domain = set(state.domains[r][c])
                    # Row uniqueness
                    for cc in range(N):
                        if cc != c and state.grid[r][cc] != 0:
                            domain.discard(state.grid[r][cc])
                    # Column uniqueness
                    for rr in range(N):
                        if rr != r and state.grid[rr][c] != 0:
                            domain.discard(state.grid[rr][c])
                    # Inequality constraints
                    domain = self._prune_inequality(state, r, c, domain)

                    if not domain:
                        return False, derived

                    new_domain = sorted(domain)
                    if len(new_domain) < len(state.domains[r][c]):
                        state.domains[r][c] = new_domain
                        changed = True

                    # Unit propagation: |domain|=1 ⇒ derive Val(r,c,v)
                    if len(new_domain) == 1:
                        v = new_domain[0]
                        state.grid[r][c] = v
                        derived.append((r, c, v))
                        changed = True
        return True, derived

    def _prune_inequality(self, state, r, c, domain):
        N = self.N
        # Left neighbor: h_constraints[r][c-1] is between (r,c-1) and (r,c)
        if c > 0:
            h = state.h_constraints[r][c - 1]
            left = state.grid[r][c - 1]
            if h != 0:
                if left != 0:
                    if h == 1:    # left < right ⇒ we (right) > left
                        domain = {v for v in domain if v > left}
                    else:         # h == -1, left > right
                        domain = {v for v in domain if v < left}
                else:
                    ld = state.domains[r][c - 1]
                    if ld:
                        if h == 1:
                            domain = {v for v in domain if v > min(ld)}
                        else:
                            domain = {v for v in domain if v < max(ld)}
        # Right neighbor: h_constraints[r][c] is between (r,c) and (r,c+1)
        if c < N - 1:
            h = state.h_constraints[r][c]
            right = state.grid[r][c + 1]
            if h != 0:
                if right != 0:
                    if h == 1:    # left (us) < right
                        domain = {v for v in domain if v < right}
                    else:
                        domain = {v for v in domain if v > right}
                else:
                    rd = state.domains[r][c + 1]
                    if rd:
                        if h == 1:
                            domain = {v for v in domain if v < max(rd)}
                        else:
                            domain = {v for v in domain if v > min(rd)}
        # Top neighbor: v_constraints[r-1][c] is between (r-1,c) and (r,c)
        if r > 0:
            vc = state.v_constraints[r - 1][c]
            top = state.grid[r - 1][c]
            if vc != 0:
                if top != 0:
                    if vc == 1:   # top < bottom ⇒ we (bottom) > top
                        domain = {v for v in domain if v > top}
                    else:
                        domain = {v for v in domain if v < top}
                else:
                    td = state.domains[r - 1][c]
                    if td:
                        if vc == 1:
                            domain = {v for v in domain if v > min(td)}
                        else:
                            domain = {v for v in domain if v < max(td)}
        # Bottom neighbor: v_constraints[r][c] is between (r,c) and (r+1,c)
        if r < N - 1:
            vc = state.v_constraints[r][c]
            bottom = state.grid[r + 1][c]
            if vc != 0:
                if bottom != 0:
                    if vc == 1:   # top (us) < bottom
                        domain = {v for v in domain if v < bottom}
                    else:
                        domain = {v for v in domain if v > bottom}
                else:
                    bd = state.domains[r + 1][c]
                    if bd:
                        if vc == 1:
                            domain = {v for v in domain if v < max(bd)}
                        else:
                            domain = {v for v in domain if v > min(bd)}
        return domain

    def _backtrack(self, state: State, path: List[Tuple[int, int, int]]):
        self.nodes_expanded += 1
        if state.is_complete():
            return state, path

        # MRV: choose unassigned cell with smallest domain
        best = None
        best_size = float("inf")
        for r in range(self.N):
            for c in range(self.N):
                if state.grid[r][c] == 0:
                    size = len(state.domains[r][c])
                    if 0 < size < best_size:
                        best_size = size
                        best = (r, c)
        if best is None:
            return None
        r, c = best

        for v in list(state.domains[r][c]):
            new_state = state.clone()
            new_state.grid[r][c] = v
            new_state.domains[r][c] = [v]
            guess = (r, c, v)

            ok, prop_steps = self._propagate(new_state)
            if ok:
                result = self._backtrack(new_state, path + [guess] + prop_steps)
                if result is not None:
                    return result
        return None