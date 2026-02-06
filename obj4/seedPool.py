import numpy as np
import random

class Pool:
    def __init__(self, edge_count: int = 65536 ):
        """Initialize the Seed Pool"""
        self.pool = []
        with open("application_details.bin", "rb") as f:
            edge_count = int.from_bytes(f.read(4), byteorder="little")
            print(f"There are {edge_count} edges found")
        self.coverage = np.zeros(edge_count, dtype=bool)

    def add_seed(self, test):
        self.pool.append(test)

    def get_seed(self) -> str:
        return random.choice(list(self.pool))
    
    def filter(self, file, test):
        #take in bit map
        #extract coverage - in new edges are found update coverage and add to pool
        with open(file, "rb") as f:
            cov = f.read()
            flag = False
            new_edges=[]
            for i in range(len(cov)):
                if cov[i] and not self.coverage[i]:
                    self.coverage[i] = True
                    flag=True
                    new_edges.append(i)
        if flag:
            print(f"Adding {test} to pool!! {new}")
            self.add_seed(test)