#utils/file_io.py
from typing import Tuple
from core.state import State

def read_input_file(filepath: str) -> 'State':
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]

        # Line 1: N
        N: int = int(lines[0])
        current_line: int = 1

        # Grid
        grid = []
        for _ in range(N):
            row = list(map(int, lines[current_line].split(',')))
            grid.append(row)
            current_line += 1

        # Read horizontal constraints
        h_constraints = []
        for _ in range(N):
            row = list(map(int, lines[current_line].split(',')))
            h_constraints.append(row)
            current_line += 1

        # Read vertical constraints
        v_constraints = []
        for _ in range(N - 1):
            row = list(map(int, lines[current_line].split(',')))
            v_constraints.append(row)
            current_line += 1
        
        return State(N, grid, h_constraints, v_constraints, None)
