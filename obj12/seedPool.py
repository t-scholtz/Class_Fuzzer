import numpy as np
import mmap
import random
import os

class Pool:
    def __init__(self, shared_mem: mmap.mmap, edge_count: int = 65536,):
        self.pool = []
        self.pool_index = 0 
        self.test_count = 0
        self.edge_count = edge_count  # store for use in filter
        self.coverage = np.zeros(edge_count, dtype=np.uint8)
        self.cov_buffer = np.zeros(edge_count, dtype=np.uint8)  # reusable buffer
        self.cov_mm = shared_mem
        os.makedirs("interesting", exist_ok=True)

    def add_seed(self, test):
        self.pool.append(test)

    def get_seed(self) -> bytes:
        seed = self.pool[self.pool_index % len(self.pool)]
        self.pool_index += 1
        return seed

    def get_coverage(self) -> float:
        if len(self.coverage) == 0:
            return 0.0
        edges_hit = np.count_nonzero(self.coverage)
        return (edges_hit / len(self.coverage)) * 100.0

    def get_edges_found(self) -> int:
        return np.count_nonzero(self.coverage)

    def filter(self, test: bytes):
        # Read into reusable buffer — no new allocation
        self.cov_mm.seek(0)
        raw = self.cov_mm.read(self.edge_count)

        # Guard against unexpected size
        if len(raw) != self.edge_count:
            print(f"[!] Coverage size mismatch: got {len(raw)}, expected {self.edge_count}")
            return

        # Copy into pre-allocated buffer instead of allocating a new array
        np.copyto(self.cov_buffer, np.frombuffer(raw, dtype=np.uint8))

        new_edges = self.cov_buffer > self.coverage
        if new_edges.any():
            np.maximum(self.coverage, self.cov_buffer, out=self.coverage)  # write back into existing array
            with open(f"interesting/test_{self.test_count}.bin", "wb") as f:
                f.write(test)
            self.add_seed(test)
            self.test_count += 1