
import os
import time
import tracemalloc
from typing import Optional


from utils.file_io import read_input_file
from solvers.backward_chaining import BackwardChainingSolver
from core.state import State
from solvers.AStar1Solver import AStar1Solver
from solvers.AStar2Solver import AStar2Solver
from solvers.AStar3Solver import AStar3Solver

def run_test(input_path: str) -> None:
    print(f"=== ĐANG CHẠY TEST CASE: {input_path} ===")
    
    # 1. Khởi tạo trạng thái từ file
    try:
        initial_state: State = read_input_file(input_path)
        print("Lưới ban đầu:")
        initial_state.display()
    except FileNotFoundError:
        print(f"[LỖI] Không tìm thấy file: {input_path}")
        return

    # 2. Khởi tạo thuật toán Backward Chaining
    solver = AStar3Solver(initial_state)

    # 3. Bắt đầu đo lường hiệu năng (Chuẩn bị số liệu cho Báo cáo)
    tracemalloc.start()
    start_time: float = time.perf_counter()

    # 4. Thực thi giải thuật
    solution: Optional[State] = solver.solve()

    # 5. Dừng đo lường
    end_time: float = time.perf_counter()
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 6. Xử lý và in kết quả
    if solution is not None:
        print("=> TÌM THẤY LỜI GIẢI THÀNH CÔNG!")
        solution.display()
    else:
        print("=> BÀI TOÁN VÔ NGHIỆM!")

    # 7. In thông số thống kê để vẽ biểu đồ
    time_taken: float = end_time - start_time
    memory_mb: float = peak_memory / (1024 * 1024)
    
    print("--- THỐNG KÊ HIỆU NĂNG ---")
    print(f"- Thuật toán       : Backward Chaining (SLD Resolution)")
    print(f"- Thời gian chạy   : {time_taken:.5f} giây")
    print(f"- Bộ nhớ đỉnh (RAM): {memory_mb:.5f} MB")
    print(f"- Số node mở rộng  : {solver.nodes_expanded} nodes")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    # Đường dẫn tương đối từ file main.py (trong thư mục Source) trỏ ra thư mục Inputs
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    test_file_01: str = os.path.join(BASE_DIR, "Inputs", "input-45.txt")
    run_test(test_file_01)
    
    # Bạn có thể bỏ comment đoạn dưới đây để chạy một lúc nhiều test case
    # test_files = [f"../Inputs/input-{str(i).zfill(2)}.txt" for i in range(1, 11)]
    # for file in test_files:
    #     run_test(file)