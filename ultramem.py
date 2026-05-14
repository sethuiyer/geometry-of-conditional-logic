"""
UltraMeM — Ultrametric Memory Module
======================================

A structured retrieval and repair layer that ranks memories by preserved
hierarchy depth, not just semantic similarity.

Architecture:
  - Hierarchical feature extraction (domain → entities → deps → content → surface)
  - CRT encoding of hierarchy levels into a single coordinate z
  - Ultrametric distance d_R = base^{-v_R} where v_R = preserved levels
  - Memory storage with commit/rollback semantics
  - Hybrid mode: embedding pre-filter + ultrametric rerank

Usage:
    from ultramem import UltraMeM, TextFeatureExtractor

    mem = UltraMeM(hierarchy_levels=5, primes=[2,3,5,7,11])
    extractor = TextFeatureExtractor()

    mem.store("doc1", extractor("The dog chased the cat"))
    mem.store("doc2", extractor("The wolf hunted the rabbit"))

    results = mem.query(extractor("The fox chased the mouse"), top_k=5)
    for d_R, v_R, key in results:
        print(f"d_R={d_R:.3f} v_R={v_R} key={key}")
"""

import math
import numpy as np
from collections import Counter, defaultdict
from typing import List, Tuple, Optional, Dict, Any, Callable


# ─────────────────────────────────────────────
# CRT encoding / decoding
# ─────────────────────────────────────────────

def _crt_encode(values: List[int], moduli: List[int]) -> int:
    """Garner reconstruction.  values[i] in [0, moduli[i])."""
    n = len(moduli)
    v = [0] * n
    v[0] = values[0] % moduli[0]
    for i in range(1, n):
        t = values[i] % moduli[i]
        for j in range(i):
            t -= v[j] * math.prod(moduli[:j])
        inv = pow(math.prod(moduli[:i]), -1, moduli[i])
        v[i] = t * inv % moduli[i]
    z = 0
    for i in range(n):
        z += v[i] * math.prod(moduli[:i])
    return z


def _crt_decode(z: int, moduli: List[int]) -> List[int]:
    return [z % m for m in moduli]


def _crt_jump(z: int, target_idx: int, target_val: int,
              shield_indices: List[int], moduli: List[int]) -> int:
    """z' = z + k*M preserving all shielded residues."""
    M = 1
    for idx in shield_indices:
        M *= moduli[idx]
    p_t = moduli[target_idx]
    k = ((target_val - z) * pow(M % p_t, -1, p_t)) % p_t
    return z + k * M


def _repair_valuation(z1: int, z2: int, moduli: List[int]) -> int:
    """Number of leading moduli where residues agree."""
    v = 0
    for m in moduli:
        if (z1 - z2) % m == 0:
            v += 1
        else:
            break
    return v


# ─────────────────────────────────────────────
# Feature comparison helpers
# ─────────────────────────────────────────────

def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _jaccard_from_counter(c1: Counter, c2: Counter) -> float:
    return _jaccard(set(c1.keys()), set(c2.keys()))


# ─────────────────────────────────────────────
# Built-in text feature extractor
# ─────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "is", "was", "are", "were", "it", "its",
    "this", "that", "of", "in", "on", "at", "to", "for",
    "and", "or", "but", "not", "no", "be", "been", "with",
    "from", "by", "as", "have", "has", "had", "do", "does",
    "did", "will", "would", "can", "could", "shall", "should",
    "may", "might", "i", "you", "he", "she", "we", "they",
    "me", "him", "her", "us", "them", "my", "your", "his",
    "its", "our", "their", "what", "which", "who", "whom",
    "when", "where", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "so", "than", "too", "very", "just", "also",
    "up", "down", "out", "into", "over", "under", "after",
}


class TextFeatureExtractor:
    """
    Extract hierarchical feature sets from text.

    Levels (0 = deepest):
      0: Domain — top content words (nouns, longest terms)
      1: Role structure — bigram patterns (adj-noun, verb-noun)
      2: Content — content words (non-stop, >3 chars)
      3: Surface — all tokens (with stops, normalized)
    """

    def __init__(self, use_spacy: bool = False):
        self.use_spacy = use_spacy
        self._nlp = None
        if use_spacy:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")

    def __call__(self, text: str) -> Dict[str, Any]:
        if self._nlp:
            return self._extract_spacy(text)
        return self._extract_fallback(text)

    def _extract_spacy(self, text: str) -> Dict[str, Any]:
        doc = self._nlp(text[:100000])
        tokens = [t.text.lower() for t in doc if not t.is_punct and not t.is_space]
        lemmas = [t.lemma_.lower() for t in doc
                  if not t.is_punct and not t.is_space]
        content = [t.lemma_.lower() for t in doc
                   if t.pos_ in ("NOUN", "VERB", "ADJ", "ADV")
                   and t.lemma_.lower() not in STOPWORDS]
        bigrams = [f"{doc[i].lemma_}_{doc[i+1].lemma_}"
                   for i in range(len(doc)-1)
                   if not doc[i].is_punct and not doc[i+1].is_punct]
        entities = [ent.label_ for ent in doc.ents]
        return {
            "feature_sets": {
                0: set(content[:10]),        # domain: top content
                1: set(bigrams[:15]),        # role: bigram patterns
                2: set(content),              # content: all content words
                3: set(tokens[:30]),          # surface: all tokens
            },
            "tokens": tokens,
            "content": content,
        }

    def _extract_fallback(self, text: str) -> Dict[str, Any]:
        words = text.lower().split()
        bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)]
        content = [w for w in words if len(w) > 3 and w not in STOPWORDS]
        return {
            "feature_sets": {
                0: set(content[:5]),          # domain: top content
                1: set(bigrams[:10]),         # role: bigram patterns
                2: set(content),               # content: all content words
                3: set(words[:30]),            # surface: all tokens
            },
            "tokens": words,
            "content": content,
        }


# ─────────────────────────────────────────────
# UltraMeM — main class
# ─────────────────────────────────────────────

DEFAULT_THRESHOLDS = [0.05, 0.05, 0.05, 0.0]


class UltraMeM:
    """
    Ultrametric Memory Module.

    Stores memories indexed by hierarchical feature sets and retrieves them
    by preserved structure depth, not semantic similarity.

    Each memory has feature sets at multiple hierarchy levels (0 = deepest).
    v_R(query, memory) = number of leading levels where Jaccard similarity
    between feature sets meets a threshold.

    Parameters:
        n_levels: hierarchy depth (default 4)
        thresholds: per-level Jaccard thresholds for v_R computation
        base: base for ultrametric distance d = base^{-v}
        embedder: optional function text → vector for hybrid retrieval
    """

    def __init__(
        self,
        n_levels: int = 4,
        thresholds: Optional[List[float]] = None,
        base: float = 2.0,
        embedder: Optional[Callable] = None,
    ):
        self.n_levels = n_levels
        self.thresholds = thresholds or DEFAULT_THRESHOLDS[:n_levels]
        self.base = base
        self.embedder = embedder

        # Storage: key → {feature_sets, metadata, embedding}
        self._store: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []

    # ── Core operations ──

    def store(self, key: str, features: Dict[str, Any],
              metadata: Optional[Dict] = None) -> None:
        """Store a memory.

        features must contain 'feature_sets' — dict of level → set.
        """
        fs = features.get("feature_sets", {})
        assert len(fs) >= self.n_levels, \
            f"Need feature_sets for {self.n_levels} levels, got {len(fs)}"

        embedding = None
        if self.embedder and "tokens" in features:
            embedding = self.embedder(" ".join(features["tokens"]))

        self._store[key] = {
            "feature_sets": fs,
            "features": features,
            "metadata": metadata or {},
            "embedding": embedding,
        }

    def delete(self, key: str) -> bool:
        return bool(self._store.pop(key, None))

    def query(
        self,
        features: Dict[str, Any],
        top_k: int = 10,
        mode: str = "ultrametric",
        embed_top_k: int = 50,
    ) -> List[Tuple[float, int, str, Dict]]:
        """Query the memory.

        modes:
          'ultrametric' — pure ultrametric distance ranking
          'hybrid'      — embedding pre-filter, then ultrametric rerank
          'cosine'      — pure embedding similarity (for comparison)
        """
        if mode == "ultrametric" or not self.embedder:
            return self._ultrametric_scan(features, top_k)
        elif mode == "cosine":
            return self._cosine_rank(features, top_k)
        elif mode == "hybrid":
            return self._hybrid_rank(features, embed_top_k, top_k)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _compute_v(self, query_sets: Dict, memory_sets: Dict) -> int:
        """Compute v_R = number of consecutive matching levels."""
        v = 0
        for level in range(self.n_levels):
            qs = query_sets.get(level, set())
            ms = memory_sets.get(level, set())
            if not qs or not ms:
                break
            sim = _jaccard(qs, ms)
            if sim >= self.thresholds[level]:
                v += 1
            else:
                break
        return v

    def _ultrametric_scan(
        self, features: Dict[str, Any], top_k: int
    ) -> List[Tuple[float, int, str, Dict]]:
        q_sets = features.get("feature_sets", {})
        scored = []
        for key, entry in self._store.items():
            v = self._compute_v(q_sets, entry["feature_sets"])
            d = self.base ** (-v)
            scored.append((d, v, key, entry["metadata"]))
        scored.sort(key=lambda x: (x[0], -x[1]))
        return scored[:top_k]

    def _cosine_rank(
        self, features: Dict[str, Any], top_k: int
    ) -> List[Tuple[float, int, str, Dict]]:
        if not self.embedder or "tokens" not in features:
            return self._ultrametric_scan(features, top_k)
        q_emb = self.embedder(" ".join(features["tokens"]))
        q_norm = np.linalg.norm(q_emb)
        q_sets = features.get("feature_sets", {})
        scored = []
        for key, entry in self._store.items():
            if entry["embedding"] is None:
                continue
            cos = float(np.dot(q_emb, entry["embedding"]) /
                        (q_norm * np.linalg.norm(entry["embedding"]) + 1e-12))
            v = self._compute_v(q_sets, entry["feature_sets"])
            scored.append((cos, v, key, entry["metadata"]))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]

    def _hybrid_rank(
        self, features: Dict[str, Any],
        embed_top_k: int, final_top_k: int,
    ) -> List[Tuple[float, int, str, Dict]]:
        if not self.embedder or "tokens" not in features:
            return self._ultrametric_scan(features, final_top_k)
        q_emb = self.embedder(" ".join(features["tokens"]))
        q_norm = np.linalg.norm(q_emb)
        candidates = []
        for key, entry in self._store.items():
            if entry["embedding"] is None:
                continue
            cos = float(np.dot(q_emb, entry["embedding"]) /
                        (q_norm * np.linalg.norm(entry["embedding"]) + 1e-12))
            candidates.append((cos, key, entry))
        candidates.sort(key=lambda x: -x[0])
        candidates = candidates[:embed_top_k]

        q_sets = features.get("feature_sets", {})
        reranked = []
        for cos, key, entry in candidates:
            v = self._compute_v(q_sets, entry["feature_sets"])
            d = self.base ** (-v)
            reranked.append((d, v, key, entry["metadata"]))
        reranked.sort(key=lambda x: (x[0], -x[1]))
        return reranked[:final_top_k]

    # ── Repair operations ──

    def update(self, key: str, features: Dict[str, Any],
              metadata: Optional[Dict] = None) -> Dict:
        """Update a memory, measuring repair depth."""
        if key not in self._store:
            self.store(key, features, metadata)
            return {"v_R": self.n_levels, "d_R": self.base ** (-self.n_levels)}

        old_entry = self._store[key].copy()
        q_sets = features.get("feature_sets", {})
        v = self._compute_v(q_sets, old_entry["feature_sets"])
        d = self.base ** (-v)

        self._store[key] = {
            "feature_sets": q_sets,
            "features": features,
            "metadata": metadata or old_entry.get("metadata", {}),
            "embedding": old_entry.get("embedding"),
        }

        self._history.append({
            "key": key, "old_entry": old_entry, "v_R": v, "d_R": d,
        })

        return {"v_R": v, "d_R": d}

    def rollback(self, steps: int = 1) -> int:
        count = 0
        for _ in range(min(steps, len(self._history))):
            record = self._history.pop()
            self._store[record["key"]] = record["old_entry"]
            count += 1
        return count

    def repair_history(self) -> List[Dict]:
        return list(self._history)

    # ── Introspection ──

    def stats(self) -> Dict:
        return {
            "n_items": len(self._store),
            "n_levels": self.n_levels,
            "base": self.base,
            "n_repairs": len(self._history),
            "has_embedder": self.embedder is not None,
        }

    def list_keys(self) -> List[str]:
        return list(self._store.keys())

    def get(self, key: str) -> Optional[Dict]:
        entry = self._store.get(key)
        if entry:
            return {
                "feature_sets": entry["feature_sets"],
                "features": entry["features"],
                "metadata": entry["metadata"],
            }
        return None

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store


# ─────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import random

    print("=" * 65)
    print("UltraMeM — Ultrametric Memory Module Demo")
    print("=" * 65)

    mem = UltraMeM(n_levels=4, base=2)
    extractor = TextFeatureExtractor(use_spacy=False)

    memories = [
        ("doc1", "The dog chased the cat through the garden"),
        ("doc2", "The wolf hunted the rabbit in the forest"),
        ("doc3", "The car drove down the highway very fast"),
        ("doc4", "The chef cooked pasta in the restaurant kitchen"),
        ("doc5", "The democracy solved the economic crisis"),
        ("doc6", "The cat slept on the warm sofa all afternoon"),
        ("doc7", "The programmer debugged the code until midnight"),
        ("doc8", "The bird flew over the tall pine trees"),
        ("doc9", "The lion chased the zebra across the savanna"),
        ("doc10", "The algorithm sorted the data in logarithmic time"),
    ]
    for key, text in memories:
        features = extractor(text)
        mem.store(key, features, {"text": text})

    print(f"\nStored {len(mem)} memories")

    queries = [
        ("The fox chased the mouse", "animal pursuit"),
        ("The dog ran after the ball", "animal motion"),
        ("The software processed the request", "programming"),
        ("The tiger stalked the deer silently", "predator-prey"),
    ]

    print(f"\n{'='*65}")
    print("Retrieval Results")
    print(f"{'='*65}")

    for qtext, qlabel in queries:
        qfeats = extractor(qtext)
        results = mem.query(qfeats, top_k=3)
        print(f"\nQuery: \"{qtext}\"  [{qlabel}]")
        for d, v, key, meta in results:
            text = meta.get("text", key)
            marker = "✓" if v >= 2 else " "
            print(f"  [{marker}] d_R={d:.3f}  v_R={v}  \"{text}\"")

    # Repair demo
    print(f"\n{'='*65}")
    print("Repair Demo")
    print(f"{'='*65}")
    doc1_sets = mem.get("doc1")["feature_sets"]
    print(f"\nOriginal doc1 feature sets:")
    for level in range(4):
        print(f"  level {level}: {doc1_sets.get(level, set())}")

    new_feats = extractor("The algorithm processed the data efficiently")
    result = mem.update("doc1", new_feats)
    print(f"\nUpdate to: \"The algorithm processed the data efficiently\"")
    print(f"  v_R = {result['v_R']} (preserved {result['v_R']} levels)")
    print(f"  d_R = {result['d_R']:.3f}")

    new_sets = mem.get("doc1")["feature_sets"]
    print(f"  new feature sets:")
    for level in range(4):
        print(f"  level {level}: {new_sets.get(level, set())}")

    mem.rollback(1)
    restored = mem.get("doc1")["feature_sets"]
    rollback_ok = restored[0] == doc1_sets[0] and restored[1] == doc1_sets[1]
    print(f"\n  Rollback: {'✓ feature sets restored' if rollback_ok else '✗ mismatch'}")

    # Hierarchy depth continuum
    print(f"\n{'='*65}")
    print("Hierarchy Depth Continuum")
    print(f"{'='*65}")

    f1 = extractor(memories[0][1])
    results = mem.query(f1, top_k=len(mem))
    print(f"\nNearest neighbors to \"{memories[0][1]}\":")
    for d, v, key, meta in results:
        text = meta.get("text", key)
        marker = "✓" if v >= 2 else " "
        print(f"  [{marker}] d_R={d:.3f}  v_R={v}  \"{text}\"")
