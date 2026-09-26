# GVWG newsletter search

Full-text search of the Greater Vancouver Woodturners Guild newsletter archive
(October 1999 onward) at **https://newsletters.gvwg.ca/search**. The newsletters themselves
stay where they are: PDFs in the ClubExpress (CE) Documents library, linked from
the [Newsletters page](https://gvwg.ca/content.aspx?page_id=22&club_id=182740&module_id=717502)
on gvwg.ca. This project reads that page, extracts the text of each PDF, and
publishes a search site that links back to the PDFs.

The first part of this README is for the club volunteer looking after the
search. The second part is for a developer changing it.

---

## For the club maintainer

### What happens on its own

- **Every day at 11:17 UTC** (3:17 or 4:17 am Vancouver time) GitHub checks the
  Newsletters page. Any newly linked issue is downloaded, its text extracted,
  and the search site republished. A newsletter linked on CE today is
  searchable tomorrow.
- **Nothing needs to be done here when a newsletter is published.** Add it to
  the Newsletters page in CE as usual. The CE page is the only list; if an
  issue is not linked there, it is not in the search.
- **Wrong links are reported.** Each run compares every link on the Newsletters
  page with the PDF it opens and opens a GitHub issue for any that look wrong
  (see "Seeing problems" below).

### Seeing problems

| Where to look | What it tells you |
|---|---|
| [Issues labelled `link-check`](https://github.com/gvwg/newsletter-search/issues?q=label%3Alink-check) | A link on the Newsletters page probably opens the wrong PDF (a duplicate, the wrong month, or the wrong year). One issue per link. People watching the repository get an email when one opens. |
| [Actions tab](https://github.com/gvwg/newsletter-search/actions) | Every run of "Extract newsletters" and "Build and deploy search site". A red X is a failed run. GitHub emails failures of the daily run to the account that last edited its schedule. |
| https://newsletters.gvwg.ca/search | Search for a word from the newest issue. If it is not found a day or two after the issue went up, check the Actions tab. |

**When a `link-check` issue appears:** open the link on the Newsletters page
and look at the PDF. If the link is wrong, fix it in CE; the next daily run
notices and closes the issue by itself. If the link is right (for example a
misprinted date in the newsletter header), close the issue by hand with a
comment. A closed issue is never reopened or repeated for that document.

### Restarting the daily run

The repository is public, so GitHub Actions costs nothing. The catch is that
**GitHub pauses scheduled workflows in public repositories after 60 days with
no repository activity**, which can happen over a summer with no new issues.
The search site keeps working while paused; only new issues stop being added.

To restart it:

1. Go to the [Actions tab](https://github.com/gvwg/newsletter-search/actions)
   and click **Extract newsletters** in the left-hand list.
2. If a banner says the workflow is disabled, click **Enable workflow**.
3. Click **Run workflow**, leave the box blank, and click the green
   **Run workflow** button. This catches up now instead of waiting a day.
4. When it finishes, "Build and deploy search site" runs by itself. Check that
   it has a green tick, then search for a word from the newest issue.

The same **Run workflow** button is the way to force an update at any time, for
example straight after linking a new issue. "Build and deploy search site" also
has a **Run workflow** button, which republishes the site without checking CE.

### When a run fails

- **HTTP 403 or 429 when downloading from gvwg.ca.** ClubExpress has started
  refusing the downloads. Do not try to work around it; see "ClubExpress
  downloads" in the developer section and decide with the maintainer.
- **"CLOUDFLARE_API_TOKEN is not set" warning on the deploy.** The site was
  built but not published, because the repository secrets `CLOUDFLARE_API_TOKEN`
  and `CLOUDFLARE_ACCOUNT_ID` are missing (Settings, Secrets and variables,
  Actions). Create a new token in Cloudflare (see below) and add it.
- **Anything else.** Click the failed run, then the red step, to see the
  message. Re-running it (**Re-run jobs**) is safe: finished issues are kept
  and never processed twice.

### Accounts and what they cost

| Service | Used for | Cost |
|---|---|---|
| GitHub organization `gvwg` | This repository and the daily and deploy runs | Free (public repository, standard runners) |
| Cloudflare account (holds the gvwg.ca DNS) | Hosting newsletters.gvwg.ca as a Worker with static assets | Free: static-asset requests are free and unlimited, no storage charge |
| ClubExpress | The newsletters and the Newsletters page | The club's existing subscription |

The deploy uses a Cloudflare account API token named
`github-deploy-newsletter-search` (Cloudflare dashboard, Manage account,
Account API tokens). It has no expiry. If it is ever revoked, create a new one
from the "Edit Cloudflare Workers" template limited to the gvwg.ca zone, and
paste it into the `CLOUDFLARE_API_TOKEN` repository secret.

Each of these accounts should have at least two club officers as
administrators with their own logins, so the search does not depend on one
person.

### The search box on gvwg.ca

The search banner on the Newsletters page is an HTML widget in CE. Its source is
[`ce/search-banner.html`](ce/search-banner.html); paste it into the widget's
HTML view if the banner is ever lost or needs to go on another page. It sends
readers to `https://newsletters.gvwg.ca/search?q=<their words>`.

---

## For developers

### Architecture

```
 ClubExpress (gvwg.ca)                 GitHub (gvwg/newsletter-search)                 Cloudflare
 ---------------------                 -------------------------------                 ----------
 Newsletters page  --- harvest.py -->  data/catalog.json
 docs.ashx?id=N    --- extract.py -->  data/issues/<id>.json  (committed text cache)
                                       check.py / alerts.py -> GitHub issues
                                       build.mjs -> dist/ (Pagefind index + site/)
                                       wrangler deploy  ----------------------------->  Worker "gvwg-newsletter-search"
                                                                                        static assets at newsletters.gvwg.ca
 Reader's browser: loads newsletters.gvwg.ca/search, runs the search locally (Pagefind JS + WASM),
 and opens results at https://gvwg.ca/docs.ashx?id=N#page=P in a new tab.
```

There is no server-side code and no database. The search index is a set of
static files; the browser downloads only the index fragments a query needs.

### What runs where

| Component | Runs on | Trigger | Does |
|---|---|---|---|
| `.github/workflows/extract.yml` ("Extract newsletters") | GitHub Actions, ubuntu-24.04, Python 3.12, apt Tesseract | Daily cron `17 11 * * *`, or by hand (optional `limit`) | OCR self-test on `tests/sample.pdf`; `harvest.py`; `extract.py`; commits `data/`; `check.py --github` |
| `.github/workflows/deploy.yml` ("Build and deploy search site") | GitHub Actions, Node 24 | After every extraction run (`workflow_run`, unless cancelled), pushes to `main` touching site or build files, or by hand | `npm ci`, `npm run build`, `wrangler deploy` (skipped with a warning if the Cloudflare secrets are absent) |
| `wrangler.jsonc` | Cloudflare Workers | Deploy | Assets-only Worker serving `dist/`, custom domain `newsletters.gvwg.ca` (and `search.gvwg.ca` until it is retired) |
| `site/_headers` | Cloudflare | Every request | `frame-ancestors https://gvwg.ca https://www.gvwg.ca` (so the page may be iframed on gvwg.ca only) and `nosniff` |
| `site/search.html` | Reader's browser | Page load | Search page, served at `/search` (and, until the issue list is built, at `/`) on the Pagefind JS API; reads `?q=&from=&to=` |
| `ce/search-banner.html` | gvwg.ca (CE HTML widget) | Pasted by hand | Search box that opens newsletters.gvwg.ca/search with the reader's words |

`deploy.yml` uses `workflow_run` because commits pushed by the extraction
workflow with `GITHUB_TOKEN` do not trigger `push` workflows.

### Pipeline in detail

1. **`scripts/harvest.py`** parses the Newsletters page into
   `data/catalog.json` (doc ID, title, year, month, listed contents). The CE
   page is the source of truth. Links without a year in the title (site-menu
   items such as "Gallery Tags") are skipped.
2. **`scripts/extract.py`** downloads each issue not yet extracted from
   `https://gvwg.ca/docs.ashx?id=N`, extracts text per page with PyMuPDF, OCRs
   pages with no text layer (Tesseract via PyMuPDF), and writes
   `data/issues/<id>.json`. These files are committed, so OCR runs once per
   issue. Each run also syncs existing files with the catalog: files whose
   title or date changed are relabelled without re-downloading, and files for
   documents no longer linked are removed (at most 10 per run; more stops the
   run as a likely harvest problem). Downloads are throttled to one every two
   seconds.
3. **`scripts/check.py`** flags likely wrong links: duplicate text, contents
   list matching poorly (IDF-weighted) or matching another issue better, a
   different year on pages 1-2, or a different month in the page-1 header.
   Warnings only; it never fails the run. Hand-confirmed misprints go in
   `KNOWN_OK`. With `--github` it calls **`scripts/alerts.py`**, which opens one
   issue per flagged doc ID (label `link-check`, hidden marker
   `<!-- link-check-id: N -->`), never repeats an ID that has any issue open or
   closed, and closes open issues whose ID is no longer flagged (skipped if
   under 90% of the catalog was checked). `--dry-run` previews.
4. **`scripts/build.mjs`** builds `dist/`: a Pagefind index with one custom
   record per PDF page (URL `docs.ashx?id=N#page=P`, a `year` filter, meta for
   issue label, page and page count), plus the files in `site/`.

### Search page notes

- `site/search.html` uses the Pagefind JS API rather than the default UI,
  because the default UI ANDs selected filter values and each page has one
  year. The From/To range is sent as `{ year: { any: [...] } }`.
- Pagefind excerpts are not HTML-escaped, so the page rebuilds each excerpt
  keeping only text and `<mark>`.
- Some PDFs open at the wrong page in Edge and Chrome despite `#page=N` (a
  viewer quirk with certain files, not fixable here); the page tells readers to
  use the page number shown.
- Letter-spaced headers ("T H E C I R C U L A R") are left as extracted;
  collapsing them would make every recent page match "circular".

### ClubExpress downloads

CE's load balancer returns HTTP 403 for `docs.ashx` requests whose User-Agent
does not look like a browser. `scripts/common.py` sends a Chrome-style
User-Agent with this project's identifier appended, a maintainer decision for
the club's own public documents. It works from GitHub runners and locally. If
downloads start failing with 403 or 429, stop and consult the maintainer; do
not escalate (proxies, browser automation, other header changes). Never store
or link the presigned S3 URLs that `docs.ashx` redirects to; they expire within
hours.

The Newsletters page is a single ASP.NET `<form>`, which is why the banner in
`ce/` uses inline handlers rather than its own form.

### Running locally

Python part (Tesseract must be installed; on Windows set
`TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`, or OCR silently
finds nothing):

    pip install -r requirements.txt
    cd scripts
    python harvest.py
    python extract.py --limit 5
    python check.py

`extract.py --force <id>` re-extracts one issue (for example after a corrected
PDF is uploaded to CE); `--all` re-extracts everything. `check.py --github
--dry-run` shows what issues would be opened or closed.

Search site (Node 20 or later):

    npm install
    npm run build        # writes dist/
    npm run serve        # preview at http://localhost:8765

Use `npm run serve` rather than `python -m http.server`: on some Windows PCs
Python serves .js as text/plain, and the browser then refuses to run Pagefind.

### Tests

`tests/listing_sample.html` and `tests/sample.pdf` (one text page, one scanned
page) exercise the parser and the OCR path without network access:

    cd scripts
    python harvest.py --html ../tests/listing_sample.html
    python extract.py --pdf ../tests/sample.pdf --id 999   # expect {'pages': 2, 'ocr_pages': 1}

Afterwards delete `data/issues/999.json` and restore the real catalog with
`git checkout data/catalog.json`: `harvest.py --html` overwrites it with the
sample's few issues, and an extraction run on that catalog would stop rather
than remove the other issue files (it refuses to remove more than 10).

### Repository layout

    .github/workflows/   extract.yml, deploy.yml
    ce/                  HTML pasted into ClubExpress (search banner)
    data/                catalog.json and issues/<id>.json (committed; the text cache)
    scripts/             harvest, extract, check, alerts, common (Python); build, serve (Node)
    site/                search page, _headers, images copied from gvwg.ca
    tests/               offline samples
    wrangler.jsonc       Cloudflare Worker config
    CLAUDE.md            project history and decisions
