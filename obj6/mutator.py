import random
import string

class Mutator:

    def mutate(self, test_case: str) -> str:
        
        if not test_case:
            return test_case  # avoid empty string

        # Pick a random index
        i = random.randrange(len(test_case))

        # Pick a random character
        char = random.choice(string.ascii_letters + string.digits)

        # Build a new string with the mutation
        mutated = test_case[:i] + char + test_case[i+1:]
        return mutated
