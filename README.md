# GVWG newsletter search

The Greater Vancouver Woodturners Guild newsletter archive (October 1999
onward) at **https://newsletters.gvwg.ca**: every issue listed by year with
its cover and contents, and full-text search at
**https://newsletters.gvwg.ca/search**. The newsletters themselves
stay where they are: PDFs in the Newsletters folder of the ClubExpress (CE)
[Document Library](https://gvwg.ca/content.aspx?page_id=86&club_id=182740)
on gvwg.ca. This project reads that folder, extracts the text of each PDF, and
publishes a search site that links back to the PDFs.

The first part of this README is for the club volunteer looking after the
search. The second part is for a developer changing it.

---

## For the club maintainer

### What happens on its own

- **Every 3 hours** GitHub checks the Newsletters folder in the CE Document
  Library. Any new document is downloaded, its text and table of contents
  extracted, and the site republished. A newsletter uploaded to the folder is
  searchable within a few hours. Runs that find nothing new change nothing.
- **Nothing needs to be done here when a newsletter is published.** Upload the
  PDF to the Newsletters folder in CE, with a title that includes the month
  and year (for example "October 2026"). The folder is the only list: every
  document in it is published, except those excluded in `data/overrides.json`.
  Removing a document from the folder removes it from the site.
- **Problems are reported** as GitHub issues (see "Seeing problems" below):
  a document whose title may not match its PDF, an issue whose contents list
  could not be read, or a document left out because its title has no year.

### Seeing problems

| Where to look | What it tells you |
|---|---|
| [Issues labelled `link-check`](https://github.com/gvwg/newsletter-search/issues?q=label%3Alink-check) | A newsletter's title probably does not match its PDF (a duplicate, the wrong month, or the wrong year). One issue per document. People watching the repository get an email when one opens. |
| [Issues labelled `contents`](https://github.com/gvwg/newsletter-search/issues?q=label%3Acontents) | No contents list could be read from a new issue (its layout may have changed). It is still searchable; add the list by hand (see below). |
| [Issues labelled `untitled`](https://github.com/gvwg/newsletter-search/issues?q=label%3Auntitled) | A document in the Newsletters folder was left out because its title has no year. |
| [Actions tab](https://github.com/gvwg/newsletter-search/actions) | Every run of "Extract newsletters" and "Build and deploy search site". A red X is a failed run. GitHub emails failures of the scheduled run to the account that last edited its schedule. |
| https://newsletters.gvwg.ca/search | Search for a word from the newest issue. If it is not found a few hours after the issue went up, check the Actions tab. |

Each issue says what to do. In short: fix a wrong title in CE (or set one in
`data/overrides.json`); add a missing contents list to `data/overrides.json`;
or, if nothing is wrong (for example a misprinted date in the newsletter
header), close the issue by hand with a comment. The next run closes an issue
once its cause is fixed. A closed issue is never reopened or repeated for that
document.

### Hand corrections: `data/overrides.json`

Edit it on GitHub (pencil icon) and commit; the next run applies it. All
entries are keyed by the CE doc ID, the number in `docs.ashx?id=N`.

- `exclude`: documents in the Newsletters folder not to publish, each with a
  reason. Currently an earlier version of March/April 2020.
- `titles`: a title to use instead of the CE title.
- `contents`: a contents list to use instead of the one read from the PDF,
  one string per article, for example
  `"1830001": ["Presidential Ramblings", "Tech Talk"]`.

### Restarting the scheduled run

The repository is public, so GitHub Actions costs nothing. The catch is that
**GitHub pauses scheduled workflows in public repositories after 60 days with
no repository activity**, which can happen over a summer with no new issues.
The search site keeps working while paused; only new issues stop being added.

To restart it:

1. Go to the [Actions tab](https://github.com/gvwg/newsletter-search/actions)
   and click **Extract newsletters** in the left-hand list.
2. If a banner says the workflow is disabled, click **Enable workflow**.
3. Click **Run workflow**, leave the box blank, and click the green
   **Run workflow** button. This catches up now instead of waiting.
4. If it found anything new, its "deploy" job republishes the site. Check that
   the run has a green tick, then search for a word from the newest issue.

The same **Run workflow** button is the way to force an update at any time, for
example straight after uploading a new issue. "Build and deploy search site" also
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
| GitHub organization `gvwg` | This repository and the scheduled and deploy runs | Free (public repository, standard runners) |
| Cloudflare account (holds the gvwg.ca DNS) | Hosting newsletters.gvwg.ca as a Worker with static assets | Free: static-asset requests are free and unlimited, no storage charge |
| ClubExpress | The newsletters (Document Library) | The club's existing subscription |

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
 Newsletters folder --- harvest.py -> data/catalog.json, data/folder.json
                                       (+ data/overrides.json, kept by hand)
 docs.ashx?id=N    --- extract.py -->  data/issues/<id>.json  (committed text cache)
                                       data/thumbs/<id>.jpg   (page-1 thumbnails)
                                       + contents of new issues (toc.py) -> catalog.json
                                       check.py / alerts.py -> GitHub issues
                                       build.mjs -> dist/ (issue list, Pagefind index, site/)
                                       wrangler deploy  ----------------------------->  Worker "gvwg-newsletter-search"
                                                                                        static assets at newsletters.gvwg.ca
 Reader's browser: newsletters.gvwg.ca/ is a static issue list; /search runs the search locally
 (Pagefind JS + WASM) and opens results at https://gvwg.ca/docs.ashx?id=N#page=P in a new tab.
```

There is no server-side code and no database. The search index is a set of
static files; the browser downloads only the index fragments a query needs.

### What runs where

| Component | Runs on | Trigger | Does |
|---|---|---|---|
| `.github/workflows/extract.yml` ("Extract newsletters") | GitHub Actions, ubuntu-24.04, Python 3.12, apt Tesseract | Cron `17 */3 * * *`, or by hand (optional `limit`) | OCR self-test on `tests/sample.pdf`; `harvest.py`; `extract.py`; commits `data/`; `check.py --github`; calls `deploy.yml` if it committed anything |
| `.github/workflows/deploy.yml` ("Build and deploy search site") | GitHub Actions, Node 24 | Called by an extraction run that committed data (`workflow_call`), pushes to `main` touching site or build files, or by hand | `npm ci`, `npm run build`, `wrangler deploy` (skipped with a warning if the Cloudflare secrets are absent) |
| `wrangler.jsonc` | Cloudflare Workers | Deploy | Assets-only Worker serving `dist/`, custom domain `newsletters.gvwg.ca` |
| `site/_headers` | Cloudflare | Every request | `frame-ancestors https://gvwg.ca https://www.gvwg.ca` (so the page may be iframed on gvwg.ca only) and `nosniff` |
| `site/index.html` | Reader's browser | Page load | Template for the issue list at `/`; `build.mjs` writes the list into it. Search box (submits to `/search`) and a From/To year range that also filters the list; reads `?from=&to=` |
| `site/search.html` | Reader's browser | Page load | Search page, served at `/search`, on the Pagefind JS API; reads `?q=&from=&to=` |
| `site/site.css` | Reader's browser | Page load | Look shared by both pages (header, search panel, footer) |
| `ce/search-banner.html` | gvwg.ca (CE HTML widget) | Pasted by hand | Search box that opens newsletters.gvwg.ca/search with the reader's words |

The extraction workflow calls `deploy.yml` itself because its commits, pushed
with `GITHUB_TOKEN`, do not trigger `push` workflows; calling it only after a
commit avoids eight identical deploys a day.

### Pipeline in detail

1. **`scripts/harvest.py`** reads the Newsletters folder (id `216109`) of the
   public Document Library. Its list comes from
   `/handlers/documenthandler.ashx?cat_id=216109`, which returns 404 unless the
   library page has been loaded first in the same session (cookie). The raw
   listing goes to `data/folder.json`; the merged result to `data/catalog.json`
   (doc ID, title, year, month, contents, `contents_source`), which is the
   committed record. Documents under `exclude` in `data/overrides.json` are
   skipped, as are documents whose title has no year (reported). Title rule:
   the CE title wins if it has a month and year and is not a bare filename;
   otherwise the catalog title is kept, or for a new document one is made from
   the filename. A run that would remove more than 10 issues stops without
   writing. Contents: the 248 issues on the old CE Newsletters page keep the
   lists typed there (`ce`; `--bootstrap` copies them again from the live page,
   and is harmless once that page no longer lists issues); an override list
   always wins (`override`).
2. **`scripts/extract.py`** downloads each issue not yet extracted from
   `https://gvwg.ca/docs.ashx?id=N`, extracts text per page with PyMuPDF, OCRs
   pages with no text layer (Tesseract via PyMuPDF), and writes
   `data/issues/<id>.json`. These files are committed, so OCR runs once per
   issue. Each run also syncs existing files with the catalog: files whose
   title or date changed are relabelled without re-downloading, and files for
   documents no longer in the catalog are removed (at most 10 per run; more
   stops the run as a likely harvest problem). Downloads are throttled to one
   every two seconds. Each issue also gets a 240 px JPEG of page 1 in
   `data/thumbs/` (about 14 KB each); an issue already extracted but missing
   its thumbnail is downloaded again for the thumbnail only. For an issue with
   no contents list, it reads one from the
   PDF with **`scripts/toc.py`** and writes it to the catalog (`pdf`).
   `toc.py` tries a position-based reader for the CONTENTS box of the April
   2026 template, then a layout-independent reader that finds the longest run
   of title and page-number pairs on pages 1-3. A result needs at least 3
   entries with ascending page numbers within the issue, or the list stays
   empty and is reported. `python toc.py --score` scores the text reader
   against the 248 hand-typed CE lists (0.74 of entries found, 2026-09-26);
   a change to either reader should not lower it.
3. **`scripts/check.py`** flags newsletters whose title may not match the PDF:
   duplicate text, contents list matching poorly (IDF-weighted) or matching
   another issue better, a different year on pages 1-2, or a different month
   in the page-1 header. Warnings only; it never fails the run. Hand-confirmed
   misprints go in `KNOWN_OK`. With `--github` it calls
   **`scripts/alerts.py`**, which keeps three kinds of GitHub issue, one per
   doc ID each: `link-check` (the findings above), `contents` (an extracted
   issue with no contents list) and `untitled` (a folder document left out for
   want of a year). Each carries a hidden marker `<!-- kind-id: N -->`; an ID
   with any issue of that kind, open or closed, never gets another, and open
   issues are closed once their ID is no longer flagged (link-check: not if
   under 90% of the catalog was checked). `--dry-run` previews.
4. **`scripts/build.mjs`** builds `dist/`: the files in `site/`; the issue
   list, written into the `<!-- build:... -->` markers of `site/index.html`
   (years newest first, the two most recent open, one card per issue with its
   thumbnail and contents); `data/thumbs/` as `/thumbs/`; and a Pagefind index
   with one custom record per PDF page (URL `docs.ashx?id=N#page=P`, a `year`
   filter, meta for issue label, page and page count).

### Search page notes

- `site/search.html` uses the Pagefind JS API rather than the default UI,
  because the default UI ANDs selected filter values and each page has one
  year. The From/To range is sent as `{ year: { any: [...] } }`.
- Each result card shows the issue's cover (`meta.image` in the Pagefind
  record, `/thumbs/<id>.jpg`), not the matching page.
- The Back link (`site/site.js`) goes back in the browser history when the
  reader came from gvwg.ca or from this site, so they return to the exact
  page (CE pages send `Referrer-Policy: no-referrer` but also
  `<meta name="referrer" content="always">`, which wins: tested
  2026-09-26 from the Contact Us page). Arriving directly, it is a plain link:
  "Back to GVWG home" from the list, the list from search.
- A back-to-top button (`site/site.js`, shared with the issue list) appears
  once the reader has scrolled a screen down.
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

Offline checks, from `scripts/`:

    python harvest.py --html ../tests/folder_sample.html   # folder as of 2026-09-26: expect no changes
    python extract.py --pdf ../tests/sample.pdf --id 999   # expect {'pages': 2, 'ocr_pages': 1}
    python toc.py --score                                  # contents reader vs the CE lists

`tests/folder_sample.html` is the live folder listing saved on 2026-09-26;
`tests/listing_sample.html` is a small copy of the old Newsletters page
(for `harvest.py --bootstrap --page-html`). `tests/sample.pdf` has one text
page and one scanned page. Afterwards delete `data/issues/999.json`, and run
`git checkout data` if a harvest changed anything.

### Repository layout

    .github/workflows/   extract.yml, deploy.yml
    ce/                  HTML pasted into ClubExpress (search banner)
    data/                catalog.json, folder.json, overrides.json (hand-kept),
                         issues/<id>.json (the text cache) and thumbs/<id>.jpg (committed)
    archive/             retired tools (the publish-newsletter skill); see archive/README.md
    scripts/             harvest, extract, toc, check, alerts, publish_prep, common (Python);
                         build, serve (Node)
    site/                issue list template, search page, shared CSS, _headers,
                         images copied from gvwg.ca
    tests/               offline samples
    wrangler.jsonc       Cloudflare Worker config
    CLAUDE.md            project history and decisions
