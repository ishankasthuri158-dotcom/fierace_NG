"""Train all five subdomain-scoring models on one corpus, saving each in turn.

Usage:
    python -m ml_predictor.train_all                          # built-in corpus
    python -m ml_predictor.train_all data/subdomains_clean.txt # external corpus
    python -m ml_predictor.train_all data/subdomains_clean.txt models
"""
from __future__ import annotations

import os
import sys

from .corpus import COMMON_SUBDOMAINS
from .train import labels_from_lines
from .ngram import CharNgramModel
from .hmm import HMMModel
from .naive_bayes import NaiveBayesModel
from .logistic import LogisticNgramModel
from .ppm import PPMModel


def load_labels(corpus_path: str | None) -> list[str]:
    if not corpus_path:
        return COMMON_SUBDOMAINS
    with open(corpus_path, "r", encoding="utf-8", errors="ignore") as fh:
        return labels_from_lines(fh)


def main(argv: list[str]) -> int:
    corpus_path = argv[0] if len(argv) > 0 else None
    out_dir = argv[1] if len(argv) > 1 else "models"
    os.makedirs(out_dir, exist_ok=True)

    labels = load_labels(corpus_path)
    source = corpus_path or "built-in corpus"
    print(f"Training on {len(labels)} labels from {source}\n")

    models = {
        "ngram": CharNgramModel(order=4),
        "hmm": HMMModel(n_states=6),
        "naive_bayes": NaiveBayesModel(order=3),
        "logistic": LogisticNgramModel(order=3, epochs=15),
        "ppm": PPMModel(max_order=4),
    }

    for name, model in models.items():
        print(f"Training {name}...")
        model.train(labels)
        out_path = os.path.join(out_dir, f"{name}.pkl")
        model.save(out_path)
        print(f"  Saved -> {out_path}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
