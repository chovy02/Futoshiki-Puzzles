#core/state.py
from typing import List, Optional, Tuple

class State:
    def __init__(
            self, 
            N: int, # Size of maze
            grid: List[List[int]], 
            h_constraints: List[List[int]], 
            v_constraints: List[List[int]], 
            domains: Optional[List[List[List[int]]]]
            ) -> None:
        self.N: int = N
        self.grid: List[List[int]] = grid # N x N
        self.h_constraints: List[List[int]] = h_constraints # N x (N - 1)
        self.v_constraints: List[List[int]] = v_constraints # (N - 1) x N

        if domains is None:
            self.domains: List[List[List[int]]] = self._initialize_domains()
        else:
            self.domains = domains

    def _initialize_domains(self) -> List[List[List[int]]]:
        domains: List[List[List[int]]] = []
        for r in range(self.N):
            row_domains: List[List[int]] = []
            for c in range(self.N):
                val = self.grid[r][c]
                if (val == 0):
                    row_domains.append(list(range(1, self.N + 1)))
                else:
                    row_domains.append([val])
            domains.append(row_domains)
        return domains
    
    def clone(self) -> 'State':
        new_grid: List[List[int]] = [row[:] for row in self.grid]
        new_domains: List[List[List[int]]] = [[col[:] for col in row] for row in self.domains]
        return State(self.N, new_grid, self.h_constraints, self.v_constraints, new_domains)
    
    def is_complete(self) -> bool:
        """Check whether a complete assignment"""
        for r in range(self.N):
            for c in range(self.N):
                if self.grid[r][c] == 0:
                    return False
        return True
    
    def assign_value(self, r: int, c: int, value: int) -> 'State':
        """Assign value to a cell and update domains"""
        new_state: 'State' = self.clone()
        new_state.grid[r][c] = value
        new_state.domains[r][c] = [value]
        return new_state
    
    def get_empty_cells(self) -> List[Tuple[int, int]]:
        empty_cells: List[Tuple[int, int]] = []
        for r in range(self.N):
            for c in range(self.N):
                if self.grid[r][c] == 0:
                    empty_cells.append((r, c))
        return empty_cells
    
    def display(self) -> None:
        for r in range(self.N):
            row_str = ""
            for c in range(self.N):
                val = self.grid[r][c]
                row_str += f"{val} "
                # Horizontal constraints
                if (c < self.N - 1):
                    h_val = self.h_constraints[r][c]
                    if h_val == 1: row_str += "< "
                    elif h_val == -1: row_str += "> "
                    else: row_str += "  "
            print(row_str)

            # Vertical constraints
            if (r < self.N - 1):
                v_str = ""
                for c in range(self.N):
                    v_val = self.v_constraints[r][c]
                    if v_val == 1: v_str += "^   "
                    elif v_val == -1: v_str += "v   "
                    else: v_str += "    "
                print(v_str)

        print("-" * 20)

    # =====
    # PREDICATE
    # =====

    def is_valid_assignment(self, r: int, c: int, v: int) -> bool:
        """Check whether an assignment is valid."""
        return (self.is_valid_row(r, v) and 
                self.is_valid_col(c, v) and 
                self.is_valid_h_constraints(r, c, v) and 
                self.is_valid_v_constraints(r, c, v))
    
    def is_valid_row(self, r: int, v: int) -> bool:
        """Check whether value v has already been assigned to row r"""
        for c in range(self.N):
            if self.grid[r][c] == v: return False
        return True
    
    def is_valid_col(self, c: int, v: int) -> bool:
        """Check whether value v has already been assigned to column c"""
        for r in range(self.N):
            if self.grid[r][c] == v: return False
        return True
    
    def is_valid_h_constraints(self, r: int, c: int, v: int) -> bool:
        """Check whether an assignment satisfies left and right constraints"""
        # Check left
        if c > 0 and self.grid[r][c - 1] != 0:
            left_v = self.grid[r][c - 1]
            rule = self.h_constraints[r][c - 1]
            if rule == 1 and not (left_v < v): return False
            if rule == -1 and not (left_v > v): return False
        # Check right
        if c < self.N - 1 and self.grid[r][c + 1] != 0:
            right_v = self.grid[r][c + 1]
            rule = self.h_constraints[r][c]
            if rule == 1 and not (v < right_v): return False
            if rule == -1 and not (v > right_v): return False
        return True
    
    def is_valid_v_constraints(self, r: int, c: int, v: int) -> bool:
        """Check whether an assignment satisfies top and bottom constraints"""
        # Check top
        if r > 0 and self.grid[r - 1][c] != 0:
            top_v = self.grid[r - 1][c]
            rule = self.v_constraints[r - 1][c]
            if rule == 1 and not (top_v < v): return False
            if rule == -1 and not (top_v > v): return False
        # Check bottom
        if r < self.N - 1 and self.grid[r + 1][c] != 0:
            bottom_v = self.grid[r + 1][c]
            rule = self.v_constraints[r][c]
            if rule == 1 and not (v < bottom_v): return False
            if rule == -1 and not (v > bottom_v): return False
        return True

    def get_pruned_domain(self, r: int, c: int) -> List[int]:
        """Prune domain of cell (r, c) using row/col uniqueness + inequality constraints."""
        domain = set(self.domains[r][c])

        # Row uniqueness
        for cc in range(self.N):
            if cc != c and self.grid[r][cc] != 0:
                domain.discard(self.grid[r][cc])
        # Column uniqueness
        for rr in range(self.N):
            if rr != r and self.grid[rr][c] != 0:
                domain.discard(self.grid[rr][c])
        # Inequality constraints
        domain = self._prune_inequality(r, c, domain)

        return sorted(domain)

    def _prune_inequality(self, r: int, c: int, domain: set) -> set:
        """Prune domain based on all 4 inequality neighbors."""
        # Left neighbor
        if c > 0 and self.h_constraints[r][c - 1] != 0:
            domain = self._prune_by_neighbor(
                domain, self.h_constraints[r][c - 1],
                self.grid[r][c - 1], self.domains[r][c - 1], is_greater=True
            )
        # Right neighbor
        if c < self.N - 1 and self.h_constraints[r][c] != 0:
            domain = self._prune_by_neighbor(
                domain, self.h_constraints[r][c],
                self.grid[r][c + 1], self.domains[r][c + 1], is_greater=False
            )
        # Top neighbor
        if r > 0 and self.v_constraints[r - 1][c] != 0:
            domain = self._prune_by_neighbor(
                domain, self.v_constraints[r - 1][c],
                self.grid[r - 1][c], self.domains[r - 1][c], is_greater=True
            )
        # Bottom neighbor
        if r < self.N - 1 and self.v_constraints[r][c] != 0:
            domain = self._prune_by_neighbor(
                domain, self.v_constraints[r][c],
                self.grid[r + 1][c], self.domains[r + 1][c], is_greater=False
            )
        return domain

    def _prune_by_neighbor(self, domain: set, sign: int, neighbor_val: int,
                           neighbor_domain: List[int], is_greater: bool) -> set:
        """Prune domain based on one inequality neighbor.
        is_greater=True means constraint says neighbor <sign> us (we are on the right/bottom side).
        is_greater=False means constraint says us <sign> neighbor (we are on the left/top side).
        """
        if is_greater:
            if neighbor_val != 0:
                if sign == 1:  return {v for v in domain if v > neighbor_val}
                else:          return {v for v in domain if v < neighbor_val}
            elif neighbor_domain:
                if sign == 1:  return {v for v in domain if v > min(neighbor_domain)}
                else:          return {v for v in domain if v < max(neighbor_domain)}
        else:
            if neighbor_val != 0:
                if sign == 1:  return {v for v in domain if v < neighbor_val}
                else:          return {v for v in domain if v > neighbor_val}
            elif neighbor_domain:
                if sign == 1:  return {v for v in domain if v < max(neighbor_domain)}
                else:          return {v for v in domain if v > min(neighbor_domain)}
        return domain