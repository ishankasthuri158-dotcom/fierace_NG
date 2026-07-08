"""Train/test-split accuracy check for each subdomain-scoring model, printed
one by one as each finishes (rather than compare_models.py's single summary
table at the end).

Accuracy here means: given a real held-out label and a random same-length
decoy string, how often does the model score the real one higher?

Usage:
    python -m ml_predictor.evaluate_accuracy                          # built-in corpus
    python -m ml_predictor.evaluate_accuracy data/subdomains_clean.txt
"""
from __future__ import annotations

import sys
import time

from .corpus import COMMON_SUBDOMAINS
from .train import labels_from_lines
from .compare_models import _split, _random_label, RANDOM_ALPHABET
from .ngram import CharNgramModel
from .hmm import HMMModel
from .naive_bayes import NaiveBayesModel
from .logistic import LogisticNgramModel
from .ppm import PPMModel
import random


def load_labels(corpus_path: str | None) -> list[str]:
    if not corpus_path:
        return COMMON_SUBDOMAINS
    with open(corpus_path, "r", encoding="utf-8", errors="ignore") as fh:
        return labels_from_lines(fh)


def main(argv: list[str]) -> int:
    corpus_path = argv[0] if len(argv) > 0 else None
    labels = load_labels(corpus_path)
    source = corpus_path or "built-in corpus"

    train_labels, test_labels = _split(labels, seed=42)
    print(f"Corpus: {source} ({len(labels)} labels)")
    print(f"Train/test split: {len(train_labels)}/{len(test_labels)}\n")

    models = {
        "n-gram (order=4)": CharNgramModel(order=4),
        "HMM (states=6)": HMMModel(n_states=6),
        "Naive Bayes (order=3)": NaiveBayesModel(order=3),
        "Logistic/MaxEnt (order=3)": LogisticNgramModel(order=3, epochs=15),
        "PPM (order=4)": PPMModel(max_order=4),
    }

    rng = random.Random(42)
    results: dict[str, float] = {}
    for name, model in models.items():
        try:
            t0 = time.perf_counter()
            model.train(train_labels)
            train_time = time.perf_counter() - t0

            correct = 0
            for label in test_labels:
                decoy = _random_label(rng, max(3, len(label)))
                if model.score(label) > model.score(decoy):
                    correct += 1
            acc = correct / len(test_labels)
        except Exception as exc:
            print(f"{name:28s} FAILED: {exc}")
            continue

        results[name] = acc
        print(f"{name:28s} accuracy={acc:.4f}  train_time={train_time:.2f}s")

    print("\n" + "=" * 50)
    print("Final accuracy summary")
    print("=" * 50)
    if not results:
        print("No model finished successfully.")
        return 1

    for name, acc in sorted(results.items(), key=lambda kv: -kv[1]):
        print(f"  {name:28s} {acc:.4f}")

    best_name, best_acc = max(results.items(), key=lambda kv: kv[1])
    avg_acc = sum(results.values()) / len(results)
    print(f"\nBest model    : {best_name} ({best_acc:.4f})")
    print(f"Average acc.  : {avg_acc:.4f}  ({len(results)}/{len(models)} models completed)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
