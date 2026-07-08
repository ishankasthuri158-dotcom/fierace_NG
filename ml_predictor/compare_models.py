"""Side-by-side comparison of subdomain-scoring models.

Trains the existing n-gram baseline alongside four additional algorithms --
Hidden Markov Model, Naive Bayes, Logistic Regression (MaxEnt), and PPM -- on
the same train/test split of a corpus, and reports the numbers typically
wanted in a model-comparison table: training time, held-out average
log-probability (higher/less negative is better), and accuracy at telling a
real label apart from a same-length random string.

Note: Naive Bayes' score is a log-odds ratio rather than a log-probability,
so its avg_logprob column is not on the same absolute scale as the other
models -- only its sign and its real-vs-random accuracy are comparable.

Usage:
    python -m ml_predictor.compare_models                       # built-in corpus
    python -m ml_predictor.compare_models big_corpus.txt         # real wordlist
    python -m ml_predictor.compare_models big_corpus.txt --sample=8000

The HMM and Logistic models are iterative pure-Python implementations, so on
a corpus with tens of thousands of labels a random --sample keeps runtime in
the minutes rather than hours while still using far more data than the
built-in ~250-label corpus. Omit --sample (or set it >= corpus size) to train
on everything.
"""
from __future__ import annotations

import random
import sys
import time

from .corpus import COMMON_SUBDOMAINS
from .train import labels_from_lines
from .ngram import CharNgramModel
from .hmm import HMMModel
from .naive_bayes import NaiveBayesModel
from .logistic import LogisticNgramModel
from .ppm import PPMModel

RANDOM_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def _split(labels, test_frac: float = 0.2, seed: int = 42):
    rng = random.Random(seed)
    shuffled = list(labels)
    rng.shuffle(shuffled)
    cut = max(1, int(len(shuffled) * (1 - test_frac)))
    return shuffled[:cut], shuffled[cut:]


def _random_label(rng: random.Random, length: int) -> str:
    return "".join(rng.choice(RANDOM_ALPHABET) for _ in range(length))


def evaluate(model, train_labels, test_labels, rng: random.Random) -> dict:
    t0 = time.perf_counter()
    model.train(train_labels)
    train_time = time.perf_counter() - t0

    avg_logprob = sum(model.score(l) for l in test_labels) / len(test_labels)

    correct = 0
    for label in test_labels:
        decoy = _random_label(rng, max(3, len(label)))
        if model.score(label) > model.score(decoy):
            correct += 1
    discrimination = correct / len(test_labels)

    return {
        "train_time_s": train_time,
        "avg_logprob": avg_logprob,
        "real_vs_random_acc": discrimination,
    }


def load_corpus(argv: list[str]) -> list[str]:
    """Load labels from a corpus file arg, or fall back to the built-in corpus."""
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        return list(COMMON_SUBDOMAINS)
    with open(paths[0], "r", encoding="utf-8", errors="ignore") as fh:
        return labels_from_lines(fh)


def _sample_arg(argv: list[str]) -> int | None:
    for a in argv:
        if a.startswith("--sample"):
            return int(a.split("=")[-1])
    return None


def main(argv: list[str] | None = None) -> dict:
    argv = sys.argv[1:] if argv is None else argv
    rng = random.Random(42)

    labels = load_corpus(argv)
    n_loaded = len(labels)
    sample = _sample_arg(argv)
    if sample and sample < len(labels):
        labels = random.Random(42).sample(labels, sample)
    print(f"Corpus: {n_loaded} labels loaded" + (f", sampled down to {len(labels)}" if sample and sample < n_loaded else ""))

    train_labels, test_labels = _split(labels, seed=42)

    models = {
        "n-gram (order=3)": CharNgramModel(order=3),
        "HMM (states=6)": HMMModel(n_states=6),
        "Naive Bayes (order=3)": NaiveBayesModel(order=3),
        "Logistic/MaxEnt (order=3)": LogisticNgramModel(order=3, epochs=15),
        "PPM (order=4)": PPMModel(max_order=4),
    }

    results = {}
    for name, model in models.items():
        results[name] = evaluate(model, train_labels, test_labels, rng)

    header = f"{'Model':28s} {'train_s':>8s} {'avg_logprob':>12s} {'real_vs_rand_acc':>17s}"
    print(f"Train/test split: {len(train_labels)}/{len(test_labels)} labels\n")
    print(header)
    print("-" * len(header))
    for name, m in results.items():
        print(f"{name:28s} {m['train_time_s']:8.4f} {m['avg_logprob']:12.4f} {m['real_vs_random_acc']:17.4f}")
    print("\nNote: Naive Bayes reports a log-odds score, not a log-probability --")
    print("its avg_logprob is not directly comparable in scale to the other rows.")

    return results


if __name__ == "__main__":
    main()
