"""Train the subdomain n-gram model (Day 5).

Usage as a script:
    python -m ml_predictor.train                 # train on built-in corpus
    python -m ml_predictor.train big_corpus.txt  # train on Rapid7/SecLists file
    python -m ml_predictor.train corpus.txt models/subs.json --order 4

A corpus file is one hostname or bare label per line. Full hostnames like
``dev.api.example.com`` are reduced to their labels (``dev``, ``api``).
"""
from __future__ import annotations

import sys

from .ngram import CharNgramModel
from .corpus import COMMON_SUBDOMAINS


def labels_from_lines(lines) -> list[str]:
    """Extract subdomain labels from raw corpus lines (drop the apex/TLD)."""
    labels: list[str] = []
    for line in lines:
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        parts = line.split(".")
        # Heuristic: for a full hostname keep everything except the last two
        # labels (registrable domain); for a bare label keep it as-is.
        chosen = parts[:-2] if len(parts) > 2 else parts[:1]
        labels.extend(p for p in chosen if p)
    return labels


def train_from_labels(labels, order: int = 3, smoothing: float = 0.1) -> CharNgramModel:
    return CharNgramModel(order=order, smoothing=smoothing).train(labels)


def train_from_file(path: str, order: int = 3, smoothing: float = 0.1) -> CharNgramModel:
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        labels = labels_from_lines(fh)
    return train_from_labels(labels, order=order, smoothing=smoothing)


def default_model(order: int = 3) -> CharNgramModel:
    """A model trained on the built-in corpus -- always available."""
    return train_from_labels(COMMON_SUBDOMAINS, order=order)


def _main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    order = 3
    for a in argv:
        if a.startswith("--order"):
            order = int(a.split("=")[-1]) if "=" in a else 3

    corpus = args[0] if len(args) > 0 else None
    out = args[1] if len(args) > 1 else "models/subdomains.pkl"

    if corpus:
        model = train_from_file(corpus, order=order)
        print(f"Trained on {model.trained_on} labels from {corpus}")
    else:
        model = default_model(order=order)
        print(f"Trained on {model.trained_on} built-in labels")

    import os
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    model.save(out)
    print(f"Saved model -> {out} (order={order}, contexts={len(model.counts)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
