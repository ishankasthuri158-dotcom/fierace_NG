from ml_predictor.ngram import CharNgramModel
from ml_predictor.train import default_model, labels_from_lines


def test_train_and_score_real_beats_random():
    model = default_model()
    # Real-looking labels should score higher than random gibberish.
    assert model.score("admin") > model.score("xqzwjk")
    assert model.score("api") > model.score("zzzzq9")


def test_generate_produces_valid_labels():
    model = default_model()
    labels = model.generate(n=20, seed=42)
    assert len(labels) > 0
    assert all(lbl and lbl.isascii() for lbl in labels)


def test_generate_is_deterministic_with_seed():
    model = default_model()
    assert model.generate(n=15, seed=7) == model.generate(n=15, seed=7)


def test_rank_orders_best_first():
    model = default_model()
    ranked = model.rank(["zzqx", "admin", "api"])
    names = [r[0] for r in ranked]
    assert names.index("admin") < names.index("zzqx")


def test_save_load_roundtrip(tmp_path):
    model = default_model()
    path = tmp_path / "m.json"
    model.save(str(path))
    loaded = CharNgramModel.load(str(path))
    assert abs(loaded.score("admin") - model.score("admin")) < 1e-9
    assert loaded.trained_on == model.trained_on


def test_labels_from_lines_strips_registrable_domain():
    labels = labels_from_lines(["dev.api.example.com", "www.test.org", "admin"])
    assert "dev" in labels and "api" in labels
    assert "www" in labels
    assert "admin" in labels
    assert "example" not in labels  # registrable domain dropped
