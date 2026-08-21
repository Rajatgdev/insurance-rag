"""Parse motor PDFs -> structure-aware chunks -> data/motor/chunks.jsonl

Run from backend/:  python -m ingestion.ingest_policies

DB-free and offline on purpose: isolates the heuristic chunker so you can eyeball every
chunk boundary and is_exclusion flag before embeddings / Neon. Reads raw/manifest.json.

Tuned to the 6 Irish wordings from a font/heading/exclusion diagnostic:
  - headings detected by KNOWN VOCABULARY first (font size is inconsistent across insurers),
    then larger-than-body size, then all-caps, all with a word-count guard
  - Contents/Index pages, cover branding (giant fonts) and phone/number lines are dropped
  - split-line titles (e.g. RSA "Section 1" + "Legal Liability...") are merged
  - is_exclusion is driven by the governing heading (vocab is now pinned per insurer)
"""
import json
import re
import statistics
from pathlib import Path

import fitz  # pymupdf

DATA = Path(__file__).resolve().parent.parent / "data" / "motor"
RAW = DATA / "raw"
OUT = DATA / "chunks.jsonl"

SOFT_MAX_CHARS = 1500     # past this, split at the next clause boundary
HARD_MAX_CHARS = 2400     # past this, force-split even without a boundary (dense prose / bullet lists)
BRAND_DELTA = 11          # font > body + this = cover/branding, drop

# Structural heading vocabulary seen across all 6 wordings.
HEADING_RE = re.compile(
    r"^(?:"
    r"SECTION\s+\d+|Section\s+\d+|PART\s+[\w\d]+|"
    r"General\s+Exceptions(?:\s+and\s+Conditions)?|General\s+Exclusions|General\s+Conditions|"
    r"Exceptions?\s+to\s+|"
    r"What\s+is\s+not\s+covered|We\s+(?:do|will)\s+not\s+(?:cover|pay)|"
    r"You\s+are\s+(?:also\s+)?not\s+covered|"
    r"Definitions|Endorsements|Introduction|Conditions|"
    r"The\s+Contract\s+of\s+Insurance|Data\s+Protection|"
    r"Complaints|Important\s+(?:Information|Notice)|Understanding\s+the\s+Policy|Welcome"
    r")",
    re.IGNORECASE,
)

# is_exclusion: match on the governing heading (fallback: chunk opening).
EXCL_RE = re.compile(
    r"(?:general\s+)?(?:exclusion|exception)s?\b|what\s+is\s+not\s+covered|"
    r"we\s+(?:do|will)\s+not\s+(?:cover|pay|be\s+liable)|"
    r"you\s+are\s+(?:also\s+)?not\s+covered|not\s+covered\s+under\s+this",
    re.IGNORECASE,
)

CLAUSE_BOUNDARY_RE = re.compile(r"^(?:\d+\.\d+|\d+\.|\(\w+\)|[•▶\-])\s")
CLAUSE_ID_RE = re.compile(r"^(?:SECTION\s+)?(\d+(?:\.\d+)*)", re.IGNORECASE)
BARE_SECTION_RE = re.compile(r"^(?:SECTION|Section)\s+\d+[:\-\s]*$")   # number only, needs its title
CONNECTIVE_END = ("of", "the", "to", "and", "or", "in", "a", "by", "for", "with", "that")
TOC_TITLE_RE = re.compile(r"^(?:contents|index|contents\s+page)$", re.IGNORECASE)
DOTTED_RE = re.compile(r"\.\s?\.\s?\.")                 # TOC leaders "......"
NUMERIC_RE = re.compile(r"^[\d\s\-\+\(\)\.]{4,}$")      # page numbers / phone lines


def _body_size(doc) -> float:
    sizes = [round(s["size"], 1)
             for page in doc for b in page.get_text("dict")["blocks"]
             for l in b.get("lines", []) for s in l["spans"] if s["text"].strip()]
    return statistics.median(sizes) if sizes else 10.0


def _is_bold(span) -> bool:
    return bool(span["flags"] & 16) or "bold" in span["font"].lower()


def _raw_lines(doc):
    for pno, page in enumerate(doc, start=1):
        for b in page.get_text("dict", sort=True)["blocks"]:
            for l in b.get("lines", []):
                spans = [s for s in l["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = " ".join(s["text"] for s in spans).strip()
                yield pno, text, max(s["size"] for s in spans), any(_is_bold(s) for s in spans)


def _toc_pages(rows) -> set:
    return {pno for pno, text, *_ in rows if TOC_TITLE_RE.match(text) and len(text.split()) <= 3}


def _keep(text, size, body) -> bool:
    """Drop cover branding, TOC leaders, bare page numbers / phone lines."""
    if size > body + BRAND_DELTA:
        return False
    if DOTTED_RE.search(text):
        return False
    if NUMERIC_RE.match(text):
        return False
    return True


def _is_heading(text, size, bold, body) -> bool:
    words = len(text.split())
    if words > 12 or text.rstrip().endswith((",", ";")):
        return False
    if text.rstrip().split()[-1].lower().strip(".") in CONNECTIVE_END:
        return False                                   # mid-sentence body line
    if HEADING_RE.match(text):
        return True
    if size >= body + 1.5:
        return True
    if text.isupper() and words <= 8:
        return True
    return False


def _clause_id(heading: str):
    m = CLAUSE_ID_RE.match(heading.strip())
    return m.group(1) if m else None


def chunk_pdf(path: Path, meta: dict) -> list[dict]:
    doc = fitz.open(path)
    body = _body_size(doc)
    rows = list(_raw_lines(doc))
    skip_pages = _toc_pages(rows)

    chunks = []
    heading = "(preamble)"
    buf, buf_page = [], 1

    def flush():
        text = "\n".join(buf).strip()
        if len(text) < 30:
            return
        chunks.append({
            "insurer": meta["insurer"], "doc_type": meta["doc_type"],
            "version_date": meta["version_date"], "source_url": meta["url"],
            "section": heading, "clause_id": _clause_id(heading),
            "is_exclusion": bool(EXCL_RE.search(heading) or EXCL_RE.search(text[:160])),
            "page": buf_page, "content": text,
        })

    for pno, text, size, bold in rows:
        if pno in skip_pages or not _keep(text, size, body):
            continue
        if _is_heading(text, size, bold, body):
            if not buf and BARE_SECTION_RE.match(heading):
                heading = f"{heading} {text}".strip()      # merge only bare "Section N" + its title
            else:
                flush()
                heading, buf, buf_page = text, [], pno
            continue
        buf.append(text)
        size_now = sum(len(x) for x in buf)
        if size_now > SOFT_MAX_CHARS and CLAUSE_BOUNDARY_RE.match(text):
            last = buf.pop()
            flush()
            buf, buf_page = [last], pno
        elif size_now > HARD_MAX_CHARS:
            flush()                                    # dense section with no boundary: force-split
            buf, buf_page = [], pno
    flush()
    doc.close()
    return chunks


def main() -> None:
    manifest = json.loads((RAW / "manifest.json").read_text())
    all_chunks = []
    for meta in manifest:
        pdf = RAW / meta["filename"]
        if not pdf.exists():
            print(f"  MISSING {meta['filename']} -- run fetch_docs first")
            continue
        cs = chunk_pdf(pdf, meta)
        all_chunks.extend(cs)
        excl = sum(c["is_exclusion"] for c in cs)
        print(f"\n=== {meta['insurer']}  |  {len(cs)} chunks, {excl} exclusion ===")
        seen = []
        for c in cs:
            if c["section"] not in seen:
                seen.append(c["section"])
        for h in seen[:40]:
            print(f"    {'X' if EXCL_RE.search(h) else ' '} {h[:70]}")

    with OUT.open("w") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"\n{len(all_chunks)} chunks -> {OUT}")


if __name__ == "__main__":
    main()