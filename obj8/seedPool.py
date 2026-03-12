import numpy as np
import random
import os

class Pool:
    def __init__(self, edge_count: int = 65536):
        self.pool = []
        self.test_count = 0
        self.coverage = np.zeros(edge_count, dtype=np.uint8)  # match uint8
        os.makedirs("interesting", exist_ok=True)

    def add_seed(self, test):
        self.pool.append(test)

    def get_seed(self) -> bytes:
        return random.choice(self.pool) 
    
    def get_coverage(self) -> float:
        if len(self.coverage) == 0:
            return 0.0
        edges_hit = np.count_nonzero(self.coverage)
        return (edges_hit / len(self.coverage)) * 100.0

    def filter(self, file, test):
        with open(file, "rb") as f:
            cov = f.read()

        cov_array = np.frombuffer(cov, dtype=np.uint8)

        if len(cov_array) != len(self.coverage):
            print(f"[!] Coverage size mismatch: got {len(cov_array)}, expected {len(self.coverage)}")
            return

        new_edges = cov_array > self.coverage
        if new_edges.any():
            self.coverage = np.maximum(self.coverage, cov_array)
            with open(f"interesting/test_{self.test_count}.bin", "wb") as f:
                f.write(test)
            self.add_seed(test)
            self.test_count += 1