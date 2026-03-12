"""
mutator.py
Simputer mutator class
"""
import random

class Mutator:
    def mutate(self, test_case: bytes) -> bytes:
        if not test_case:
            return test_case

        data = bytearray(test_case)   # make it mutable
        i = random.randrange(len(data))
        data[i] = data[i] = random.randint(0, 255) #return a random byte

        return bytes(data)
