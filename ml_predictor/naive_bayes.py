"""Multinomial Naive Bayes classifier for subdomain-label scoring.

Frames "is this a plausible subdomain label?" as a two-class text
classification problem: the positive class is the real training labels, and
a matched-size negative class is synthesised by shuffling each label's
characters (destroying its structure while preserving length/alphabet).
Each label is represented as a bag of overlapping character n-grams
(default trigrams), and Naive Bayes assumes these tokens are conditionally
independent given the class -- the classic simplifying assumption that makes
training a single pass over counts.

``score`` returns the log-odds log P(real|label) - log P(shuffled|label),
so it is not on the same absolute scale as the other models' log-probability
scores, but higher still means "more subdomain-like" and it is safe to rank
or threshold on.

Same public interface as ``CharNgramModel`` (train / score / rank / generate
/ save / load); ``generate`` falls back to sampling from the positive class's
character transition statistics, since Naive Bayes itself is a discriminative
scorer rather than a sequence generator.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from .serialize import save_model, load_model

START = "^"
END = "$"


class NaiveBayesModel:
    def __init__(self, order: int = 3, smoothing: float = 1.0, seed: int = 1234):
        self.order = order
        self.smoothing = smoothing
        self.seed = seed
        self.pos_counts: dict[str, int] = defaultdict(int)
        self.neg_counts: dict[str, int] = defaultdict(int)
        self.pos_total = 0
        self.neg_total = 0
        self.vocab: set[str] = set()
        self.gen_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.trained_on = 0

    # -- features ------------------------------------------------------
    def _tokens(self, label: str):
        padded = START * (self.order - 1) + label + END
        for i in range(len(padded) - self.order + 1):
            yield padded[i:i + self.order]

    def _contexts(self, label: str):
        padded = START * (self.order - 1) + label + END
        for i in range(self.order - 1, len(padded)):
            yield padded[i - (self.order - 1):i], padded[i]

    def train(self, labels) -> "NaiveBayesModel":
        cleaned = [l.strip().lower() for l in labels if l.strip()]
        rng = random.Random(self.seed)

        for label in cleaned:
            for tok in self._tokens(label):
                self.pos_counts[tok] += 1
                self.pos_total += 1
                self.vocab.add(tok)
            for ctx, nxt in self._contexts(label):
                self.gen_counts[ctx][nxt] += 1
            self.trained_on += 1

        for label in cleaned:
            chars = list(label)
            rng.shuffle(chars)
            shuffled = "".join(chars)
            for tok in self._tokens(shuffled):
                self.neg_counts[tok] += 1
                self.neg_total += 1
                self.vocab.add(tok)

        return self

    def _logprob(self, tok: str, counts: dict[str, int], total: int) -> float:
        v = len(self.vocab) or 1
        return math.log((counts.get(tok, 0) + self.smoothing) / (total + self.smoothing * v))

    # -- scoring ---------------------------------------------------------
    def score(self, label: str) -> float:
        label = label.strip().lower()
        if not label:
            return float("-inf")
        toks = list(self._tokens(label))
        if not toks:
            return float("-inf")
        pos = sum(self._logprob(t, self.pos_counts, self.pos_total) for t in toks)
        neg = sum(self._logprob(t, self.neg_counts, self.neg_total) for t in toks)
        return (pos - neg) / len(toks)

    def rank(self, candidates) -> list[tuple[str, float]]:
        scored = [(c, self.score(c)) for c in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    # -- generation (via positive-class transition stats) -------------------
    def generate(self, n: int = 100, max_len: int = 20, seed: int | None = None) -> list[str]:
        rng = random.Random(seed)
        out: set[str] = set()
        attempts = 0
        while len(out) < n and attempts < n * 20:
            attempts += 1
            ctx = START * (self.order - 1)
            label = []
            for _ in range(max_len):
                row = self.gen_counts.get(ctx)
                if not row:
                    break
                chars, weights = zip(*row.items())
                ch = rng.choices(chars, weights=weights, k=1)[0]
                if ch == END:
                    break
                label.append(ch)
                ctx = (ctx + ch)[-(self.order - 1):] if self.order > 1 else ""
            word = "".join(label)
            if word and word not in out:
                out.add(word)
        return sorted(out)

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "smoothing": self.smoothing,
            "trained_on": self.trained_on,
            "pos_counts": dict(self.pos_counts),
            "neg_counts": dict(self.neg_counts),
            "pos_total": self.pos_total,
            "neg_total": self.neg_total,
            "vocab": sorted(self.vocab),
            "gen_counts": {ctx: dict(row) for ctx, row in self.gen_counts.items()},
        }

    def save(self, path: str) -> None:
        save_model(self.to_dict(), path)

    @classmethod
    def from_dict(cls, data: dict) -> "NaiveBayesModel":
        model = cls(order=data["order"], smoothing=data["smoothing"])
        model.trained_on = data.get("trained_on", 0)
        model.pos_counts = defaultdict(int, data["pos_counts"])
        model.neg_counts = defaultdict(int, data["neg_counts"])
        model.pos_total = data["pos_total"]
        model.neg_total = data["neg_total"]
        model.vocab = set(data["vocab"])
        for ctx, row in data["gen_counts"].items():
            model.gen_counts[ctx] = defaultdict(int, row)
        return model

    @classmethod
    def load(cls, path: str) -> "NaiveBayesModel":
        return cls.from_dict(load_model(path))
