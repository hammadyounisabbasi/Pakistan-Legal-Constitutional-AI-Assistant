import math

from backend.app.embeddings.factory import HashingEmbeddings


def test_hashing_embeddings_are_deterministic_and_normalized():
    embeddings = HashingEmbeddings(128)
    first = embeddings.embed_query("Section 302 PPC kya hai?")
    second = embeddings.embed_query("Section 302 PPC kya hai?")
    assert first == second
    assert len(first) == 128
    assert math.isclose(sum(value * value for value in first), 1.0, rel_tol=1e-6)


def test_hashing_embeddings_support_urdu_text():
    vector = HashingEmbeddings(128).embed_query("آرٹیکل 25 کیا ہے؟")
    assert any(vector)
