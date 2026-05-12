"""
PRIME-TOPOLOGY TIMETABLE SCHEDULER
==================================
Using Riemann Manifolds to resolve teacher and room conflicts.

Classes: Math, Physics, Chemistry, History, Biology
Resources: 4 Slots, 2 Rooms, 3 Teachers
"""

import numpy as np

# 1. SCHEDULING CONFIG
CLASSES = ["Math", "Physics", "Chemistry", "History", "Biology"]
TEACHERS = ["Alpha", "Alpha", "Beta", "Beta", "Gamma"] # Teacher per class
PRIMES = [11, 13, 17, 19, 23]
SLOTS = 4
ROOMS = 2

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

def decode_state(v):
    """Map a prime residue to (Slot, Room)."""
    slot = v % SLOTS
    room = v // SLOTS
    return slot, room

def get_timetable(z):
    z_int = int(round(z))
    res = []
    for i, p in enumerate(PRIMES):
        v = z_int % p
        slot, room = decode_state(v)
        res.append({
            "class": CLASSES[i],
            "teacher": TEACHERS[i],
            "slot": slot,
            "room": room
        })
    return res

def check_conflicts(timetable, current_idx):
    """
    Check if the current class (at current_idx) conflicts 
    with any previously scheduled classes.
    """
    curr = timetable[current_idx]
    
    for i in range(current_idx):
        prev = timetable[i]
        
        # Room Conflict: Same slot, same room
        if curr['slot'] == prev['slot'] and curr['room'] == prev['room']:
            return True, f"Room Conflict with {prev['class']} in Room {curr['room']} at Slot {curr['slot']}"
            
        # Teacher Conflict: Same slot, same teacher
        if curr['slot'] == prev['slot'] and curr['teacher'] == prev['teacher']:
            return True, f"Teacher Conflict: {curr['teacher']} is already teaching {prev['class']} at Slot {curr['slot']}"
            
    return False, ""

def render_timetable(z):
    tt = get_timetable(z)
    res = "\n" + "="*70 + "\n"
    res += f"{'CLASS':<12} | {'TEACHER':<10} | {'SLOT':<8} | {'ROOM':<8}\n"
    res += "-"*70 + "\n"
    for item in tt:
        res += f"{item['class']:<12} | {item['teacher']:<10} | {item['slot']:<8} | {item['room']:<8}\n"
    res += "="*70 + "\n"
    return res

# ---------------------------------------------------------
# 2. THE SYNCHRONIZER
# ---------------------------------------------------------
def synchronize_timetable():
    print("Initializing Prime-Topology Scheduler...")
    
    attempts = 0
    while True:
        attempts += 1
        z = 0
        solved = []
        
        # Potential states for each prime (residues 0-7 cover 4 slots x 2 rooms)
        # Note: Since primes are >= 11, residues 8-10 are 'invalid' (empty rooms)
        # We only want to try valid (Slot, Room) combinations
        valid_residues = list(range(SLOTS * ROOMS))
        
        # (class_index, shuffled_residues_to_try)
        initial_states = valid_residues.copy()
        np.random.shuffle(initial_states)
        stack = [(0, initial_states)]
        z_history = [0]
        
        while len(solved) < len(CLASSES):
            if not stack: break
            
            c_idx, available_v = stack[-1]
            
            if not available_v:
                # Backtrack
                stack.pop()
                if not stack: break
                solved.pop()
                z = z_history.pop()
                continue
                
            v = available_v.pop()
            
            # Temporary decode to check constraints
            slot, room = decode_state(v)
            temp_item = {
                "class": CLASSES[c_idx],
                "teacher": TEACHERS[c_idx],
                "slot": slot,
                "room": room
            }
            
            # Conflict Check against solved classes
            conflict = False
            for prev_idx in solved:
                prev_v = int(round(z)) % PRIMES[prev_idx]
                p_slot, p_room = decode_state(prev_v)
                
                # Room Conflict
                if slot == p_slot and room == p_room:
                    conflict = True; break
                # Teacher Conflict
                if slot == p_slot and TEACHERS[c_idx] == TEACHERS[prev_idx]:
                    conflict = True; break
            
            if not conflict:
                # TOPOLOGICAL JUMP
                z_history.append(z)
                if c_idx == 0:
                    z = v
                else:
                    jump = garners_jump(z, v, c_idx, [PRIMES[idx] for idx in solved])
                    z += jump
                
                solved.append(c_idx)
                if len(solved) < len(CLASSES):
                    next_v = valid_residues.copy()
                    np.random.shuffle(next_v)
                    stack.append((c_idx + 1, next_v))
            else:
                continue
                
        if len(solved) == len(CLASSES):
            break
            
    print(f"Timetable synchronized in {attempts} topological attempts.")
    print(f"Master Schedule Coordinate: z = {z}")
    print(render_timetable(z))

if __name__ == "__main__":
    synchronize_timetable()
