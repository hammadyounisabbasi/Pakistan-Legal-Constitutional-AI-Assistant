import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LegalEntities:
    article: str | None = None
    section: str | None = None
    act: str | None = None


def extract_entities(query: str) -> LegalEntities:
    article = re.search(
        r"\b(?:article|\u0622\u0631\u0679\u06cc\u06a9\u0644)\s*([0-9]+[A-Za-z-]*)",
        query,
        re.IGNORECASE,
    )
    section = re.search(
        r"\b(?:section|dafa|\u062f\u0641\u0639\u06c1)\s*([0-9]+[A-Za-z-]*)",
        query,
        re.IGNORECASE,
    )
    lowered = query.casefold()
    act = None
    if "ppc" in lowered or "penal code" in lowered:
        act = "Pakistan Penal Code, 1860"
        if not section:
            section = re.search(
                r"(?:\bppc\s*|\b)([0-9]+[A-Za-z-]*)\s*ppc\b|\bppc\s*([0-9]+[A-Za-z-]*)",
                query,
                re.IGNORECASE,
            )
    elif "crpc" in lowered or "criminal procedure" in lowered:
        act = "Code of Criminal Procedure, 1898"
    elif "constitution" in lowered or article:
        act = "Constitution of the Islamic Republic of Pakistan, 1973"
    return LegalEntities(
        article=article.group(1) if article else None,
        section=(
            section.group(1)
            or (section.group(2) if section.lastindex and section.lastindex > 1 else None)
        )
        if section
        else None,
        act=act,
    )


def normalize_query(query: str, entities: LegalEntities) -> str:
    expansions = []
    lowered = query.casefold()
    concepts = {
        ("arrest", "giraftar", "detain", "police custody", "bina warrant"): (
            "arrest detention safeguards rights of arrested person Constitution Article 10 "
            "Code of Criminal Procedure"
        ),
        ("theft", "chori", "stolen"): "theft Pakistan Penal Code sections 378 379",
        ("equality", "barabari", "equal treatment"): "equality of citizens Constitution Article 25",
        ("speech", "bolne", "expression"): "freedom of speech Constitution Article 19",
        ("bail", "zamanat"): "bail Code of Criminal Procedure",
        ("fir", "first information report"): "FIR first information report criminal procedure",
    }
    for signals, expansion in concepts.items():
        if any(signal in lowered for signal in signals):
            expansions.append(expansion)
    if entities.article:
        expansions.append(f"constitutional Article {entities.article}")
    if entities.section:
        expansions.append(f"statutory Section {entities.section}")
    if entities.act:
        expansions.append(entities.act)
    return " ".join([query.strip(), *expansions])


def implicit_legal_filters(query: str, entities: LegalEntities) -> list[dict]:
    """Map common natural-language intents to narrow, authoritative provisions."""
    if entities.article or entities.section:
        return []

    lowered = query.casefold()
    rules = (
        (
            ("arrest", "giraftar", "detain", "police custody", "bina warrant"),
            (
                ("section", "10", "Constitution of the Islamic Republic of Pakistan, 1973"),
                ("section", "54", "Code of Criminal Procedure, 1898"),
                ("section", "60", "Code of Criminal Procedure, 1898"),
                ("section", "61", "Code of Criminal Procedure, 1898"),
            ),
        ),
        (
            ("theft", "chori", "stolen"),
            (
                ("section", "378", "Pakistan Penal Code, 1860"),
                ("section", "379", "Pakistan Penal Code, 1860"),
            ),
        ),
        (
            ("equality", "barabari", "equal treatment"),
            (("section", "25", "Constitution of the Islamic Republic of Pakistan, 1973"),),
        ),
        (
            ("speech", "bolne", "expression"),
            (("section", "19", "Constitution of the Islamic Republic of Pakistan, 1973"),),
        ),
    )
    filters = []
    for signals, provisions in rules:
        if any(signal in lowered for signal in signals):
            filters.extend(
                {"$and": [{field: number}, {"title": title}]}
                for field, number, title in provisions
            )
            break
    return filters
