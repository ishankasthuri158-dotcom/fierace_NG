"""Turn a trained n-gram model into ranked subdomain candidates (Day 5)."""
from __future__ import annotations

from .ngram import CharNgramModel
from .train import default_model
from .corpus import COMMON_SUBDOMAINS


class SubdomainPredictor:
    def __init__(self, model: CharNgramModel | None = None, model_path: str | None = None):
        if model is not None:
            self.model = model
        elif model_path:
            self.model = CharNgramModel.load(model_path)
        else:
            self.model = default_model()

    def predict(self, n: int = 200, seed: int | None = 1337) -> list[str]:
        """Produce up to ``n`` candidate labels, ranked most-plausible first.

        Combines two sources and ranks the union by model likelihood:
          * generated labels sampled from the model, and
          * the common-subdomain vocabulary (re-ranked to this model's taste).
        """
        generated = self.model.generate(n=n, seed=seed)
        pool = set(generated) | set(COMMON_SUBDOMAINS)
        ranked = self.model.rank(pool)
        return [label for label, _ in ranked[:n]]

    def rank_existing(self, candidates) -> list[tuple[str, float]]:
        """Score a caller-supplied candidate list (e.g. a big wordlist)."""
        return self.model.rank(candidates)
