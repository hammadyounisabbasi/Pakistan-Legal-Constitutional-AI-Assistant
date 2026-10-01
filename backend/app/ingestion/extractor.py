import io
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader

from backend.app.utils.text import clean_display_text


def extract_text(content: bytes, content_type: str, url: str) -> str:
    lowered = content_type.casefold()
    if "pdf" in lowered or url.casefold().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif "html" in lowered or content.lstrip().startswith((b"<!DOCTYPE", b"<html")):
        soup = BeautifulSoup(content, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "noscript"]):
            element.decompose()
        text = soup.get_text("\n")
    else:
        text = content.decode("utf-8", errors="replace")
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return clean_display_text(text)
