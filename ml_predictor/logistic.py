"""Multinomial logistic regression (MaxEnt) next-character model.

Where the n-gram model estimates P(next_char | context) from raw counts, this
model learns it as a softmax classifier over overlapping suffix features
(context of length 1, 2, ... up to ``order``), trained with plain SGD on
cross-entropy loss. Overlapping-length features let the model automatically
lean on shorter, more reliable contexts when the longest context is sparse,
which is generally more robust than a single fixed-order count table.

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
ALPHABET = sorted(set("abcdefghijklmnopqrstuvwxyz0123456789-_" + START + END))


class LogisticNgramModel:
    def __init__(self, order: int = 3, lr: float = 0.15, epochs: int = 15, l2: float = 1e-4, seed: int = 7):
        self.order = order
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2
        self.seed = seed
        self.vocab = ALPHABET
        self.char_index = {c: i for i, c in enumerate(self.vocab)}
        self.weights: dict[str, list[float]] = {}
        self.trained_on = 0

    # -- features ------------------------------------------------------
    def _features(self, ctx: str) -> list[str]:
        feats = ["bias"]
        for k in range(1, len(ctx) + 1):
            feats.append(f"s{k}:{ctx[-k:]}")
        return feats

    def _contexts(self, label: str):
        padded = START * self.order + label.lower() + END
        for i in range(self.order, len(padded)):
            yield padded[i - self.order:i], padded[i]

    def _scores(self, feats: list[str]) -> list[float]:
        totals = [0.0] * len(self.vocab)
        for f in feats:
            w = self.weights.get(f)
            if w:
                for j in range(len(self.vocab)):
                    totals[j] += w[j]
        return totals

    @staticmethod
    def _softmax(scores: list[float]) -> list[float]:
        m = max(scores)
        exps = [math.exp(s - m) for s in scores]
        z = sum(exps) or 1e-300
        return [e / z for e in exps]

    def train(self, labels) -> "LogisticNgramModel":
        data = []
        for label in labels:
            label = label.strip().lower()
            if not label:
                continue
            for ctx, nxt in self._contexts(label):
                data.append((ctx, nxt))
            self.trained_on += 1

        rng = random.Random(self.seed)
        v = len(self.vocab)
        for _ in range(self.epochs):
            rng.shuffle(data)
            for ctx, nxt in data:
                feats = self._features(ctx)
                probs = self._softmax(self._scores(feats))
                target_idx = self.char_index[nxt]
                for f in feats:
                    w = self.weights.setdefault(f, [0.0] * v)
                    for j in range(v):
                        grad = probs[j] - (1.0 if j == target_idx else 0.0)
                        w[j] -= self.lr * (grad + self.l2 * w[j])
        return self

    # -- scoring ---------------------------------------------------------
    def _logprob_char(self, ctx: str, ch: str) -> float:
        probs = self._softmax(self._scores(self._features(ctx)))
        p = max(probs[self.char_index[ch]], 1e-12)
        return math.log(p)

    def score(self, label: str) -> float:
        label = label.strip().lower()
        if not label:
            return float("-inf")
        total, n = 0.0, 0
        for ctx, nxt in self._contexts(label):
            total += self._logprob_char(ctx, nxt)
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
            ctx = START * self.order
            label = []
            for _ in range(max_len):
                probs = self._softmax(self._scores(self._features(ctx)))
                ch = rng.choices(self.vocab, weights=probs, k=1)[0]
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
            "lr": self.lr,
            "epochs": self.epochs,
            "l2": self.l2,
            "trained_on": self.trained_on,
            "weights": self.weights,
        }

    def save(self, path: str) -> None:
        save_model(self.to_dict(), path)

    @classmethod
    def from_dict(cls, data: dict) -> "LogisticNgramModel":
        model = cls(order=data["order"], lr=data["lr"], epochs=data["epochs"], l2=data["l2"])
        model.trained_on = data.get("trained_on", 0)
        model.weights = data["weights"]
        return model

    @classmethod
    def load(cls, path: str) -> "LogisticNgramModel":
        return cls.from_dict(load_model(path))
