from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader


@dataclass(frozen=True)
class PDFDocument:
    path: Path
    pages: List[str]

    @property
    def text(self) -> str:
        return "\n\n".join([p.strip() for p in self.pages if p and p.strip()]).strip()


def load_pdf_text(pdf_path: str | Path, *, max_pages: int | None = None) -> PDFDocument:
    """
    Load PDF and extract text only (no OCR).
    """
    path = Path(pdf_path).expanduser().resolve()
    reader = PdfReader(str(path))

    pages: List[str] = []
    limit = min(len(reader.pages), max_pages) if max_pages else len(reader.pages)
    for i in range(limit):
        page = reader.pages[i]
        txt = page.extract_text() or ""
        pages.append(_normalize_pdf_text(txt))

    return PDFDocument(path=path, pages=pages)


def _normalize_pdf_text(s: str) -> str:
    # Basic cleanup for common PDF artifacts.
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Remove excessive spaces.
    lines = [line.strip() for line in s.split("\n")]
    # Join hyphenated line breaks: "trans-\nformer" -> "transformer"
    merged: List[str] = []
    for line in lines:
        if not line:
            merged.append("")
            continue
        if merged and merged[-1].endswith("-") and line and line[0].islower():
            merged[-1] = merged[-1][:-1] + line
        else:
            merged.append(line)
    # Collapse 3+ blank lines.
    out_lines: List[str] = []
    blank = 0
    for line in merged:
        if line == "":
            blank += 1
            if blank <= 2:
                out_lines.append(line)
        else:
            blank = 0
            out_lines.append(line)
    return "\n".join(out_lines).strip()

