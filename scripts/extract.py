"""Download newsletter PDFs and extract per-page text into data/issues/<id>.json.

Incremental: an issue whose JSON already exists is skipped, so OCR runs once
per issue ever. Use --force ID to re-extract one issue (e.g. after CE replaces
the file), or --all to rebuild everything.

Pages with too little extractable text are treated as scanned and OCR'd with
Tesseract via PyMuPDF. Tesseract must be installed (apt: tesseract-ocr).

Usage:
    python scripts/extract.py                 # process new issues
    python scripts/extract.py --limit 5       # trial run on 5 issues
    python scripts/extract.py --pdf f.pdf --id 999   # test on a local file
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import pymupdf

from common import (CATALOG_PATH, ISSUES_DIR, LISTING_URL, REQUEST_DELAY_SECONDS,
                    BlockedError, http_get, new_session)

MAX_CONSECUTIVE_NON_PDF = 3   # this many HTML responses in a row => treat as blocked

OCR_THRESHOLD_CHARS = 40   # fewer real characters than this on a page => OCR it
OCR_DPI = 300
OCR_LANGUAGE = "eng"


def clean_text(text: str) -> str:
    """Normalise extracted text for indexing."""
    text = text.replace("\u00ad", "")                       # soft hyphens
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)             # re-join hyphenated line breaks
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def meaningful_chars(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]", text))


def extract_pdf(pdf_bytes: bytes):
    """Return (pages, stats). pages = [{'n': 1, 'text': ..., 'ocr': bool}]."""
    pages, ocr_count = [], 0
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            used_ocr = False
            if meaningful_chars(text) < OCR_THRESHOLD_CHARS:
                try:
                    tp = page.get_textpage_ocr(language=OCR_LANGUAGE, dpi=OCR_DPI, full=True)
                    ocr_text = page.get_text("text", textpage=tp)
                    if meaningful_chars(ocr_text) > meaningful_chars(text):
                        text, used_ocr = ocr_text, True
                        ocr_count += 1
                except Exception as exc:  # Tesseract missing or failed on this page
                    print(f"  OCR failed on page {page.number + 1}: {exc}", file=sys.stderr)
            pages.append({"n": page.number + 1, "text": clean_text(text), "ocr": used_ocr})
    return pages, {"pages": len(pages), "ocr_pages": ocr_count}


def write_issue(meta: dict, pages: list):
    record = {
        **meta,
        "pages": pages,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extractor": f"pymupdf {pymupdf.VersionBind}",
    }
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    path = ISSUES_DIR / f"{meta['id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="process at most N new issues")
    ap.add_argument("--force", action="append", default=[], metavar="ID", help="re-extract this ID")
    ap.add_argument("--all", action="store_true", help="re-extract every issue")
    ap.add_argument("--pdf", help="extract a local PDF (testing); requires --id")
    ap.add_argument("--id", help="doc ID to use with --pdf")
    args = ap.parse_args()

    if args.pdf:
        if not args.id:
            ap.error("--pdf requires --id")
        with open(args.pdf, "rb") as f:
            pages, stats = extract_pdf(f.read())
        path = write_issue({"id": args.id, "title": args.pdf, "year": None,
                            "month": None, "url": None}, pages)
        print(f"{path}: {stats}")
        return

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    todo = [i for i in catalog
            if args.all or i["id"] in args.force
            or not (ISSUES_DIR / f"{i['id']}.json").exists()]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(catalog)} issues in catalog, {len(todo)} to process")

    # Visit the Newsletters page first, as a browser would, so any session
    # cookies ClubExpress sets are sent with the document requests, and send
    # it as the Referer.
    session = new_session()
    try:
        http_get(LISTING_URL, session)
        session.headers["Referer"] = LISTING_URL
    except Exception as exc:
        print(f"Warning: could not load listing page first: {exc}", file=sys.stderr)

    consecutive_non_pdf = 0
    totals = {"issues": 0, "pages": 0, "ocr_pages": 0, "failed": 0}
    for n, meta in enumerate(todo, 1):
        print(f"[{n}/{len(todo)}] {meta['title']} (id {meta['id']})")
        try:
            resp = http_get(meta["url"], session)
            if not resp.content.startswith(b"%PDF"):
                consecutive_non_pdf += 1
                snippet = " ".join(resp.content[:300].decode("utf-8", "replace").split())
                msg = (f"not a PDF: HTTP {resp.status_code}, "
                       f"Content-Type {resp.headers.get('Content-Type')}, "
                       f"final URL {resp.url}, starts: {snippet!r}")
                if consecutive_non_pdf >= MAX_CONSECUTIVE_NON_PDF:
                    raise BlockedError(f"{MAX_CONSECUTIVE_NON_PDF} non-PDF responses in a row. Last: {msg}")
                raise ValueError(msg)
            consecutive_non_pdf = 0
            pages, stats = extract_pdf(resp.content)
            write_issue(meta, pages)
            totals["issues"] += 1
            totals["pages"] += stats["pages"]
            totals["ocr_pages"] += stats["ocr_pages"]
            print(f"  {stats['pages']} pages, {stats['ocr_pages']} OCR'd")
        except BlockedError as exc:
            print(f"STOPPING: {exc}", file=sys.stderr)
            totals["failed"] += 1
            break
        except Exception as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)
            totals["failed"] += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    text_bytes = sum(len(p["text"].encode("utf-8"))
                     for f in ISSUES_DIR.glob("*.json")
                     for p in json.loads(f.read_text(encoding="utf-8"))["pages"])
    print(f"\nThis run: {totals}")
    print(f"Corpus now: {len(list(ISSUES_DIR.glob('*.json')))} issues, "
          f"{text_bytes / 1e6:.1f} MB of extracted text")
    if totals["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
