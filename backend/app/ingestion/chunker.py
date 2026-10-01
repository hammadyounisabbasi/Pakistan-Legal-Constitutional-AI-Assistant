import re
from dataclasses import dataclass

HEADING = re.compile(
    r"(?im)^(?:(?P<label>article|section|chapter|part)\s+(?P<number>[0-9IVXLC]+[A-Z-]*)\b[^\n]*|(?P<bare>[0-9]+[A-Z-]*)\.\s+[A-Z][^\n]{3,})"
)


@dataclass(slots=True)
class Chunk:
    text: str
    metadata: dict


def legal_chunks(text: str, target_chars: int = 1800, overlap: int = 220) -> list[Chunk]:
    if not text.strip():
        return []
    starts = list(HEADING.finditer(text))
    sections = []
    if starts:
        if starts[0].start() > 0:
            sections.append((text[:starts[0].start()], {}))
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            label = match.group("label").casefold() if match.group("label") else "section"
            number = match.group("number") or match.group("bare")
            meta = {label: number, "provision": match.group(0).strip()[:180]}
            sections.append((text[match.start():end], meta))
    else:
        sections = [(text, {})]

    output = []
    for section, meta in sections:
        position = 0
        while position < len(section):
            end = min(len(section), position + target_chars)
            if end < len(section):
                boundary = max(section.rfind("\n", position, end), section.rfind(". ", position, end))
                if boundary > position + target_chars // 2:
                    end = boundary + 1
            piece = section[position:end].strip()
            if len(piece) >= 80:
                output.append(Chunk(piece, dict(meta)))
            if end >= len(section):
                break
            position = max(position + 1, end - overlap)
    return output
