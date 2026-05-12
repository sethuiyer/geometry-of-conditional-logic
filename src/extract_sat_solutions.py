import numpy as np

PRIMES = [2, 3, 5, 7] # x1, x2, x3, x4
COORDINATES = [17, 18, 32, 38, 53, 67, 68, 73, 102, 108, 128, 137, 138, 143, 158, 193, 198]

def extract_logic(z):
    # Map residue to Boolean: 1 is True, 0 is False. 
    # (Residues > 1 are topological "ghost" states that satisfied the waves)
    return [z % p for p in PRIMES]

print(f"{'Coord (z)':<10} | {'x1 (p=2)':<8} | {'x2 (p=3)':<8} | {'x3 (p=5)':<8} | {'x4 (p=7)':<8}")
print("-" * 55)

for z in COORDINATES:
    logic = extract_logic(z)
    # We treat 1 as True, and anything else as False for the sake of the SAT problem
    bool_logic = [val == 1 for val in logic]
    formatted = [f"{'T' if b else 'F'} ({v})" for b, v in zip(bool_logic, logic)]
    print(f"{z:<10} | {formatted[0]:<8} | {formatted[1]:<8} | {formatted[2]:<8} | {formatted[3]:<8}")

# Verify one: z=17
# Clause 1: (x1 OR NOT x2 OR x3)
# z=17 -> x1=1 (T), x2=2 (F), x3=2 (F)
# (T OR NOT F OR F) -> (T OR T OR F) -> TRUE
