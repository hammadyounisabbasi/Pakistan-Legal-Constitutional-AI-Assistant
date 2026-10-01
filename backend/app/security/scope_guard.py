import re
from dataclasses import dataclass

PAKISTAN_MARKERS = {
    "pakistan", "pakistani", "constitution", "constitutional", "article", "section",
    "ppc", "crpc", "cpc", "court", "judge", "judgment", "law", "legal", "act",
    "ordinance", "police", "arrest", "bail", "fir", "fundamental rights", "petition",
    "supreme court", "high court", "shariat", "parliament", "senate", "national assembly",
    "qanoon", "qanun", "haq", "huqooq", "adalat", "wakeel", "waseeqa", "giraftar",
    "zamanat", "dafa", "jurisdiction", "theft", "murder", "detain", "custody",
    "chori", "talaq", "divorce", "khula", "wirasat", "inheritance", "zameen",
    "property", "tenant", "kiraya", "fraud", "dhoka", "cybercrime", "harassment",
    "domestic violence", "nikah", "maintenance", "warrant", "complaint",
    "consumer", "customer", "overcharge", "charges", "fee", "fine", "refund",
    "transport", "transporter", "bus", "conductor", "ticket", "fare", "student",
    "school", "college", "university", "hostel", "job", "salary", "employer",
    "employee", "workplace", "misbehavior", "misbehaviour", "badtameezi",
    "dhamki", "threat", "insult", "abuse", "paise", "paisa", "rasid", "receipt",
}
FOREIGN_MARKERS = {
    "american law", "us law", "united states law", "uk law", "english law",
    "indian law", "canadian law", "australian law",
}
INJECTION_MARKERS = (
    "ignore previous instructions", "reveal system prompt", "show hidden prompt",
    "act as an unrestricted", "bypass scope", "forget your rules",
)


@dataclass(frozen=True)
class ScopeDecision:
    scope: str
    confidence: float
    reason: str
    injection_detected: bool = False


class ScopeGuard:
    """Conservative multilingual scope classifier with conversation-aware intent signals.

    It deliberately avoids making an external LLM the security boundary. An optional
    semantic classifier can be added behind this interface without weakening defaults.
    """

    def classify(self, query: str, history: list[dict[str, str]] | None = None) -> ScopeDecision:
        normalized = re.sub(r"\s+", " ", query.casefold()).strip()
        injection = any(marker in normalized for marker in INJECTION_MARKERS)
        foreign_jurisdiction = any(marker in normalized for marker in FOREIGN_MARKERS) or bool(
            re.search(r"\b(american|u\.?s\.?|british|english|indian|canadian|australian)\b.*\b(law|tax|court|constitution)\b", normalized)
        )
        if foreign_jurisdiction:
            return ScopeDecision("out_of_scope", 0.98, "foreign jurisdiction requested", injection)

        explicit = sum(marker in normalized for marker in PAKISTAN_MARKERS)
        provision = bool(re.search(r"\b(article|section|dafa)\s*\d+[a-z-]*\b", normalized))
        roman_urdu = bool(re.search(
            r"\b(kya|kia|hai|hain|may|mein|mujhe|mera|meri|ham|hum|kaise|karna|"
            r"chahye|chahiye|qanoon|haq|zyada|le|raha|rahi|kary|kare)\b",
            normalized,
        ))
        legal_action = bool(re.search(
            r"\b(arrest|detain|bail|police|court|rights?|property|divorce|inheritance|"
            r"fir|crime|charges?|overcharge|refund|complaint|harass|misbehav|badtameezi|"
            r"dhamki|fraud|fee|fine|salary|tenant|consumer|transport)\w*\b",
            normalized,
        ))
        context_legal = any(
            any(marker in item.get("content", "").casefold() for marker in PAKISTAN_MARKERS)
            for item in (history or [])[-4:]
        )

        situational_question = roman_urdu and len(normalized.split()) >= 6
        if explicit >= 1 or provision or (roman_urdu and legal_action) or situational_question or (context_legal and legal_action):
            confidence = min(0.99, 0.62 + explicit * 0.1 + provision * 0.15 + context_legal * 0.08)
            return ScopeDecision("pakistan_law", confidence, "legal intent detected", injection)
        if len(normalized.split()) <= 5 and context_legal:
            return ScopeDecision("pakistan_law", 0.68, "legal conversation context", injection)
        if legal_action:
            return ScopeDecision("unclear", 0.5, "jurisdiction is unclear", injection)
        return ScopeDecision("out_of_scope", 0.88, "no Pakistan-law intent detected", injection)
