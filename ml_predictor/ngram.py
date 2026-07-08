"""Character n-gram language model for subdomain prediction (Day 5).

This is the lightweight "AI" component from the proposal. It is a classic
character-level n-gram model (the baseline the proposal calls for, ahead of an
optional char-RNN) implemented in pure Python so it has no heavy ML
dependencies and trains in milliseconds on tens of thousands of labels.

What it does:
  * ``train``     -- learn P(next_char | previous k chars) from real subdomain
                     labels with add-k (Laplace) smoothing.
  * ``score``     -- average log-probability of a label; higher = more
                     "subdomain-like" per the training vocabulary.
  * ``generate``  -- sample brand-new candidate labels from the distribution.
  * ``rank``      -- order an arbitrary candidate list by score.

Predictions let Fierce-NG go beyond a static wordlist: it can rank a huge
candidate pool and verify only the most plausible names, or invent new ones
that match the organisation's naming style.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from .serialize import save_model, load_model

START = "^"   # start-of-label marker
END = "$"     # end-of-label marker
# Characters legal in a DNS label, plus our markers.
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789-_" + START + END


class CharNgramModel:
    def __init__(self, order: int = 3, smoothing: float = 0.1):
        self.order = order
        self.smoothing = smoothing
        # context (string of length `order`) -> {next_char: count}
        self.counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.vocab: set[str] = set(ALPHABET)
        self.trained_on = 0

    # -- training ----------------------------------------------------------
    def _contexts(self, label: str):
        padded = START * self.order + label.lower() + END
        for i in range(self.order, len(padded)):
            yield padded[i - self.order:i], padded[i]

    def train(self, labels) -> "CharNgramModel":
        for label in labels:
            label = label.strip().lower()
            if not label:
                continue
            for ctx, nxt in self._contexts(label):
                self.counts[ctx][nxt] += 1
                self.vocab.add(nxt)
            self.trained_on += 1
        return self

    # -- probability -------------------------------------------------------
    def _logprob_char(self, ctx: str, ch: str) -> float:
        row = self.counts.get(ctx, {})
        total = sum(row.values())
        v = len(self.vocab)
        prob = (row.get(ch, 0) + self.smoothing) / (total + self.smoothing * v)
        return math.log(prob)

    def score(self, label: str) -> float:
        """Average per-character log-probability (length-normalised)."""
        label = label.strip().lower()
        if not label:
            return float("-inf")
        total, n = 0.0, 0
        for ctx, nxt in self._contexts(label):
            total += self._logprob_char(ctx, nxt)
            n += 1
        return total / n if n else float("-inf")

    def rank(self, candidates) -> list[tuple[str, float]]:
        """Return ``(label, score)`` sorted best-first."""
        scored = [(c, self.score(c)) for c in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    # -- generation --------------------------------------------------------
    def generate(self, n: int = 100, max_len: int = 20, seed: int | None = None) -> list[str]:
        """Sample ``n`` unique new labels from the learned distribution."""
        rng = random.Random(seed)
        out: set[str] = set()
        attempts = 0
        while len(out) < n and attempts < n * 20:
            attempts += 1
            ctx = START * self.order
            label = []
            for _ in range(max_len):
                row = self.counts.get(ctx)
                if not row:
                    break
                chars, weights = zip(*row.items())
                ch = rng.choices(chars, weights=weights, k=1)[0]
                if ch == END:
                    break
                label.append(ch)
                ctx = (ctx + ch)[-self.order:]
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
            "vocab": sorted(self.vocab),
            "counts": {ctx: dict(row) for ctx, row in self.counts.items()},
        }

    def save(self, path: str) -> None:
        save_model(self.to_dict(), path)

    @classmethod
    def from_dict(cls, data: dict) -> "CharNgramModel":
        model = cls(order=data["order"], smoothing=data["smoothing"])
        model.trained_on = data.get("trained_on", 0)
        model.vocab = set(data["vocab"])
        for ctx, row in data["counts"].items():
            model.counts[ctx] = defaultdict(int, row)
        return model

    @classmethod
    def load(cls, path: str) -> "CharNgramModel":
        return cls.from_dict(load_model(path))
