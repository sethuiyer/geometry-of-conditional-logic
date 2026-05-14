"""
Ultrametric Retrieval on Project Gutenberg
============================================

Demonstrates that ultrametric distance preserves deeper structural
commitments than BM25 on real-world text.

Hierarchy levels (book paragraph → features):
  0: Book source (which book)
  1: Named entity types (PERSON, ORG, GPE, etc.)
  2: Dependency triples (subject-verb-object patterns)
  3: Content word overlap (nouns, verbs, adjectives)
  4: Surface token overlap (all words)

BM25 operates at level 4 (surface tokens).
Ultrametric retrieval operates at all levels, weighted by depth.
"""

import re
import math
import random
import urllib.request
import time
import spacy
from collections import Counter

# ─────────────────────────────────────────────
# 1. Download books from Project Gutenberg
# ─────────────────────────────────────────────

GUTENBERG_URLS = {
    "pride_and_prejudice": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
    "moby_dick": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
    "alice_in_wonderland": "https://www.gutenberg.org/cache/epub/11/pg11.txt",
    "great_expectations": "https://www.gutenberg.org/cache/epub/1400/pg1400.txt",
    "dracula": "https://www.gutenberg.org/cache/epub/345/pg345.txt",
}

CACHE_DIR = "/tmp/gutenberg_cache"


def download_book(name, url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{name}.txt")
    if not os.path.exists(path):
        print(f"  Downloading {name}...")
        urllib.request.urlretrieve(url, path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_paragraphs(text, book_name, min_words=10, max_paragraphs=200):
    """Split book text into paragraphs, assign book-level metadata."""
    lines = text.split("\n\n")
    paragraphs = []
    for para in lines:
        clean = re.sub(r"\s+", " ", para).strip()
        words = clean.split()
        if len(words) >= min_words:
            paragraphs.append({
                "text": clean,
                "book": book_name,
                "words": words,
            })
        if len(paragraphs) >= max_paragraphs:
            break
    return paragraphs


# ─────────────────────────────────────────────
# 2. Feature extraction with spaCy
# ─────────────────────────────────────────────

nlp = None


def get_nlp():
    global nlp
    if nlp is None:
        print("  Loading spaCy model...")
        nlp = spacy.load("en_core_web_sm")
    return nlp


def extract_features(text):
    """
    Extract hierarchical features from a paragraph.
    Returns dict with levels 0-4.
    """
    doc = get_nlp()(text[:100000])  # limit to avoid OOM

    # Level 0: Book — set externally

    # Level 1: Named entity types present
    entity_types = Counter()
    for ent in doc.ents:
        entity_types[ent.label_] += 1

    # Level 2: Dependency triples (simplified: (root.dep_, root.head.pos_))
    dep_patterns = Counter()
    for token in doc:
        if token.dep_ in ("nsubj", "dobj", "iobj", "pobj") and token.head.pos_ == "VERB":
            dep_patterns[(token.dep_, token.head.lemma_)] += 1

    # Level 3: Content words (nouns, verbs, adjectives, adverbs)
    content_words = Counter()
    for token in doc:
        if token.pos_ in ("NOUN", "VERB", "ADJ", "ADV") and not token.is_stop:
            content_words[token.lemma_.lower()] += 1

    # Level 4: Surface tokens (all non-punct, lowercased)
    surface_tokens = Counter()
    for token in doc:
        if not token.is_punct and not token.is_space:
            surface_tokens[token.text.lower()] += 1

    return {
        "entity_types": entity_types,
        "dep_patterns": dep_patterns,
        "content_words": content_words,
        "surface_tokens": surface_tokens,
    }


# ─────────────────────────────────────────────
# 3. Hierarchy depth between two paragraphs
# ─────────────────────────────────────────────

# Primes for each level (0 = deepest)
LEVEL_PRIMES = [2, 3, 5, 7, 11]


def feature_similarity(c1, c2):
    """Jaccard similarity between two Counters (treating as sets)."""
    set1 = set(c1.keys())
    set2 = set(c2.keys())
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def hierarchy_depth(p1, p2, threshold=0.05):
    """
    v_R = number of consecutive levels (0=NEs, 1=dep, 2=content, 3=surface)
    where similarity >= threshold.
    Also checks level -1 (same book).
    """
    levels = [
        ("book", p1["book"] == p2["book"]),
        ("entities", feature_similarity(p1["entity_types"], p2["entity_types"]) >= threshold),
        ("dep", feature_similarity(p1["dep_patterns"], p2["dep_patterns"]) >= threshold),
        ("content", feature_similarity(p1["content_words"], p2["content_words"]) >= threshold),
        ("surface", feature_similarity(p1["surface_tokens"], p2["surface_tokens"]) >= threshold),
    ]
    v = 0
    for name, ok in levels:
        if ok:
            v += 1
        else:
            break
    return v


def ultrametric_distance(p1, p2, base=2):
    return base ** (-hierarchy_depth(p1, p2))


# ─────────────────────────────────────────────
# 4. BM25 baseline
# ─────────────────────────────────────────────

class BM25:
    def __init__(self, corpus):
        self.corpus = corpus
        self.N = len(corpus)
        self.k1 = 1.5
        self.b = 0.75
        self.avgdl = sum(len(p["words"]) for p in corpus) / self.N
        self.df = Counter()
        self.doc_len = []
        for p in corpus:
            tokens = [w.lower() for w in p["words"]]
            self.doc_len.append(len(tokens))
            for t in set(tokens):
                self.df[t] += 1

    def score(self, query_words, doc_idx):
        q_tokens = [w.lower() for w in query_words]
        d_tokens = [w.lower() for w in self.corpus[doc_idx]["words"]]
        dl = self.doc_len[doc_idx]
        score = 0.0
        for qt in set(q_tokens):
            if qt not in self.df:
                continue
            idf = math.log((self.N - self.df[qt] + 0.5) / (self.df[qt] + 0.5) + 1)
            tf = d_tokens.count(qt)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            score += idf * numerator / denominator
        return score

    def rank(self, query_words, exclude_idx=None, top_k=10):
        scores = [(self.score(query_words, i), i) for i in range(self.N)
                  if i != exclude_idx]
        scores.sort(reverse=True)
        return scores[:top_k]


# ─────────────────────────────────────────────
# 5. Experiment
# ─────────────────────────────────────────────

def run_experiment():
    print("=" * 68)
    print("  Ultrametric Retrieval on Project Gutenberg")
    print("=" * 68)

    # Download and parse books
    print("\nLoading books...")
    all_paragraphs = []
    for name, url in GUTENBERG_URLS.items():
        text = download_book(name, url)
        paras = extract_paragraphs(text, name, min_words=15, max_paragraphs=150)
        all_paragraphs.extend(paras)
        print(f"  {name}: {len(paras)} paragraphs")

    print(f"\nTotal paragraphs: {len(all_paragraphs)}")

    # Extract features (this is the expensive part)
    print("\nExtracting features with spaCy...")
    t0 = time.time()
    for i, p in enumerate(all_paragraphs):
        features = extract_features(p["text"])
        p.update(features)
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            print(f"  [{i+1}/{len(all_paragraphs)}] ({elapsed:.1f}s)")
    t1 = time.time()
    print(f"  Feature extraction complete: {t1-t0:.1f}s")

    # Build BM25 index
    print("\nBuilding BM25 index...")
    bm25 = BM25(all_paragraphs)

    # Sample queries
    random.seed(42)
    query_indices = random.sample(range(len(all_paragraphs)), 8)
    queries = [(all_paragraphs[i]["text"], i) for i in query_indices]

    # Evaluate
    print(f"\n{'='*68}")
    print(f"  Evaluating {len(queries)} queries...")
    print(f"{'='*68}")

    bm25_depth_total = 0
    ultra_depth_total = 0
    bm25_p3_total = 0
    ultra_p3_total = 0
    bm25_top1_total = 0
    ultra_top1_total = 0

    for qi, (qtext, qidx) in enumerate(queries):
        qpara = all_paragraphs[qidx]

        # Ground truth: paragraphs sharing depth >= 2 (entity or book match)
        relevant = set()
        for j, p in enumerate(all_paragraphs):
            if j == qidx:
                continue
            d = hierarchy_depth(qpara, p, threshold=0.03)
            if d >= 2:
                relevant.add(j)

        # BM25
        bm25_results = bm25.rank(qpara["words"], exclude_idx=qidx, top_k=10)
        bm25_top5 = [idx for _, idx in bm25_results[:5]]
        bm25_depth = sum(hierarchy_depth(qpara, all_paragraphs[j]) for j in bm25_top5) / max(len(bm25_top5), 1)
        bm25_relevant = sum(1 for j in bm25_top5 if j in relevant)
        bm25_top1 = 1 if bm25_top5 and bm25_top5[0] in relevant else 0

        # Ultrametric retrieval: rank all by hierarchy_depth
        ultra_scores = []
        for j, p in enumerate(all_paragraphs):
            if j == qidx:
                continue
            d = hierarchy_depth(qpara, p, threshold=0.03)
            ultra_scores.append((d, j))
        ultra_scores.sort(reverse=True)  # higher depth = better
        ultra_top5 = [j for _, j in ultra_scores[:5]]
        ultra_depth = sum(hierarchy_depth(qpara, all_paragraphs[j]) for j in ultra_top5) / max(len(ultra_top5), 1)
        ultra_relevant = sum(1 for j in ultra_top5 if j in relevant)
        ultra_top1 = 1 if ultra_top5 and ultra_top5[0] in relevant else 0

        bm25_depth_total += bm25_depth
        ultra_depth_total += ultra_depth
        bm25_p3_total += bm25_relevant / 5.0
        ultra_p3_total += ultra_relevant / 5.0
        bm25_top1_total += bm25_top1
        ultra_top1_total += ultra_top1

        if qi < 2:
            # Show first two queries in detail
            print(f"\n  Query {qi+1}: \"{qtext[:80]}...\"")
            print(f"  Book: {qpara['book']}, entities: {list(qpara['entity_types'].keys())[:3]}")
            print(f"  Relevant: {len(relevant)} paragraphs")
            print(f"  BM25 top-1: [{chr(10003) if bm25_top1 else ' '}] depth={bm25_depth:.1f}  \"{all_paragraphs[bm25_top5[0]]['text'][:60]}...\"")
            print(f"  Ultra top-1: [{chr(10003) if ultra_top1 else ' '}] depth={ultra_depth:.1f}  \"{all_paragraphs[ultra_top5[0]]['text'][:60]}...\"")

    n = len(queries)
    print(f"\n{'='*68}")
    print(f"  Aggregated Results ({n} queries, {len(all_paragraphs)} docs)")
    print(f"{'='*68}")
    print(f"  {'Metric':<50} {'BM25':>8} {'Ultra':>8}")
    print(f"  {'-'*50} {'-'*8} {'-'*8}")
    print(f"  {'Mean preserved depth in top-5':<50} {bm25_depth_total/n:>8.2f} {ultra_depth_total/n:>8.2f}")
    print(f"  {'Precision@5 (depth >= 2)':<50} {bm25_p3_total/n:>8.3f} {ultra_p3_total/n:>8.3f}")
    print(f"  {'Top-1 hit rate':<50} {bm25_top1_total/n:>8.2f} {ultra_top1_total/n:>8.2f}")
    print(f"\n  {'='*54}")
    if ultra_depth_total > bm25_depth_total:
        print(f"  ✓ Ultrametric preserves {ultra_depth_total/n - bm25_depth_total/n:.2f} more depth layers than BM25")
    if ultra_p3_total > bm25_p3_total:
        print(f"  ✓ Ultrametric precision@5: +{(ultra_p3_total - bm25_p3_total)/n*100:.0f}%")
    if ultra_top1_total > bm25_top1_total:
        print(f"  ✓ Ultrametric top-1: +{(ultra_top1_total - bm25_top1_total)/n*100:.0f}%")
    print(f"  {'='*54}")


if __name__ == "__main__":
    import os
    run_experiment()
