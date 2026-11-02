"""Visible editorial punctuation policy; never rewrite code or link targets."""

import html
import re

from bs4 import BeautifulSoup


PROTECTED = re.compile(
    r"(?ms)^```[^\n]*\n.*?^```[^\n]*$|^~~~[^\n]*\n.*?^~~~[^\n]*$|"
    r"<(?:pre|code)\b[^>]*>.*?</(?:pre|code)>|"
    r"`+[^`\n]*`+|<[^>]+>|\]\([^)\n]*\)|https?://[^\s<>\"')]+"
)


def normalize_editorial_dashes(text):
    """Replace prose separators, including headings/metadata, before review."""
    pieces = []
    start = 0
    for match in PROTECTED.finditer(text):
        pieces.append(_normalize(text[start:match.start()]))
        pieces.append(match.group())
        start = match.end()
    pieces.append(_normalize(text[start:]))
    return "".join(pieces)


def _normalize(text):
    text = re.sub(r"&(?:mdash|ndash|#821[12]|#x201[34]);", "\u2014", text, flags=re.I)
    text = re.sub(r"(?<=\d)[ \t]*[–—][ \t]*(?=\d)", " to ", text)
    return re.sub(r"[ \t]*[–—][ \t]*|[ \t]+--[ \t]+", ": ", text)


def has_editorial_dashes(text):
    return normalize_editorial_dashes(text) != text


def visible_html_dashes(text):
    soup = BeautifulSoup(text, "html.parser")
    for node in soup.select("pre, code, script, style"):
        node.decompose()
    visible = soup.get_text(" ")
    visible = re.sub(r"https?://[^\s<>]+", "", visible)
    return bool(re.search("[–—]", html.unescape(visible)))
