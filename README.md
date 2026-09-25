# GVWG newsletter search

Full-text search of the Greater Vancouver Woodturners Guild newsletter archive
(October 1999 onward), whose PDFs live in the ClubExpress Documents library.

## How it works

1. `scripts/harvest.py` reads the public Newsletters page on gvwg.ca and writes
   `data/catalog.json` (title, date, doc ID for every linked issue). The CE page
   is the source of truth; nothing here is maintained by hand.
2. `scripts/extract.py` downloads each issue not yet processed, extracts text per
   page with PyMuPDF, OCRs pages that have no text layer (Tesseract), and writes
   `data/issues/<docid>.json`. These files are committed, so each issue is only
   ever processed once and the repo holds a plain-text archive of the newsletters.
3. (Next stage) A Pagefind index is built from `data/issues/` and deployed to
   Cloudflare at search.gvwg.ca, which is iframed into a CE custom page.

## Running

On GitHub: Actions tab -> "Extract newsletters" -> Run workflow. Enter a limit
(e.g. 5) for a trial; leave blank to process everything new.

Locally:

    sudo apt-get install tesseract-ocr        # macOS: brew install tesseract
    pip install -r requirements.txt
    cd scripts
    python harvest.py
    python extract.py --limit 5

Useful options: `extract.py --force <docid>` re-extracts one issue (e.g. after a
corrected PDF is uploaded to CE); `--all` rebuilds everything.

## If ClubExpress blocks the GitHub runner

CE's load balancer returns HTTP 403 on document downloads unless the User-Agent
looks like a browser. `common.py` therefore sends a Chrome-style User-Agent with
our own identifier appended (a maintainer decision; see CLAUDE.md). Extraction
currently runs locally and `data/` is committed. If the scripts stop with an HTTP
403/429 message, CE has tightened its rules: stop and consult the maintainer
rather than working around it further.

## Tests

`tests/listing_sample.html` and `tests/sample.pdf` (one text page, one scanned
page) exercise the parser and the OCR path:

    cd scripts
    python harvest.py --html ../tests/listing_sample.html
    python extract.py --pdf ../tests/sample.pdf --id 999
