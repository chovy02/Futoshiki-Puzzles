import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from pysat.solvers import Glucose3
from utils.file_io import read_input_file
from core.knowledge_base import KnowledgeBase
from typing import List


def verify_with_pysat(input_path: str) -> None:
    # Read file input
    print(f"Reading from {input_path}...")
    state = read_input_file(input_path)
    state.display()  

    # Generate CNF
    kb = KnowledgeBase(state.N)
    clauses: List[List[int]] = kb.generate_all_clauses(state)
    print(f"Generated {len(clauses)} CNF clauses.")

    # SAT Solver 
    solver = Glucose3()
    for clause in clauses:
        solver.add_clause(clause)

    # Solve Problem
    print("Đang giải bài toán bằng PySAT...")
    is_solvable: bool = solver.solve()

    if is_solvable:
        print("=> SOLUTION FOUND\n")
        # get_model() return list of ID. 
        # If ID > 0 => assign, otherwise not assign.
        model: List[int] = solver.get_model()
        
        for ID in model:
            if ID > 0:
                r, c, v = kb.decode_var(ID)
                state.grid[r][c] = v
                

        state.display()
    else:
        print("=> NO SOLUTION!\n")

    solver.delete()  # Free Memory
