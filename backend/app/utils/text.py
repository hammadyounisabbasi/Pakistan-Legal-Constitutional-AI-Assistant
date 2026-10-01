import html
import re
import unicodedata

# Keep source literals ASCII-only so Windows code-page changes cannot corrupt
# the repair table itself.
MOJIBAKE_REPLACEMENTS = {
    "\u00e2\u0080\u0094": "\u2014",
    "\u00e2\u0080\u0093": "\u2013",
    "\u00e2\u0080\u0099": "\u2019",
    "\u00e2\u0080\u0098": "\u2018",
    "\u00e2\u0080\u009c": "\u201c",
    "\u00e2\u0080\u009d": "\u201d",
    "\u00e2\u0080\u00a6": "\u2026",
    "\u00e2\u20ac\u201d": "\u2014",
    "\u00e2\u20ac\u201c": "\u2013",
    "\u00e2\u20ac\u2122": "\u2019",
    "\u00e2\u20ac\u02dc": "\u2018",
    "\u00e2\u20ac\u0153": "\u201c",
    "\u00e2\u20ac\u009d": "\u201d",
    "\u00e2\u20ac\u00a6": "\u2026",
    "\u00c2\u00ad": "-",
    "\u00c2": "",
    "\u037e": "?",
    "\u2011": "-",
}


def clean_display_text(value: str) -> str:
    """Normalize extracted/model text without damaging Urdu characters."""
    text = html.unescape(value or "")
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    for broken, replacement in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(broken, replacement)
    text = text.replace("\u00ad", "-").replace("\ufeff", "")
    text = unicodedata.normalize("NFC", text)
    normalized = []
    for character in text:
        category = unicodedata.category(character)
        if category.startswith("Z"):
            normalized.append(" ")
        elif character in "\n\t" or category != "Cc":
            normalized.append(character)
    text = "".join(normalized)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
