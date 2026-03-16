"""
mutator.py
Simputer mutator class
"""
import random

class Mutator:
    def __init__(self, size: int = 4048):
        self.size = size
        self.buffer = bytearray(size)

    def mutate(self, test_case: bytes) -> bytes:
        n = len(test_case)
        self.buffer[:n] = test_case
        self.buffer[random.randrange(n)] = random.randint(0, 255)
        return bytes(self.buffer[:n])


    def mutate_big(self, test_case: bytes) -> bytes:
        n = len(test_case)
        self.buffer[:n] = test_case
        for _ in range(100):
            self.buffer[random.randrange(n)] = random.randint(0, 255)
        return bytes(self.buffer[:n])

    def mutate_huge(self, test_case: bytes) -> bytes:
        n = len(test_case)
        self.buffer[:n] = test_case
        for _ in range(1000):
            self.buffer[random.randrange(n)] = random.randint(0, 255)
        return bytes(self.buffer[:n])
