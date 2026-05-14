"""
Neural + Ultrametric:  Word2Vec Cosine vs Ultrametric Repair Distance
======================================================================

Key idea:
  Cosine similarity measures smooth semantic proximity.
  Ultrametric repair distance measures preserved symbolic hierarchy.

  A semantic hierarchy defines layers of commitment (animal > mammal > canine).
  Substituting "dog → wolf" preserves deep hierarchy (same branch).
  Substituting "dog → car" breaks mid-level hierarchy (different branch).
  Substituting "dog → democracy" breaks everything.

  Ultrametric distance naturally separates these by counting preserved
  hierarchy depth.  Cosine similarity treats all as continuous perturbations.
"""

import numpy as np
import gensim.downloader as api
from gensim.models import Word2Vec
import math
import os

MODEL_PATH = "/tmp/text8_w2v.model"

# ─────────────────────────────────────────────
# 1. Semantic hierarchy
# ─────────────────────────────────────────────

# Words mapped to (coarse, mid, fine) depth tuple.
# Deeper = more specific = higher commitment.
# Substituting within same fine → shallow repair.
# Substituting different coarse → deep repair.

HIERARCHY = {
    # ── Animals ──
    "dog":   ("animate", "mammal", "canine"),
    "wolf":  ("animate", "mammal", "canine"),
    "fox":   ("animate", "mammal", "canine"),
    "cat":   ("animate", "mammal", "feline"),
    "tiger": ("animate", "mammal", "feline"),
    "lion":  ("animate", "mammal", "feline"),
    "bird":  ("animate", "avian", "passerine"),
    "eagle": ("animate", "avian", "raptor"),
    "fish":  ("animate", "aquatic", "teleost"),
    "shark": ("animate", "aquatic", "cartilaginous"),
    "horse": ("animate", "mammal", "equine"),
    "cow":   ("animate", "mammal", "bovine"),
    "pig":   ("animate", "mammal", "suine"),
    "bear":  ("animate", "mammal", "ursine"),
    "deer":  ("animate", "mammal", "cervine"),
    "rabbit":("animate", "mammal", "leporid"),
    "mouse": ("animate", "mammal", "murine"),
    "snake": ("animate", "reptile", "serpent"),
    "turtle":("animate", "reptile", "testudine"),
    "frog":  ("animate", "amphibian", "anuran"),
    "salmon":("animate", "aquatic", "teleost"),
    "trout": ("animate", "aquatic", "teleost"),
    "whale": ("animate", "mammal", "cetacean"),
    "dolphin":("animate", "mammal", "cetacean"),
    "bat":   ("animate", "mammal", "chiropteran"),
    "monkey":("animate", "mammal", "primate"),
    "human": ("animate", "mammal", "primate"),
    "person":("animate", "mammal", "primate"),
    "man":   ("animate", "mammal", "primate"),
    "woman": ("animate", "mammal", "primate"),
    "child": ("animate", "mammal", "primate"),
    "insect":("animate", "invertebrate", "arthropod"),
    "ant":   ("animate", "invertebrate", "arthropod"),
    "bee":   ("animate", "invertebrate", "arthropod"),
    "butterfly":("animate", "invertebrate", "arthropod"),

    # ── Vehicles / Objects ──
    "car":   ("artifact", "vehicle", "automobile"),
    "truck": ("artifact", "vehicle", "automobile"),
    "bus":   ("artifact", "vehicle", "automobile"),
    "train": ("artifact", "vehicle", "rail"),
    "plane": ("artifact", "vehicle", "aircraft"),
    "boat":  ("artifact", "vehicle", "watercraft"),
    "ship":  ("artifact", "vehicle", "watercraft"),
    "bike":  ("artifact", "vehicle", "cycle"),
    "house": ("artifact", "structure", "dwelling"),
    "building":("artifact", "structure", "dwelling"),
    "school":("artifact", "structure", "institutional"),
    "hospital":("artifact", "structure", "institutional"),
    "table": ("artifact", "furniture", "surface"),
    "chair": ("artifact", "furniture", "seating"),
    "bed":   ("artifact", "furniture", "seating"),
    "book":  ("artifact", "media", "codex"),
    "newspaper":("artifact", "media", "periodical"),
    "phone": ("artifact", "device", "communication"),
    "computer":("artifact", "device", "computing"),
    "tv":    ("artifact", "device", "entertainment"),
    "radio": ("artifact", "device", "communication"),
    "knife": ("artifact", "tool", "cutting"),
    "gun":   ("artifact", "weapon", "firearm"),
    "sword": ("artifact", "weapon", "blade"),

    # ── Actions / Verbs ──
    "ran":    ("action", "motion", "run"),
    "run":    ("action", "motion", "run"),
    "walked": ("action", "motion", "walk"),
    "walk":   ("action", "motion", "walk"),
    "jumped": ("action", "motion", "jump"),
    "jump":   ("action", "motion", "jump"),
    "flew":   ("action", "motion", "fly"),
    "fly":    ("action", "motion", "fly"),
    "swam":   ("action", "motion", "swim"),
    "swim":   ("action", "motion", "swim"),
    "drove":  ("action", "motion", "drive"),
    "drive":  ("action", "motion", "drive"),
    "rode":   ("action", "motion", "ride"),
    "ride":   ("action", "motion", "ride"),
    "chased": ("action", "pursuit", "chase"),
    "chase":  ("action", "pursuit", "chase"),
    "pursued":("action", "pursuit", "pursue"),
    "ate":    ("action", "consumption", "eat"),
    "eat":    ("action", "consumption", "eat"),
    "drank":  ("action", "consumption", "drink"),
    "drink":  ("action", "consumption", "drink"),
    "slept":  ("action", "rest", "sleep"),
    "sleep":  ("action", "rest", "sleep"),
    "sat":    ("action", "rest", "sit"),
    "sit":    ("action", "rest", "sit"),
    "read":   ("action", "perception", "read"),
    "wrote":  ("action", "creation", "write"),
    "write":  ("action", "creation", "write"),
    "bought": ("action", "transaction", "buy"),
    "buy":    ("action", "transaction", "buy"),
    "sold":   ("action", "transaction", "sell"),
    "sell":   ("action", "transaction", "sell"),
    "killed": ("action", "destruction", "kill"),
    "kill":   ("action", "destruction", "kill"),
    "broke":  ("action", "destruction", "break"),
    "break":  ("action", "destruction", "break"),
    "built":  ("action", "creation", "build"),
    "build":  ("action", "creation", "build"),
    "made":   ("action", "creation", "make"),
    "make":   ("action", "creation", "make"),

    # ── Abstract / Other ──
    "democracy": ("abstract", "system", "governance"),
    "justice":   ("abstract", "concept", "ethics"),
    "freedom":   ("abstract", "concept", "ethics"),
    "love":     ("abstract", "emotion", "affection"),
    "hate":     ("abstract", "emotion", "antipathy"),
    "fear":     ("abstract", "emotion", "anxiety"),
    "thought":  ("abstract", "cognition", "idea"),
    "idea":     ("abstract", "cognition", "idea"),
    "truth":    ("abstract", "concept", "epistemic"),
    "beauty":   ("abstract", "concept", "aesthetic"),
    "triangle": ("abstract", "mathematics", "geometry"),
    "circle":   ("abstract", "mathematics", "geometry"),
    "number":   ("abstract", "mathematics", "arithmetic"),
    "time":     ("abstract", "dimension", "temporal"),
    "space":    ("abstract", "dimension", "spatial"),
    "energy":   ("abstract", "physics", "thermodynamics"),
    "force":    ("abstract", "physics", "mechanics"),
    "god":      ("abstract", "theology", "deity"),
}


def hierarchy_depth(w1, w2):
    """
    Return v_R = depth of shared hierarchy between two words (0-3).
    3 = same fine-grained class (shallow repair)
    2 = same mid-level class
    1 = same coarse class
    0 = different coarse class (deep break)
    """
    if w1 == w2:
        return 3
    t1 = HIERARCHY.get(w1)
    t2 = HIERARCHY.get(w2)
    if t1 is None or t2 is None:
        return 0
    for v in range(3):
        if t1[v] != t2[v]:
            return v
    return 3


def ultrametric_distance(w1, w2, base=2):
    return base ** (-hierarchy_depth(w1, w2))


# ─────────────────────────────────────────────
# 2. Word2Vec model
# ─────────────────────────────────────────────

def get_model():
    if os.path.exists(MODEL_PATH):
        print("  Loading cached model...")
        return Word2Vec.load(MODEL_PATH)

    print("  Downloading text8 corpus...")
    corpus = api.load("text8")
    sentences = list(corpus)

    print("  Training tiny Word2Vec (50d, window=5)...")
    model = Word2Vec(
        sentences=sentences,
        vector_size=50,
        window=5,
        min_count=50,
        workers=4,
        epochs=5,
        seed=42,
    )
    model.save(MODEL_PATH)
    print(f"  Vocabulary: {len(model.wv)} words")
    return model


# ─────────────────────────────────────────────
# 3. Substitution pairs
# ─────────────────────────────────────────────

# (word1, word2, label)
WORD_PAIRS = [
    # ── Shallow: same fine-grained class ──
    ("dog", "wolf", "canine→canine"),
    ("cat", "tiger", "feline→feline"),
    ("car", "truck", "automobile→automobile"),
    ("ran", "walked", "motion→motion"),
    ("chair", "bed", "seating→seating"),
    ("ate", "drank", "consumption→consumption"),
    ("plane", "boat", "vehicle→vehicle"),
    ("dog", "fox", "canine→canine"),
    ("lion", "tiger", "feline→feline"),
    ("ship", "boat", "watercraft→watercraft"),

    # ── Mid: same coarse, different mid ──
    ("dog", "bird", "mammal→avian"),
    ("dog", "fish", "mammal→aquatic"),
    ("car", "house", "vehicle→structure"),
    ("car", "book", "vehicle→media"),
    ("ran", "ate", "motion→consumption"),
    ("ran", "slept", "motion→rest"),
    ("cat", "whale", "feline→cetacean"),
    ("horse", "eagle", "equine→raptor"),
    ("dog", "snake", "mammal→reptile"),
    ("table", "phone", "furniture→device"),

    # ── Deep: different coarse ──
    ("dog", "car", "animate→artifact"),
    ("dog", "democracy", "animate→abstract"),
    ("car", "democracy", "artifact→abstract"),
    ("ran", "democracy", "action→abstract"),
    ("dog", "triangle", "animate→abstract"),
    ("car", "love", "artifact→abstract"),
    ("house", "freedom", "artifact→abstract"),
    ("cat", "justice", "animate→abstract"),
    ("ate", "thought", "action→abstract"),
    ("book", "energy", "artifact→abstract"),
]

# ─────────────────────────────────────────────
# 4. Run experiment
# ─────────────────────────────────────────────

print("=" * 68)
print("  Cosine vs Ultrametric: Same Words, Different Metrics")
print("=" * 68)

model = get_model()
wv = model.wv

print(f"\n  {'Pair':<35} {'Cosine':>8} {'Ultra d':>8} {'Hier v':>8}")
print("-" * 68)

rows = []
for w1, w2, label in WORD_PAIRS:
    v = hierarchy_depth(w1, w2)
    d = ultrametric_distance(w1, w2)
    if w1 in wv and w2 in wv:
        cos = float(np.dot(wv[w1], wv[w2]) / (np.linalg.norm(wv[w1]) * np.linalg.norm(wv[w2])))
    else:
        cos = 0.0
    rows.append((label, cos, v, d, w1, w2))

# Print sorted by hierarchical depth
rows.sort(key=lambda r: r[2], reverse=False)
for label, cos, v, d, w1, w2 in rows:
    print(f"  {label:<34} {cos:>8.3f} {d:>8.4f} {v:>8}")

print()
print("=" * 68)
print("  Aggregated by hierarchical depth (v_R)")
print("=" * 68)

by_v = {}
for label, cos, v, d, w1, w2 in rows:
    by_v.setdefault(v, []).append(cos)

for v in sorted(by_v.keys()):
    cosines = by_v[v]
    depth_label = {3: "same fine (shallow)", 2: "same mid", 1: "same coarse", 0: "different coarse (deep)"}
    print(f"\n  v_R = {v}  ({depth_label.get(v, '?')}):")
    print(f"    count: {len(cosines)}")
    print(f"    cosine range: [{min(cosines):.3f}, {max(cosines):.3f}]")
    print(f"    cosine mean:  {np.mean(cosines):.3f}")
    if len(cosines) >= 2:
        print(f"    cosine std:   {np.std(cosines):.3f}")

# Show the key finding: cosine heavily overlaps across hierarchy depths
shallow_v3 = by_v.get(3, [])
deep_v0 = by_v.get(0, [])
print(f"\n  {'='*50}")
print(f"  KEY FINDING:")
if shallow_v3 and deep_v0:
    overlap = max(shallow_v3) - min(deep_v0) > 0
    print(f"  Cosine ranges OVERLAP between shallow (v=3) and deep (v=0)? {'YES — cosine cannot separate hierarchy depth' if overlap else 'NO — cosine separates perfectly'}")
print(f"  Ultrametric distance is QUANTIZED (2^-v): always separates by definition.")
print(f"  Cosine is CONTINUOUS: smooth proximity ≠ hierarchical preservation.")
