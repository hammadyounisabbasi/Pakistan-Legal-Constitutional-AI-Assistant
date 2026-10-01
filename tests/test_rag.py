import asyncio

from backend.app.core.config import Settings
from backend.app.llm.base import LLMResult
from backend.app.rag.service import RAGService
from backend.app.vectorstore.base import SearchResult


class FakeStore:
    def __init__(self, results=None):
        self.results = results or []

    def search(self, _query, limit=8, where=None):
        return self.results[:limit]


class ExactProvisionStore:
    def __init__(self):
        base = dict(evidence().metadata)
        base.pop("article", None)
        base["title"] = "Pakistan Penal Code, 1860"
        self.wrong = SearchResult(
            "Section 377 text", {**base, "section": "377", "chunk_index": 1}, 0.9
        )
        self.correct = SearchResult(
            "Section 302 punishment text",
            {**base, "section": "302", "chunk_index": 2},
            0.1,
        )

    def search(self, _query, limit=8, where=None):
        return [self.correct] if where == {"section": "302"} else [self.wrong]


class FakeProviders:
    def __init__(self, value=None):
        self.value = value

    async def generate(self, _system, _prompt):
        return self.value


class NaturalArrestStore:
    def __init__(self):
        self.filters = []
        self.base = {
            "document_id": "crpc",
            "title": "Code of Criminal Procedure, 1898",
            "source_name": "Pakistan Code",
            "source_url": "https://pakistancode.gov.pk/crpc.pdf",
            "document_type": "federal_statute",
            "effective_status": "official",
        }

    def search(self, _query, limit=8, where=None):
        self.filters.append(where)
        if where and "$and" in where:
            fields = {key: value for part in where["$and"] for key, value in part.items()}
            number = fields.get("article") or fields.get("section")
            title = fields["title"]
            metadata = {
                **self.base,
                "title": title,
                "document_id": f"doc-{number}",
                "chunk_index": int(number),
            }
            if "article" in fields:
                metadata["article"] = number
            else:
                metadata["section"] = number
            return [SearchResult(f"Provision {number} text", metadata, 0.1)]
        return []


def evidence(score=0.82):
    return SearchResult(
        "Article 25 states that all citizens are equal before law.",
        {
            "document_id": "constitution", "title": "Constitution of Pakistan, 1973",
            "source_name": "National Assembly of Pakistan",
            "source_url": "https://na.gov.pk/constitution.pdf", "document_type": "constitution",
            "article": "25", "effective_status": "current",
        },
        score,
    )


def test_grounded_answer_maps_real_citation():
    rag = RAGService(Settings(), FakeStore([evidence()]), FakeProviders(LLMResult("Equality is protected [S1].", "fake")))
    response = asyncio.run(rag.answer("What does Article 25 mean?", []))
    assert response.grounding == "rag"
    assert response.sources[0].id == "constitution"
    assert str(response.sources[0].source_url).startswith("https://na.gov.pk/")


def test_invalid_citation_marker_is_removed():
    rag = RAGService(Settings(), FakeStore([evidence()]), FakeProviders(LLMResult("Supported [S1], invented [S9].", "fake")))
    response = asyncio.run(rag.answer("Explain Article 25", []))
    assert "[S1]" in response.answer
    assert "[S9]" not in response.answer


def test_missing_evidence_and_provider_returns_safe_failure():
    rag = RAGService(Settings(), FakeStore(), FakeProviders())
    response = asyncio.run(rag.answer("What does Article 25 mean?", []))
    assert response.grounding == "none"
    assert response.sources == []
    assert "could not verify" in response.answer


def test_llm_fallback_is_labelled_unverified():
    rag = RAGService(Settings(), FakeStore(), FakeProviders(LLMResult("A cautious overview.", "fake")))
    response = asyncio.run(rag.answer("What does Article 25 mean?", []))
    assert response.grounding == "unverified_llm"
    assert "not verified against" in response.answer.casefold()


def test_provider_failure_with_evidence_uses_extractive_answer():
    rag = RAGService(Settings(), FakeStore([evidence()]), FakeProviders())
    response = asyncio.run(rag.answer("What does Article 25 mean?", []))
    assert response.grounding == "rag"
    assert "extractive response" in response.answer


def test_exact_section_metadata_outranks_semantic_result():
    rag = RAGService(Settings(), ExactProvisionStore(), FakeProviders())
    response = asyncio.run(rag.answer("Section 302 PPC kya hai?", []))
    assert "Section 302 punishment text" in response.answer
    assert response.sources[0].provision == "Section 302"


def test_natural_arrest_question_fetches_exact_rights_provisions():
    store = NaturalArrestStore()
    rag = RAGService(Settings(), store, FakeProviders())
    response = asyncio.run(rag.answer("Police ne bina warrant giraftar kiya, rights?", []))
    provisions = {source.provision for source in response.sources}
    assert {"Article 10", "Section 54", "Section 60", "Section 61"} <= provisions
    assert any(
        where
        == {
            "$and": [
                {"section": "54"},
                {"title": "Code of Criminal Procedure, 1898"},
            ]
        }
        for where in store.filters
    )
