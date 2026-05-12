"""
PRIME N-QUEENS "WATCHMAKER" (STRICT VERSION)
===========================================
A strictly valid 8-Queens solver using Prime-Topology Monodromy.
Primes: [11, 13, 17, 19, 23, 29, 31, 37]
"""

import numpy as np

# 1. CONFIG
PRIMES = [11, 13, 17, 19, 23, 29, 31, 37] 
N = 8

def mod_inverse(a, m):
    a = a % m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return 1

def garners_jump(current_z, target_val, prime_idx, solved_primes):
    p_target = PRIMES[prime_idx]
    M = 1
    for p in solved_primes:
        M *= p
    diff = (target_val - current_z) % p_target
    k = (diff * mod_inverse(M, p_target)) % p_target
    return k * M

def get_board(z):
    z_int = int(round(z))
    return [z_int % p for p in PRIMES]

def check_conflicts(cols):
    conflicts = 0
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if cols[i] == cols[j]: conflicts += 1
            elif abs(cols[i] - cols[j]) == abs(i - j): conflicts += 1
    return conflicts

def render_board(cols):
    res = "\n"
    for r in range(N):
        row_str = "  "
        for c in range(N):
            if cols[r] == c: row_str += " ♛ "
            else: row_str += " . "
        res += row_str + "\n"
    return res

def solve_n_queens():
    print("=" * 60)
    print("PRIME N-QUEENS TOPOLOGICAL SOLVER")
    print("=" * 60)
    
    attempts = 0
    while True:
        attempts += 1
        z = 0
        solved = []
        # (prime_index, shuffled_cols_to_try)
        initial_cols = list(range(N))
        np.random.shuffle(initial_cols)
        stack = [(0, initial_cols)]
        z_history = [0]
        
        while len(solved) < N:
            if not stack: break
            
            p_idx, available_cols = stack[-1]
            
            if not available_cols:
                # Backtrack
                stack.pop()
                if not stack: break
                solved.pop()
                z = z_history.pop()
                continue
            
            c = available_cols.pop()
            
            # Strict Conflict Check
            conflict = False
            for prev_idx in solved:
                prev_c = int(round(z)) % PRIMES[prev_idx]
                if prev_c == c or abs(prev_c - c) == abs(prev_idx - p_idx):
                    conflict = True
                    break
            
            if not conflict:
                z_history.append(z)
                if p_idx == 0:
                    z = c
                else:
                    jump = garners_jump(z, c, p_idx, [PRIMES[idx] for idx in solved])
                    z += jump
                
                solved.append(p_idx)
                if len(solved) < N:
                    next_cols = list(range(N))
                    np.random.shuffle(next_cols)
                    stack.append((p_idx + 1, next_cols))
            else:
                continue
        
        if len(solved) == N: break
        
    print(f"Solved in {attempts} topological attempts.")
    final_cols = get_board(z)
    print(f"\nFINAL MASTER COORDINATE: z = {z}")
    print(f"LOGIC EXTRACTION: {final_cols}")
    print(render_board(final_cols))
    
    # Final Verification
    conflicts = check_conflicts(final_cols)
    if conflicts == 0:
        print("🏆 SUCCESS: Valid N-Queens configuration found.")
    else:
        print(f"❌ FAILURE: {conflicts} conflicts remaining.")

if __name__ == "__main__":
    solve_n_queens()
