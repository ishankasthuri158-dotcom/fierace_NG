"""Prediction by Partial Matching (PPM-C style) language model.

Rather than committing to one fixed context length like the n-gram model,
PPM keeps count tables for every order from 0 (no context) up to
``max_order`` and blends them at prediction time: try the longest context
first, and if the character hasn't been seen there, "escape" to the
next-shorter context with a probability proportional to how many distinct
characters that context has produced before (the PPM-C escape rule). This
adaptive back-off is a long-standing, well-studied improvement over flat
additive (Laplace) smoothing for exactly this kind of short-string modeling.

This implementation omits full PPM exclusion-set renormalisation for
simplicity/speed but keeps the core escape-and-backoff mechanism, which is
the part that matters for comparison purposes.

Same public interface as ``CharNgramModel`` (train / score / rank / generate
/ save / load).
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from .serialize import save_model, load_model

START = "^"
END = "$"
ALPHABET = set("abcdefghijklmnopqrstuvwxyz0123456789-_" + START + END)


class PPMModel:
    def __init__(self, max_order: int = 4):
        self.max_order = max_order
        self.counts: list[dict[str, dict[str, int]]] = [defaultdict(lambda: defaultdict(int)) for _ in range(max_order + 1)]
        self.vocab: set[str] = set(ALPHABET)
        self.trained_on = 0

    def train(self, labels) -> "PPMModel":
        for label in labels:
            label = label.strip().lower()
            if not label:
                continue
            padded = START * self.max_order + label + END
            for i in range(self.max_order, len(padded)):
                nxt = padded[i]
                self.vocab.add(nxt)
                for k in range(0, self.max_order + 1):
                    ctx = padded[i - k:i] if k > 0 else ""
                    self.counts[k][ctx][nxt] += 1
            self.trained_on += 1
        return self

    # -- probability -------------------------------------------------------
    def _char_prob(self, ctx: str, ch: str) -> float:
        excluded: set[str] = set()
        remaining_mass = 1.0
        for k in range(self.max_order, -1, -1):
            sub_ctx = ctx[-k:] if k > 0 else ""
            row = self.counts[k].get(sub_ctx)
            if not row:
                continue
            usable = {c: cnt for c, cnt in row.items() if c not in excluded}
            total = sum(usable.values())
            distinct = len(usable)
            if total == 0:
                continue
            escape = distinct / (total + distinct)
            if ch in usable:
                p_here = usable[ch] / (total + distinct)
                return remaining_mass * p_here
            remaining_mass *= escape
            excluded.update(usable.keys())

        remaining_chars = self.vocab - excluded
        v = len(remaining_chars) or 1
        return remaining_mass * (1.0 / v)

    def _distribution(self, ctx: str) -> dict[str, float]:
        dist = {ch: self._char_prob(ctx, ch) for ch in self.vocab}
        z = sum(dist.values()) or 1e-300
        return {c: p / z for c, p in dist.items()}

    def score(self, label: str) -> float:
        label = label.strip().lower()
        if not label:
            return float("-inf")
        padded = START * self.max_order + label + END
        total, n = 0.0, 0
        for i in range(self.max_order, len(padded)):
            ctx = padded[i - self.max_order:i]
            ch = padded[i]
            p = self._char_prob(ctx, ch)
            total += math.log(max(p, 1e-12))
            n += 1
        return total / n if n else float("-inf")

    def rank(self, candidates) -> list[tuple[str, float]]:
        scored = [(c, self.score(c)) for c in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    # -- generation --------------------------------------------------------
    def generate(self, n: int = 100, max_len: int = 20, seed: int | None = None) -> list[str]:
        rng = random.Random(seed)
        out: set[str] = set()
        attempts = 0
        while len(out) < n and attempts < n * 20:
            attempts += 1
            ctx = START * self.max_order
            label = []
            for _ in range(max_len):
                dist = self._distribution(ctx)
                chars, weights = zip(*dist.items())
                ch = rng.choices(chars, weights=weights, k=1)[0]
                if ch == END:
                    break
                label.append(ch)
                ctx = (ctx + ch)[-self.max_order:]
            word = "".join(label)
            if word and word not in out:
                out.add(word)
        return sorted(out)

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "max_order": self.max_order,
            "trained_on": self.trained_on,
            "vocab": sorted(self.vocab),
            "counts": [
                {ctx: dict(row) for ctx, row in level.items()}
                for level in self.counts
            ],
        }

    def save(self, path: str) -> None:
        save_model(self.to_dict(), path)

    @classmethod
    def from_dict(cls, data: dict) -> "PPMModel":
        model = cls(max_order=data["max_order"])
        model.trained_on = data.get("trained_on", 0)
        model.vocab = set(data["vocab"])
        model.counts = [defaultdict(lambda: defaultdict(int)) for _ in range(model.max_order + 1)]
        for k, level in enumerate(data["counts"]):
            for ctx, row in level.items():
                model.counts[k][ctx] = defaultdict(int, row)
        return model

    @classmethod
    def load(cls, path: str) -> "PPMModel":
        return cls.from_dict(load_model(path))
