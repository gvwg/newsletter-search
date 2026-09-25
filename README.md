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
3. `scripts/check.py` compares each link's title and listed contents with the
   text of the PDF it points to, and reports likely wrong links (duplicate PDF,
   contents that match poorly or match another issue better, a different year,
   or a page-1 header dated to a different month). Findings appear as warnings
   on the Actions run; fix the link in CE and the next run picks it up.
   Misprints confirmed by hand go in `KNOWN_OK` in `check.py`.
4. `scripts/build.mjs` builds the search site into `dist/`: a Pagefind index
   with one record per newsletter page (linking to the PDF at that page, with a
   year filter) plus the search page from `site/`. (Next stage: deploy `dist/`
   to Cloudflare at search.gvwg.ca, iframed into a CE custom page.)

Some PDFs open at the wrong page in Edge and Chrome despite the `#page=N` link
(a browser PDF viewer quirk with certain files, not fixable here); the search
page tells readers to use the page number shown in the result.

## Running

On GitHub: Actions tab -> "Extract newsletters" -> Run workflow. Enter a limit
(e.g. 5) for a trial; leave blank to process everything new.

Locally:

    sudo apt-get install tesseract-ocr        # macOS: brew install tesseract
    pip install -r requirements.txt
    cd scripts
    python harvest.py
    python extract.py --limit 5
    python check.py

If a link on the Newsletters page is corrected, the next run picks it up: issue
files whose title or date changed are relabelled (no re-download), newly linked
documents are extracted, and files for documents no longer linked are removed
(at most 10 per run; more than that stops the run as a likely harvest problem).

Search site (Node 20 or later):

    npm install
    npm run build        # writes dist/
    npm run serve        # preview at http://localhost:8765

Use `npm run serve` rather than `python -m http.server`: on some Windows PCs
Python serves .js files as text/plain, and the browser then refuses to run
Pagefind, so searches never return.

Useful options: `extract.py --force <docid>` re-extracts one issue (e.g. after a
corrected PDF is uploaded to CE); `--all` rebuilds everything.

## If ClubExpress blocks the GitHub runner

CE's load balancer returns HTTP 403 on document downloads unless the User-Agent
looks like a browser. `common.py` therefore sends a Chrome-style User-Agent with
our own identifier appended (a maintainer decision; see CLAUDE.md). This works
from GitHub runners as well as locally. If the scripts stop with an HTTP
403/429 message, CE has tightened its rules: stop and consult the maintainer
rather than working around it further.

## Tests

`tests/listing_sample.html` and `tests/sample.pdf` (one text page, one scanned
page) exercise the parser and the OCR path:

    cd scripts
    python harvest.py --html ../tests/listing_sample.html
    python extract.py --pdf ../tests/sample.pdf --id 999
