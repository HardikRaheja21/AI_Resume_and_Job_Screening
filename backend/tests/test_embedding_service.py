import threading
import numpy as np
import pytest

from backend.services import embedding_service as es


class DummyModel:
    def __init__(self, name: str):
        self.name = name

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
        # deterministic small embeddings for testing
        arr = np.array([[float(len(t))] * 8 for t in texts], dtype="float32")
        return arr


def _setup_dummy(monkeypatch):
    # ensure clean state
    monkeypatch.setattr(es, "SentenceTransformer", DummyModel)
    monkeypatch.setattr(es, "sentence_transformers_util", None)
    monkeypatch.setattr(es.settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    monkeypatch.setattr(es, "_MODEL", None)


def test_shared_model_reuse(monkeypatch):
    _setup_dummy(monkeypatch)

    ids = []

    def target():
        m = es.get_model()
        ids.append(id(m))

    threads = [threading.Thread(target=target) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ids) == 6
    assert len(set(ids)) == 1, "All threads should receive the same model instance"


def test_cached_embedding_cache(monkeypatch):
    _setup_dummy(monkeypatch)
    # call twice, lru_cache should return same object instance
    a1 = es.cached_embedding("hello world")
    a2 = es.cached_embedding("hello world")
    assert np.array_equal(a1, a2)
    assert id(a1) == id(a2)


def test_fallback_when_disabled(monkeypatch):
    _setup_dummy(monkeypatch)
    monkeypatch.setattr(es.settings, "MATCHER_DISABLE_EMBEDDINGS", True)
    # is_embedding_available should be False
    assert not es.is_embedding_available()
    with pytest.raises(RuntimeError):
        es.get_model()
