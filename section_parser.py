from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ParsedPaper:
    title: str
    sections: Dict[str, str]
    raw_text: str

    def get(self, name: str, default: str = "") -> str:
        return self.sections.get(name, default)


_CANONICAL = [
    "title",
    "abstract",
    "introduction",
    "related work",
    "background",
    "method",
    "methods",
    "approach",
    "model",
    "experiments",
    "results",
    "discussion",
    "limitations",
    "conclusion",
    "references",
]


def parse_sections(text: str) -> ParsedPaper:
    """
    Heuristic section parsing from extracted PDF text.
    - Finds likely headings (e.g., "Abstract", "1 Introduction", "Conclusion")
    - Splits into sections, maps variants to canonical names when possible.
    """
    cleaned = _preclean(text)
    title = _guess_title(cleaned)
    headings = _find_headings(cleaned)

    if not headings:
        return ParsedPaper(title=title, sections={"body": cleaned}, raw_text=text)

    chunks = _split_by_headings(cleaned, headings)
    sections: Dict[str, str] = {}
    for h, content in chunks:
        key = _canonicalize(h)
        if key in sections:
            sections[key] = (sections[key].rstrip() + "\n\n" + content.strip()).strip()
        else:
            sections[key] = content.strip()

    return ParsedPaper(title=title, sections=sections, raw_text=text)


def _preclean(text: str) -> str:
    # Remove common running headers/footers lines that are just numbers.
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if not re.fullmatch(r"\d{1,4}", ln)]
    return "\n".join(lines).strip()


def _guess_title(text: str) -> str:
    # Take first non-empty line that looks like a title (not "arXiv:" etc.).
    for ln in text.splitlines()[:40]:
        ln = ln.strip()
        if not ln:
            continue
        if len(ln) < 6:
            continue
        if re.search(r"\barxiv\b", ln, re.I):
            continue
        if re.search(r"\bdoi\b", ln, re.I):
            continue
        if re.fullmatch(r"(abstract|introduction|contents)", ln, re.I):
            continue
        return ln
    return ""


def _find_headings(text: str) -> List[Tuple[int, str]]:
    headings: List[Tuple[int, str]] = []
    for m in re.finditer(r"(?m)^(?P<h>(\d+(\.\d+)*)\s+)?(?P<t>[A-Za-z][A-Za-z0-9 \-/]{2,60})\s*$", text):
        raw = (m.group("t") or "").strip()
        if _looks_like_heading(raw):
            headings.append((m.start(), raw))

    # Prefer unique-ish headings, keep order.
    dedup: List[Tuple[int, str]] = []
    seen: set[str] = set()
    for pos, h in headings:
        k = h.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append((pos, h))
    return dedup


def _looks_like_heading(h: str) -> bool:
    hl = h.lower().strip(":").strip()
    if len(hl) < 3:
        return False
    if hl in {"keywords", "acknowledgements", "acknowledgments"}:
        return True
    if any(hl == c for c in _CANONICAL):
        return True
    if any(hl.endswith(" " + c) for c in _CANONICAL):
        return True
    if re.fullmatch(r"(abstract|introduction|conclusion|references|related work|method|methods|experiments|results|discussion|limitations)", hl):
        return True
    return False


def _split_by_headings(text: str, headings: List[Tuple[int, str]]) -> List[Tuple[str, str]]:
    # Convert heading positions to slices.
    sorted_h = sorted(headings, key=lambda x: x[0])
    out: List[Tuple[str, str]] = []
    for i, (pos, h) in enumerate(sorted_h):
        start = pos
        end = sorted_h[i + 1][0] if i + 1 < len(sorted_h) else len(text)
        block = text[start:end].strip()
        # Remove the heading line itself.
        block_lines = block.splitlines()
        content = "\n".join(block_lines[1:]).strip() if len(block_lines) > 1 else ""
        out.append((h, content))
    return out


def _canonicalize(h: str) -> str:
    hl = h.lower().strip().strip(":")
    hl = re.sub(r"\s+", " ", hl)
    # Normalize some variants.
    mapping = {
        "methods": "method",
        "methodology": "method",
        "approach": "method",
        "experiments": "experiments",
        "results": "results",
        "conclusions": "conclusion",
        "related work": "related work",
        "background": "background",
        "limitations": "limitations",
        "discussion": "discussion",
        "references": "references",
        "abstract": "abstract",
        "introduction": "introduction",
    }
    for k, v in mapping.items():
        if hl == k:
            return v
    # Handle "1 Introduction" style already extracted as "Introduction".
    if hl in mapping:
        return mapping[hl]
    return hl

