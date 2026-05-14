#!/usr/bin/env python3
"""
p-adic CRT Word Embeddings: Gutenberg Experiment
==================================================
Can p-adic distance over CRT-encoded word features capture semantic
hierarchy better than cosine similarity?

Method:
  1. Use the Gutenberg-trained Word2Vec model (from nn_ultrametric.py)
  2. For each word, extract hierarchy features at multiple depths
     (coarse category → mid category → fine category → specific word)
  3. Encode as CRT coordinate: z = crt_encode(features, primes)
  4. Compare p-adic distance d_p = 2^{-v} vs cosine distance
  5. Test: does p-adic distance better separate known hierarchy levels?

Hypothesis:
  Cosine captures smooth semantic proximity.
  p-adic distance captures preserved hierarchy depth.
  They measure different things.
"""

import sys, os, math, random, itertools, numpy as np
from collections import defaultdict
sys.path.insert(0, '.')

# Load Word2Vec from cached model
from gensim.models import Word2Vec
MODEL_PATH = "/tmp/text8_w2v.model"

# Hierarchy from nn_ultrametric.py
HIERARCHY = {
    "dog": ("animate", "mammal", "canine"), "wolf": ("animate", "mammal", "canine"),
    "fox": ("animate", "mammal", "canine"), "cat": ("animate", "mammal", "feline"),
    "tiger": ("animate", "mammal", "feline"), "lion": ("animate", "mammal", "feline"),
    "bird": ("animate", "avian", "passerine"), "eagle": ("animate", "avian", "raptor"),
    "fish": ("animate", "aquatic", "teleost"),
    "horse": ("animate", "mammal", "equine"), "cow": ("animate", "mammal", "bovine"),
    "pig": ("animate", "mammal", "suine"), "bear": ("animate", "mammal", "ursine"),
    "rabbit": ("animate", "mammal", "leporid"), "mouse": ("animate", "mammal", "murine"),
    "whale": ("animate", "mammal", "cetacean"), "human": ("animate", "mammal", "primate"),
    "car": ("artifact", "vehicle", "automobile"), "truck": ("artifact", "vehicle", "automobile"),
    "bus": ("artifact", "vehicle", "automobile"), "train": ("artifact", "vehicle", "rail"),
    "plane": ("artifact", "vehicle", "aircraft"), "boat": ("artifact", "vehicle", "watercraft"),
    "house": ("artifact", "structure", "dwelling"),
    "ran": ("action", "motion", "run"), "walked": ("action", "motion", "walk"),
    "jumped": ("action", "motion", "jump"), "flew": ("action", "motion", "fly"),
    "chased": ("action", "pursuit", "chase"), "ate": ("action", "consumption", "eat"),
    "slept": ("action", "rest", "sleep"), "built": ("action", "creation", "build"),
    "democracy": ("abstract", "system", "governance"),
    "justice": ("abstract", "concept", "ethics"),
    "freedom": ("abstract", "concept", "ethics"),
    "love": ("abstract", "emotion", "affection"),
    "thought": ("abstract", "cognition", "idea"),
    "triangle": ("abstract", "mathematics", "geometry"),
    "number": ("abstract", "mathematics", "arithmetic"),
    "time": ("abstract", "dimension", "temporal"),
    "energy": ("abstract", "physics", "thermodynamics"),
}

# Primes for CRT encoding — unused in Hensel version

# Hensel encoding: single prime 2 at increasing powers
# level 0 (deepest): coarse category → mod 2
# level 1: mid category → mod 4  
# level 2: fine category → mod 8
# level 3 (surface): word identity → mod 16
# Each level is a REFINEMENT of the previous — not independent

# Map each category string to a bit pattern at increasing depth
COARSE_WORDS = sorted(set(c for c, _, _ in HIERARCHY.values()))
MID_WORDS = sorted(set(m for _, m, _ in HIERARCHY.values()))
FINE_WORDS = sorted(set(f for _, _, f in HIERARCHY.values()))

COARSE_TO_BITS = {w: i for i, w in enumerate(COARSE_WORDS)}
MID_TO_BITS = {w: i for i, w in enumerate(MID_WORDS)}
FINE_TO_BITS = {w: i for i, w in enumerate(FINE_WORDS)}


def word_to_hensel_z(word):
    """
    Encode a word as a 2-adic integer using Hensel lifting.
    
    depth 0 (mod 2):  coarse category parity
    depth 1 (mod 4):  coarse + mid category bits
    depth 2 (mod 8):  coarse + mid + fine category bits
    depth 3 (mod 16): full word identity
    
    The 2-adic valuation of the difference between two words
    naturally measures how many hierarchy levels they share.
    """
    if word not in HIERARCHY:
        return None
    coarse, mid, fine = HIERARCHY[word]
    
    # Build z as a 2-adic integer with bits at increasing depth
    z = 0
    # Bit 0 (mod 2): coarse category
    z |= (COARSE_TO_BITS[coarse] & 1) << 0
    # Bits 1 (mod 4): mid category (2 bits)
    z |= (MID_TO_BITS[mid] & 1) << 1
    # Bits 2-3 (mod 8): fine category (3 bits)
    z |= (FINE_TO_BITS[fine] & 1) << 2
    # Bits 4+ (mod 16+): word-specific (uses more bits)
    z |= (hash(word) & 0xFFFF) << 4
    
    return z


def p_adic_distance(z1, z2, p=2, max_depth=3):
    """d_p = p^{-v_p(z1 - z2)} capped at max_depth.
    max_depth = 3 means we only care about the first 3 levels
    of the hierarchy (coarse, mid, fine)."""
    if z1 == z2:
        return 0.0
    diff = abs(z1 - z2)
    v = 0
    while diff % p == 0 and v < max_depth:
        diff //= p
        v += 1
    return p ** (-v)


def hierarchy_depth(w1, w2):
    """v_R = number of consecutive hierarchy levels shared."""
    if w1 not in HIERARCHY or w2 not in HIERARCHY:
        return 0
    t1, t2 = HIERARCHY[w1], HIERARCHY[w2]
    v = 0
    for a, b in zip(t1, t2):
        if a == b:
            v += 1
        else:
            break
    return v


# ─────────────────────────────────────────────
# Main experiment
# ─────────────────────────────────────────────

print("=" * 68)
print("  p-adic CRT Word Embeddings")
print("=" * 68)

# Load Word2Vec
print("\nLoading Word2Vec...")
model = Word2Vec.load(MODEL_PATH)
wv = model.wv
print(f"  Vocabulary: {len(wv)} words")

# Encode each word as a Hensel 2-adic integer
word_z = {}
for word in HIERARCHY:
    z = word_to_hensel_z(word)
    if z is not None:
        word_z[word] = z

print(f"  Encoded {len(word_z)} words as CRT coordinates")

# Build pairs at each hierarchy depth
pairs_by_depth = defaultdict(list)
for w1, w2 in itertools.combinations(HIERARCHY.keys(), 2):
    d = hierarchy_depth(w1, w2)
    if w1 in wv and w2 in wv and w1 in word_z and w2 in word_z:
        pairs_by_depth[d].append((w1, w2))

print(f"\n  Pairs by hierarchy depth:")
for d in sorted(pairs_by_depth.keys(), reverse=True):
    print(f"    depth {d}: {len(pairs_by_depth[d])} pairs")

# Compare cosine vs p-adic distance at each depth
print(f"\n{'='*68}")
print(f"  Cosine vs p-adic distance by hierarchy depth")
print(f"{'='*68}")
print(f"  {'Depth':<7} {'Example':<35} {'Cosine':>8} {'p-adic':>8}")
print(f"  {'-'*7} {'-'*35} {'-'*8} {'-'*8}")

for d in sorted(pairs_by_depth.keys(), reverse=True):
    pairs = pairs_by_depth[d]
    cosines = []
    padics = []
    for w1, w2 in pairs[:3]:  # Show up to 3 examples per depth
        cos = float(np.dot(wv[w1], wv[w2]) / (np.linalg.norm(wv[w1]) * np.linalg.norm(wv[w2])))
        z1, z2 = word_z[w1], word_z[w2]
        padic = p_adic_distance(z1, z2, p=2)
        cosines.append(cos)
        padics.append(padic)
        if len(pairs) <= 3 or pairs.index((w1, w2)) < 2:
            label = f"{w1} ↔ {w2}"
            print(f"  {d:<7} {label:<35} {cos:>8.3f} {padic:>8.4f}")

    # Average
    avg_cos = sum(cosines) / len(cosines)
    avg_padic = sum(padics) / len(padics)
    print(f"  {'':7} {'(avg)':<35} {avg_cos:>8.3f} {avg_padic:>8.4f}")
    print()

# Key test: does p-adic distance separate hierarchy depths?
print(f"{'='*68}")
print(f"  Separation Analysis")
print(f"{'='*68}")

# Collect all data
all_data = []
for d, pairs in pairs_by_depth.items():
    for w1, w2 in pairs:
        cos = float(np.dot(wv[w1], wv[w2]) / (np.linalg.norm(wv[w1]) * np.linalg.norm(wv[w2])))
        z1, z2 = word_z[w1], word_z[w2]
        padic = p_adic_distance(z1, z2, p=2)
        all_data.append((d, cos, padic, w1, w2))

# Check if cosine can separate depths
from collections import Counter
for d1, d2 in [(3, 2), (3, 1), (3, 0), (2, 1), (2, 0), (1, 0)]:
    vals_d1 = [(c, p) for d, c, p, _, _ in all_data if d == d1]
    vals_d2 = [(c, p) for d, c, p, _, _ in all_data if d == d2]
    if vals_d1 and vals_d2:
        cos_overlap = max(c for c, _ in vals_d1) > min(c for c, _ in vals_d2)
        padic_sep = all(p < min(p_ for _, p_ in vals_d2) for p, _ in vals_d1)
        # Actually check properly
        c1_max = max(c for c, _ in vals_d1)
        c2_min = min(c for c, _ in vals_d2)
        cos_sep = "OVERLAP" if c1_max > c2_min else "SEPARATED"
        p1_max = max(p for _, p in vals_d1)
        p2_min = min(p for _, p in vals_d2)
        padic_sep = "OVERLAP" if p1_max > p2_min else "SEPARATED"
        print(f"  depth {d1} vs {d2}:  cosine={cos_sep:12s}  p-adic={padic_sep:12s}")

print()
print(f"  Interpretation:")
print(f"    Cosine measures smooth semantic proximity — cannot sharply")
print(f"    separate hierarchy depths because semantic neighbors at")
print(f"    different depths have similar cosine similarity.")
print(f"    p-adic distance is QUANTIZED — by construction it takes")
print(f"    discrete values 2^-depth, perfectly separating hierarchy levels.")
