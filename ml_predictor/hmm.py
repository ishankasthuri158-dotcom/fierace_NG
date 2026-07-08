"""Hidden Markov Model for subdomain-label scoring.

Unlike the character n-gram model, which conditions directly on the previous
``order`` characters, an HMM assumes an unobserved ("hidden") state sequence
generates the observed characters. States are learned unsupervised via the
Baum-Welch (EM) algorithm. This captures longer-range stylistic regularities
(e.g. "looks like an infra name" vs "looks like a marketing name") that a
fixed-order n-gram cannot represent as a single latent factor.

Same public interface as ``CharNgramModel``: train / score / rank / generate /
save / load, so it can be swapped in for side-by-side comparison.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from .serialize import save_model, load_model

END = "$"
ALPHABET = list("abcdefghijklmnopqrstuvwxyz0123456789-_") + [END]


class HMMModel:
    def __init__(self, n_states: int = 6, iterations: int = 15, seed: int = 13):
        self.n_states = n_states
        self.iterations = iterations
        self.seed = seed
        self.alphabet = ALPHABET
        self.sym_index = {c: i for i, c in enumerate(self.alphabet)}
        self.pi: list[float] = []
        self.A: list[list[float]] = []
        self.B: list[list[float]] = []
        self.trained_on = 0

    # -- init ----------------------------------------------------------
    def _random_init(self, rng: random.Random):
        n, v = self.n_states, len(self.alphabet)

        def _row(size):
            vals = [rng.random() + 0.1 for _ in range(size)]
            z = sum(vals)
            return [x / z for x in vals]

        self.pi = _row(n)
        self.A = [_row(n) for _ in range(n)]
        self.B = [_row(v) for _ in range(n)]

    # -- forward/backward (scaled) --------------------------------------
    def _forward_backward(self, obs: list[int]):
        n = self.n_states
        T = len(obs)
        alpha = [[0.0] * n for _ in range(T)]
        c = [0.0] * T

        for i in range(n):
            alpha[0][i] = self.pi[i] * self.B[i][obs[0]]
        c[0] = 1.0 / (sum(alpha[0]) or 1e-300)
        alpha[0] = [a * c[0] for a in alpha[0]]

        for t in range(1, T):
            for j in range(n):
                s = sum(alpha[t - 1][i] * self.A[i][j] for i in range(n))
                alpha[t][j] = s * self.B[j][obs[t]]
            c[t] = 1.0 / (sum(alpha[t]) or 1e-300)
            alpha[t] = [a * c[t] for a in alpha[t]]

        beta = [[0.0] * n for _ in range(T)]
        beta[T - 1] = [c[T - 1]] * n
        for t in range(T - 2, -1, -1):
            for i in range(n):
                beta[t][i] = c[t] * sum(
                    self.A[i][j] * self.B[j][obs[t + 1]] * beta[t + 1][j] for j in range(n)
                )

        loglik = -sum(math.log(x) for x in c)
        return alpha, beta, c, loglik

    def train(self, labels) -> "HMMModel":
        sequences = []
        for label in labels:
            label = label.strip().lower()
            if not label:
                continue
            sequences.append([self.sym_index[ch] for ch in label if ch in self.sym_index] + [self.sym_index[END]])
            self.trained_on += 1
        sequences = [s for s in sequences if s]

        rng = random.Random(self.seed)
        self._random_init(rng)
        n, v = self.n_states, len(self.alphabet)
        eps = 1e-6

        for _ in range(self.iterations):
            pi_acc = [0.0] * n
            A_num = [[0.0] * n for _ in range(n)]
            A_den = [0.0] * n
            B_num = [[0.0] * v for _ in range(n)]
            B_den = [0.0] * n

            for obs in sequences:
                T = len(obs)
                if T < 1:
                    continue
                alpha, beta, c, _ = self._forward_backward(obs)

                gamma = []
                for t in range(T):
                    row = [alpha[t][i] * beta[t][i] / c[t] for i in range(n)]
                    z = sum(row) or 1e-300
                    gamma.append([x / z for x in row])

                for i in range(n):
                    pi_acc[i] += gamma[0][i]

                for t in range(T - 1):
                    denom = 0.0
                    xi_t = [[0.0] * n for _ in range(n)]
                    for i in range(n):
                        for j in range(n):
                            val = alpha[t][i] * self.A[i][j] * self.B[j][obs[t + 1]] * beta[t + 1][j]
                            xi_t[i][j] = val
                            denom += val
                    denom = denom or 1e-300
                    for i in range(n):
                        for j in range(n):
                            A_num[i][j] += xi_t[i][j] / denom
                        A_den[i] += gamma[t][i]

                for t in range(T):
                    for i in range(n):
                        B_num[i][obs[t]] += gamma[t][i]
                        B_den[i] += gamma[t][i]

            total_seqs = len(sequences) or 1
            self.pi = [(x / total_seqs) + eps for x in pi_acc]
            z = sum(self.pi)
            self.pi = [x / z for x in self.pi]

            for i in range(n):
                den = A_den[i] or 1e-300
                row = [(A_num[i][j] / den) + eps for j in range(n)]
                z = sum(row)
                self.A[i] = [x / z for x in row]

                den = B_den[i] or 1e-300
                row = [(B_num[i][k] / den) + eps for k in range(v)]
                z = sum(row)
                self.B[i] = [x / z for x in row]

        return self

    # -- scoring ---------------------------------------------------------
    def score(self, label: str) -> float:
        label = label.strip().lower()
        if not label:
            return float("-inf")
        obs = [self.sym_index[ch] for ch in label if ch in self.sym_index] + [self.sym_index[END]]
        if not self.pi:
            return float("-inf")
        _, _, _, loglik = self._forward_backward(obs)
        return loglik / len(obs)

    def rank(self, candidates) -> list[tuple[str, float]]:
        scored = [(c, self.score(c)) for c in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    # -- generation --------------------------------------------------------
    def generate(self, n: int = 100, max_len: int = 20, seed: int | None = None) -> list[str]:
        rng = random.Random(seed)
        out: set[str] = set()
        attempts = 0
        end_idx = self.sym_index[END]
        while len(out) < n and attempts < n * 20:
            attempts += 1
            state = rng.choices(range(self.n_states), weights=self.pi, k=1)[0]
            label = []
            for _ in range(max_len):
                sym = rng.choices(range(len(self.alphabet)), weights=self.B[state], k=1)[0]
                if sym == end_idx:
                    break
                label.append(self.alphabet[sym])
                state = rng.choices(range(self.n_states), weights=self.A[state], k=1)[0]
            word = "".join(label)
            if word and word not in out:
                out.add(word)
        return sorted(out)

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "n_states": self.n_states,
            "trained_on": self.trained_on,
            "pi": self.pi,
            "A": self.A,
            "B": self.B,
        }

    def save(self, path: str) -> None:
        save_model(self.to_dict(), path)

    @classmethod
    def from_dict(cls, data: dict) -> "HMMModel":
        model = cls(n_states=data["n_states"])
        model.trained_on = data.get("trained_on", 0)
        model.pi = data["pi"]
        model.A = data["A"]
        model.B = data["B"]
        return model

    @classmethod
    def load(cls, path: str) -> "HMMModel":
        return cls.from_dict(load_model(path))
