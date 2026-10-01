import re
import time
import uuid

from backend.app.core.config import Settings
from backend.app.core.logging import get_logger
from backend.app.llm.factory import ProviderChain
from backend.app.rag.entities import extract_entities, implicit_legal_filters, normalize_query
from backend.app.rag.prompts import SYSTEM_PROMPT, build_prompt
from backend.app.schemas.chat import ChatResponse, SourceCitation
from backend.app.security.scope_guard import ScopeGuard
from backend.app.services.language import detect_language
from backend.app.utils.text import clean_display_text

logger = get_logger(__name__)
DISCLAIMER = "Legal information only - not legal advice or a lawyer-client relationship. Verify important matters from the official text and a qualified Pakistani lawyer."


class RAGService:
    def __init__(self, settings: Settings, vector_store, provider_chain: ProviderChain):
        self.settings = settings
        self.vector_store = vector_store
        self.providers = provider_chain
        self.scope_guard = ScopeGuard()

    async def answer(self, message: str, history: list[dict[str, str]]) -> ChatResponse:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        language = detect_language(message)
        decision = self.scope_guard.classify(message, history)

        if decision.scope == "out_of_scope":
            return self._response(
                "I am designed to assist only with Pakistani legal, constitutional, and judicial information.",
                "out_of_scope", "none", language, request_id, [], started,
            )
        if decision.scope == "unclear":
            return self._response(
                "Could you clarify how your question relates to Pakistani law or the Pakistani legal system?",
                "unclear", "none", language, request_id, [], started,
            )

        entities = extract_entities(message)
        query = normalize_query(message, entities)
        retrieval_started = time.perf_counter()
        try:
            exact = []
            if entities.article:
                exact.extend(
                    self.vector_store.search(
                        query, limit=5, where={"article": entities.article}
                    )
                )
                exact.extend(
                    self.vector_store.search(
                        query,
                        limit=2,
                        where={
                            "$and": [
                                {"section": entities.article},
                                {
                                    "title": (
                                        "Constitution of the Islamic Republic of Pakistan, 1973"
                                    )
                                },
                            ]
                        },
                    )
                )
            if entities.section:
                exact.extend(
                    self.vector_store.search(
                        query, limit=5, where={"section": entities.section}
                    )
                )
            for provision_filter in implicit_legal_filters(message, entities):
                exact.extend(
                    self.vector_store.search(query, limit=2, where=provision_filter)
                )
            semantic = self.vector_store.search(query, limit=10)
            exact_keys = {
                (item.metadata.get("document_id"), item.metadata.get("chunk_index"))
                for item in exact
            }
            raw = exact + [
                item
                for item in semantic
                if (item.metadata.get("document_id"), item.metadata.get("chunk_index"))
                not in exact_keys
            ]
        except Exception as exc:
            logger.warning("retrieval_failed", request_id=request_id, error=type(exc).__name__)
            exact = []
            raw = []
        retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)

        exact_ids = {id(item) for item in exact}
        # Weak semantic matches are more harmful than a clearly labelled general answer:
        # they can make unrelated provisions look authoritative for the user's situation.
        candidates = [item for item in raw if item.relevance >= 0.55 or id(item) in exact_ids]
        candidates.sort(
            key=lambda item: self._legal_rank(item, entities)
            + (2.0 if id(item) in exact_ids else 0.0),
            reverse=True,
        )
        preferred = [item for item in candidates if id(item) in exact_ids] or candidates
        selected = self._unique_provisions(preferred, limit=5)
        citations = self._citations(selected)

        if selected:
            evidence = [
                (f"S{i}", self._evidence_block(item))
                for i, item in enumerate(selected, 1)
            ]
            llm_started = time.perf_counter()
            result = await self.providers.generate(SYSTEM_PROMPT, build_prompt(message, language, evidence))
            llm_ms = round((time.perf_counter() - llm_started) * 1000, 2)
            if result:
                answer = clean_display_text(
                    self._validate_markers(result.text, len(citations))
                )
                grounding = "rag" if exact or selected[0].relevance >= 0.55 else "partial_rag"
                logger.info("rag_answer", request_id=request_id, provider=result.provider, retrieval_ms=retrieval_ms, llm_ms=llm_ms)
            else:
                answer = self._deterministic_answer(selected, language)
                grounding = "rag"
                logger.info("rag_deterministic_answer", request_id=request_id, retrieval_ms=retrieval_ms)
            return self._response(answer, "pakistan_law", grounding, language, request_id, citations, started)

        result = await self.providers.generate(
            SYSTEM_PROMPT,
            f"""No matching passage is available in the local legal knowledge base.
USER LANGUAGE: {language}
Answer this Pakistan-related question from your general knowledge in the user's natural language.
If USER LANGUAGE is roman_urdu, write in clear Latin-script Roman Urdu, not Urdu script. Be
professional, practical, easy to understand, and cautious. Use this compact structure only: a direct
answer, 3 to 5 practical steps, when urgent help is appropriate, and one limitation. Do not use a
table. Do not invent or name an exact Pakistani Article, section, case, deadline, authority,
board, department, penalty, or legal classification. Clearly distinguish general guidance from
verified law, mention what facts could change the answer, and suggest proportionate next steps.
Do not recommend an FIR or criminal complaint unless the facts described plausibly involve a crime
or immediate safety risk. For ordinary disputes, prefer records, a written complaint to the relevant
organization, escalation through its management, and advice from an appropriate professional.
Do not use source markers because no local source was retrieved.

QUESTION: {message}""",
        )
        if result:
            answer = clean_display_text(result.text) + (
                "\n\n**Verification note:** This is general AI guidance and was not verified "
                "against a matching passage in the local authoritative legal knowledge base."
            )
            grounding = "unverified_llm"
        else:
            answer = "I could not verify an answer from the indexed official sources. Please check the relevant official Pakistani source or consult a qualified Pakistani legal professional."
            grounding = "none"
        return self._response(answer, "pakistan_law", grounding, language, request_id, [], started)

    @staticmethod
    def _legal_rank(item, entities) -> float:
        meta = item.metadata
        score = item.relevance
        if entities.article and str(meta.get("article", "")).casefold() == entities.article.casefold():
            score += 1.0
        if entities.section and str(meta.get("section", "")).casefold() == entities.section.casefold():
            score += 1.0
        if entities.act and entities.act.casefold() in str(meta.get("title", "")).casefold():
            score += 0.2
        return score

    @staticmethod
    def _citations(selected) -> list[SourceCitation]:
        seen, citations = set(), []
        for item in selected:
            meta = item.metadata
            key = (
                meta.get("document_id"),
                meta.get("chunk_index"),
                meta.get("article"),
                meta.get("section"),
            )
            if key in seen or not all([meta.get("document_id"), meta.get("title"), meta.get("source_url")]):
                continue
            seen.add(key)
            is_constitution = "constitution" in str(meta.get("title", "")).casefold()
            provision = (
                (f"Article {meta['article']}" if meta.get("article") else None)
                or (
                    f"Article {meta['section']}"
                    if is_constitution and meta.get("section")
                    else None
                )
                or (f"Section {meta['section']}" if meta.get("section") else None)
                or meta.get("provision")
            )
            citations.append(SourceCitation(
                id=meta["document_id"], title=clean_display_text(meta["title"]),
                source_name=clean_display_text(
                    meta.get("source_name", "Official Pakistani source")
                ),
                source_url=meta["source_url"], document_type=meta.get("document_type", "legal_document"),
                provision=clean_display_text(provision) if provision else None,
                effective_status=meta.get("effective_status"),
                excerpt=clean_display_text(item.text[:280]),
            ))
        return citations

    @staticmethod
    def _unique_provisions(candidates, limit: int):
        selected = []
        seen = set()
        for item in candidates:
            meta = item.metadata
            provision = (
                ("article", str(meta.get("article")))
                if meta.get("article")
                else ("section", str(meta.get("section")))
                if meta.get("section")
                else ("chunk", str(meta.get("chunk_index")))
            )
            key = (meta.get("document_id"), provision)
            if key in seen:
                continue
            seen.add(key)
            selected.append(item)
            if len(selected) == limit:
                break
        return selected

    @staticmethod
    def _evidence_block(item) -> str:
        meta = item.metadata
        provision = None
        is_constitution = "constitution" in str(meta.get("title", "")).casefold()
        if meta.get("article"):
            provision = f"Article {meta['article']}"
        elif is_constitution and meta.get("section"):
            provision = f"Article {meta['section']}"
        elif meta.get("section"):
            provision = f"Section {meta['section']}"
        else:
            provision = meta.get("provision")
        return "\n".join(
            (
                f"SOURCE TITLE: {clean_display_text(str(meta.get('title', 'Unknown')))}",
                f"PROVISION: {clean_display_text(str(provision or 'Not specified'))}",
                f"STATUS: {clean_display_text(str(meta.get('effective_status', 'Not specified')))}",
                f"EXCERPT: {clean_display_text(item.text[:4000])}",
            )
        )

    @staticmethod
    def _validate_markers(text: str, source_count: int) -> str:
        return re.sub(r"\[S(\d+)\]", lambda m: m.group(0) if int(m.group(1)) <= source_count else "", text)

    @staticmethod
    def _deterministic_answer(selected, language: str) -> str:
        excerpts = "\n\n".join(
            f"[S{i}] {clean_display_text(item.text[:650])}"
            for i, item in enumerate(selected[:3], 1)
        )
        lead = "Indexed official-source excerpts relevant to your question:" if language == "english" else "Aap ke sawal se mutaliq indexed official-source excerpts:"
        return f"{lead}\n\n{excerpts}\n\nThe configured language model was unavailable, so this is an extractive response."

    @staticmethod
    def _response(answer, scope, grounding, language, request_id, sources, started):
        logger.info("chat_complete", request_id=request_id, scope=scope, grounding=grounding, total_ms=round((time.perf_counter() - started) * 1000, 2))
        return ChatResponse(answer=answer, scope=scope, grounding=grounding, sources=sources, language=language, request_id=request_id, disclaimer=DISCLAIMER)
