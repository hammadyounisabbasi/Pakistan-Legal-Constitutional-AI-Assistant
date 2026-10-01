import re

URDU_RANGE = re.compile(r"[\u0600-\u06ff]")
ROMAN_URDU = re.compile(
    r"\b(kya|hai|hain|mein|mujhe|mera|meri|ka|ki|ke|aur|se|ko|samjhao|qanoon|haq|huqooq)\b",
    re.IGNORECASE,
)


def detect_language(text: str) -> str:
    urdu = len(URDU_RANGE.findall(text))
    roman = len(ROMAN_URDU.findall(text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if urdu and latin:
        return "mixed"
    if urdu:
        return "urdu"
    if roman >= 2:
        return "roman_urdu"
    return "english"

