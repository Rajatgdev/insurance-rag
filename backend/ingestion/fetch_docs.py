"""Download Irish motor policy PDFs + IPIDs into data/motor/raw/."""
"""Download Irish motor policy wordings into data/motor/raw/ and write a manifest.

Run from backend/:  python -m ingestion.fetch_docs

Each entry's metadata (insurer, doc_type, version_date, source_url) is written to
data/motor/raw/manifest.json so ingest_policies can tag chunks without re-hardcoding URLs.
The sandbox that generated this file can't reach these domains; run it locally.
"""
import json
from pathlib import Path

import httpx

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "motor" / "raw"

# doc_type: 'wording' (full policy booklet) | 'ipid' (short product-info doc)
# version_date: best-known effective date, ISO or None
SOURCES = [
    {
        "insurer": "AIG",
        "doc_type": "wording",
        "version_date": "2026-03-18",
        "filename": "aig_private_motor.pdf",
        "url": "https://www.aig.ie/content/dam/aig/emea/ireland/documents/policy-documents/2026/2026-03-18-aig-car-policy.pdf.coredownload.pdf",
    },
    {
        "insurer": "Zurich",
        "doc_type": "wording",
        "version_date": "2026-03-01",
        "filename": "zurich_private_car.pdf",
        "url": "https://www.arachas.ie/media/l2vd15cv/zurich-car-policy_03-2026.pdf",
    },
    {
        "insurer": "AXA",
        "doc_type": "wording",
        "version_date": "2024-10-01",
        "filename": "axa_private_car.pdf",
        "url": "https://www.arachas.ie/media/0jgpro3b/oct-2024-axa-private-car-policy-booklet.pdf",
    },
    {
        "insurer": "KennCo",
        "doc_type": "wording",
        "version_date": "2026-06-01",
        "filename": "kennco_choice_car.pdf",
        "url": "https://www.arachas.ie/media/ymumsgon/kennco-choice-car-policy-wording-wef-june-2026.pdf",
    },
    {
        "insurer": "RSA",
        "doc_type": "wording",
        "version_date": None,
        "filename": "rsa_private_motor.pdf",
        "url": "https://www.howdeninsurance.ie/media/y3oagcpn/rsa-booklet.pdf",
    },
    {
        "insurer": "Travelers (123.ie)",
        "doc_type": "wording",
        "version_date": None,
        "filename": "travelers_123_private_motor.pdf",
        "url": "https://www.123.ie/downloads/motorpolicy.pdf",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (motor-copilot ingestion; research PoC)"}


def fetch_all() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fetched = []

    with httpx.Client(follow_redirects=True, timeout=60.0, headers=HEADERS) as client:
        for src in SOURCES:
            dest = RAW_DIR / src["filename"]
            if dest.exists() and dest.stat().st_size > 0:
                print(f"  skip (exists)  {src['filename']}")
                fetched.append(src)
                continue
            try:
                resp = client.get(src["url"])
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                kb = len(resp.content) // 1024
                print(f"  ok  {src['insurer']:<18} {kb:>5} KB  -> {src['filename']}")
                fetched.append(src)
            except Exception as e:
                print(f"  FAIL  {src['insurer']:<18} {e}")

    manifest = RAW_DIR / "manifest.json"
    manifest.write_text(json.dumps(fetched, indent=2))
    print(f"\n{len(fetched)}/{len(SOURCES)} sources ready. Manifest: {manifest}")


if __name__ == "__main__":
    fetch_all()