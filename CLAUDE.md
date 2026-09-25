# GVWG newsletter search: project context for Claude Code

## Goal
Full-text search across the Greater Vancouver Woodturners Guild newsletter archive
(about 248 issues, October 1999 onward). The PDFs are public, stored in the
ClubExpress (CE) Documents library and linked from the public Newsletters page:
https://gvwg.ca/content.aspx?page_id=22&club_id=182740&module_id=717502

## Architecture (decided)
1. `scripts/harvest.py`: parses the Newsletters page into `data/catalog.json`.
   The CE page is the source of truth. Links without a year in the title
   (e.g. site-menu items like "Gallery Tags") are skipped.
2. `scripts/extract.py`: downloads each new PDF from `https://gvwg.ca/docs.ashx?id=N`,
   extracts per-page text with PyMuPDF, OCRs pages with no text layer (Tesseract
   via PyMuPDF), writes `data/issues/<docid>.json`. Incremental; the committed JSON
   is the cache so OCR runs once per issue.
3. Next stage, not yet built: build a Pagefind index (Node API, custom records, one
   record per PDF page, URL `https://gvwg.ca/docs.ashx?id=N#page=P`, year filter)
   into `dist/`, plus a search page. Deploy to Cloudflare Workers static assets
   (not Cloudflare Pages; Cloudflare recommends Workers for new projects) via
   Cloudflare's wrangler GitHub Action, custom domain `search.gvwg.ca`. The gvwg.ca
   DNS is on Cloudflare; no CAA records. `site/_headers` should set
   `Content-Security-Policy: frame-ancestors https://gvwg.ca https://www.gvwg.ca`.
4. The search page is iframed into a CE custom page. Result links open PDFs in a
   new tab using the absolute `https://gvwg.ca/docs.ashx?id=N` form (CE's form for
   links from other websites).

## Key constraint discovered
CE's AWS load balancer (`Server: awselb/2.0`) returns HTTP 403 (bare "403 Forbidden"
page) for `docs.ashx` requests whose User-Agent does not look like a browser. The
Newsletters page accepts any client. Tested 2026-09-25 from the maintainer's home IP:
- `GVWG-newsletter-search/1.0 (+github URL)` alone: 403, same as on GitHub runners.
- The same identifier appended to a Chrome User-Agent string: 302 to a short-lived
  presigned S3 URL, then 200 PDF.

Decision (maintainer, 2026-09-25): send that hybrid User-Agent (see `common.py`)
for the club's own public documents, keeping our identifier on the end. CE support
was judged unlikely to help.
- GitHub runners also pass with the hybrid User-Agent (run 3, 2026-09-25), so the
  earlier runner 403 was the User-Agent rule, not an IP rule. Extraction runs in
  GitHub Actions (`extract.yml`, manual dispatch), which commits `data/` itself.
  The local environment below is kept as a fallback.
- Do not escalate further (proxies, browser automation, other header spoofing).
  If the hybrid User-Agent starts getting 403, stop and ask the maintainer.
- Keep downloads throttled (REQUEST_DELAY_SECONDS = 2.0).
- Never store or link the S3 URLs; they expire within hours. Always use `docs.ashx`.

## Local environment (Windows 11, fallback)
- Git for Windows, Python 3.12, Tesseract (UB Mannheim build), VS Code.
- `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata` (PyMuPDF needs the
  language data; OCR silently yields 0 OCR pages if this is wrong).
- Virtual environment at `.venv`. Run scripts with `.venv\Scripts\python` explicitly
  rather than activating, to avoid PowerShell execution-policy changes.
- Self-test (no network), from `scripts/`:
  `..\.venv\Scripts\python extract.py --pdf ..\tests\sample.pdf --id 999`
  expects `{'pages': 2, 'ocr_pages': 1}`; then delete `data\issues\999.json`.

## Status
- Repo created under the GVWG GitHub organization; harvest works (248 issues).
- Full extraction done (runs 4-5, 2026-09-25): all 248 issues, about 4,300 pages,
  7.4 MB of text. Even the 1999-2012 issues have text layers; only 50 pages in
  34 issues needed OCR (pasted-in images: letters, ads; quality varies).
- `extract.yml` runs an OCR self-test (`tests/sample.pdf`) before extracting;
  it passes on ubuntu-24.04 with apt Tesseract and no `TESSDATA_PREFIX`.
- `extract.py` syncs existing issue files with the catalog each run (relabels
  moved IDs, prunes unlinked IDs, max 10). Needed after Don corrected three
  2014 links that were off by one doc ID.
- `check.py` (runs after extraction, warnings only) flags likely wrong links:
  duplicate text, IDF-weighted match of the CE page's contents list, year on
  pages 1-2, month in the page-1 header. Tested 2026-09-25: no false positives
  on the archive beyond 3 hand-checked header misprints in `KNOWN_OK`; catches
  100/100 random wrong links and 217/237 simulated off-by-one links (misses are
  issues with no dated header and generic contents). Open finding: May 2022
  (1517877) links to a copy of the April 2021 PDF; Don to fix in CE.
- Search site built and tested locally (2026-09-25): `npm run build` indexes
  4,476 pages into `dist/` (about 4,600 files, 19 MB, none over 1 MB);
  `npm run serve` previews it at http://localhost:8765. `site/index.html` is a
  custom page on the Pagefind JS API (not the default UI), because the default
  UI ANDs selected filter values and each page has one year; the page sends a
  From/To year range as `{ year: { any: [...] } }` (Don's choice). Pagefind
  excerpts are not HTML-escaped, so the page rebuilds them keeping only text
  and `<mark>`.
- Letter-spaced headers ("T H E C I R C U L A R") left as is: collapsing them
  would make every recent page match "circular".
- Known viewer quirk: Edge and Chrome ignore `#page=N` for some PDFs (e.g.
  February 2023, 1517884: always lands partway down page 2). Tested with local
  variants: caused by the combination of pages 1 and 2 of that file; not page
  labels, tags, linearization, links, CE/S3 or new-tab. Not fixable on our side
  (the PDFs are CE's); the search page tells readers to use the page number shown.
- Local Node is 24 LTS (installed over an old Node 10 in
  `C:\Program Files (x86)\nodejs`). Python's http.server on this PC serves .js
  as text/plain (registry), which breaks Pagefind; use `npm run serve`.

## Next steps
1. Cloudflare (Don): confirm the account holding gvwg.ca DNS is GVWG-owned;
   create a Workers API token; add token and account ID as GitHub secrets.
2. Deploy workflow: build + wrangler deploy to Workers static assets, custom
   domain `search.gvwg.ca`. Commits pushed with the default `GITHUB_TOKEN` do
   not trigger `push` workflows (documented GitHub behaviour), so run the build
   from the extraction workflow (`workflow_run` or a job in it). Add a daily
   schedule to `extract.yml`. After deploy, verify content types and
   `_headers` on the live site.
3. CE custom page with iframe; link from the Newsletters page.

## Working with the maintainer (Don)
- Retired IT Director, 40+ years in development, architecture and infrastructure.
  Engage as a peer. Concise by default.
- Challenge assumptions that drift from best practice; do not simply agree.
- Always distinguish documented facts from inference, and never guess.
- Test before claiming something works; say plainly what was not tested.
- Communications written for others: plain professional prose, no em dashes.
- Volunteer maintainability matters: prefer simple, documented, low-maintenance
  choices, owned by GVWG accounts rather than personal ones.
