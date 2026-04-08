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

