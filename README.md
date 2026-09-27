# GVWG newsletters

The Greater Vancouver Woodturners Guild newsletter archive, from October 1999
to the latest issue, at **https://newsletters.gvwg.ca**: every issue with its
cover and contents, and a search of the full text of every page.

The newsletters themselves stay where they are, as PDFs in the Newsletters
folder of the club's ClubExpress (CE)
[Document Library](https://gvwg.ca/content.aspx?page_id=86&club_id=182740).
This project reads that folder, extracts the text of each PDF, and publishes
the site, which links back to the PDFs. It updates itself when a new issue is
uploaded.

This README has three parts: **for readers** (using the site), **for the club
maintainer** (the volunteer keeping it running) and **for developers**.

---

## For readers

### Browsing the issues

[newsletters.gvwg.ca](https://newsletters.gvwg.ca) lists every issue, newest
first, grouped by year.

- Each issue shows its cover and its list of articles. Click the title or the
  cover to open the newsletter (PDF) in a new tab.
- The two most recent years are open. Click any year to open or close it, or
  use **Expand all** and **Collapse all**. The row of year buttons jumps
  straight to a year.
- **Years** (from and to), in the blue search panel, narrows the list to those
  years. The same range applies if you then search from that page.

### Searching

Type a name, technique, wood or any other words in the search box and press
Enter or **Search**, for example *hollowing*, *Stuart Batty* or *pepper mill*.
The search covers the full text of every page of every issue, including
scanned pages, where the text was recognised automatically and may be
imperfect.

- Each result is one page of a newsletter: the issue, the page number, the
  passage with your words highlighted, and the issue's cover. Results are
  shown ten at a time; **More results** shows the next ten.
- Clicking a result opens the newsletter in a new tab at that page. A few
  issues open on the wrong page in some browsers; if that happens, go to the
  page number shown in the result.
- **Years** narrows the search to a range of years.
- The address in the browser keeps your search and year range, so you can
  bookmark a search or send the link to someone.

You can also search from the search box on the
[Newsletters page](https://gvwg.ca/content.aspx?page_id=22&club_id=182740&module_id=717502)
of gvwg.ca.

### Getting around

- The **Back** button at the top returns you to where you came from: the
  gvwg.ca page you left, or the issue list after a search (with your place in
  the list kept). If you opened the site directly, it takes you to the GVWG
  home page, or from a search to the issue list.
- Once you scroll down, a **Top** button in the corner takes you back to the
  top of the page.
- The site works on phones and tablets as well as computers.

---

## For the club maintainer

### How a new issue gets published

1. The editor uploads the PDF to the **Newsletters** folder of the CE Document
   Library, visible to the public, with a title that includes the month and
   year (for example "October 2026").
2. Within about three hours it appears on
   [newsletters.gvwg.ca](https://newsletters.gvwg.ca) with its cover and
   contents list (read from the PDF), and its text is searchable. Nothing needs
   to be done here.
3. The News post on the gvwg.ca home page is still made by hand in CE.
   `scripts/publish_prep.py` can prepare its body and cover image (see the
   developer section). The earlier tool that did this through Claude in Chrome
   is retired; see [`archive/`](archive/README.md).

To see a new issue sooner, run the update by hand (see "Running an update by
hand" below). To take an issue off the site, delete it from the Newsletters
folder or hide it; the next run removes it.

The folder is the only list: every public document in it is published, except
those excluded in `data/overrides.json` (see "Hand corrections" below).

### Seeing problems

| Where to look | What it tells you |
|---|---|
| [Issues labelled `link-check`](https://github.com/gvwg/newsletter-search/issues?q=label%3Alink-check) | A newsletter's title probably does not match its PDF (a duplicate, the wrong month, or the wrong year). One issue per document. People watching the repository get an email when one opens. |
| [Issues labelled `contents`](https://github.com/gvwg/newsletter-search/issues?q=label%3Acontents) | No contents list could be read from a new issue (its layout may have changed). It is still listed and searchable; add the list by hand (see "Hand corrections"). |
| [Issues labelled `untitled`](https://github.com/gvwg/newsletter-search/issues?q=label%3Auntitled) | A document in the Newsletters folder was left out because its title has no year. |
| [Actions tab](https://github.com/gvwg/newsletter-search/actions) | Every run of "Extract newsletters" and "Build and deploy search site". A red X is a failed run. GitHub emails failures of the scheduled run to the account that last edited its schedule. |
| https://newsletters.gvwg.ca | Check that the newest issue is listed and that a word from it is found. If not, a few hours after it was uploaded, check the Actions tab. |

Each issue says what to do. In short: fix a wrong title in CE (or set one in
`data/overrides.json`); add a missing contents list to `data/overrides.json`;
or, if nothing is wrong (for example a misprinted date in the newsletter
header), close the issue by hand with a comment. The next run closes an issue
once its cause is fixed. A closed issue is never reopened or repeated for that
document.

### Correcting an issue that is already published

The site notices new documents in the Newsletters folder, not changes to a
document already there. To publish a corrected PDF, either:

- **Upload it as a new document** in the Newsletters folder and delete (or
  hide) the old one. The next run adds the new one and removes the old one.
  Nothing else is needed.
- **Or replace the file on the existing document** in CE, then refresh it
  here: Actions tab, **Extract newsletters**, **Run workflow**, enter the doc
  ID (the number in `docs.ashx?id=N`) in **Re-extract doc ID**, and run. This
  re-reads its text, cover and contents list. Without this step the site keeps
  showing the old version.

### Hand corrections: `data/overrides.json`

Edit it on GitHub (pencil icon) and commit; the next run applies it. All
entries are keyed by the CE doc ID, the number in `docs.ashx?id=N`.

- `exclude`: documents in the Newsletters folder not to publish, each with a
  reason. Currently an earlier version of March/April 2020.
- `titles`: a title to use instead of the CE title.
- `contents`: a contents list to use instead of the one read from the PDF,
  one string per article, for example
  `"1830001": ["Presidential Ramblings", "Tech Talk"]`.

### Running an update by hand

1. Go to the [Actions tab](https://github.com/gvwg/newsletter-search/actions)
   and click **Extract newsletters** in the left-hand list.
2. Click **Run workflow**, leave the boxes blank, and click the green
   **Run workflow** button.
3. If it found anything new, its "deploy" job republishes the site. Check that
   the run has a green tick, then look for the new issue on the site.

"Build and deploy search site" also has a **Run workflow** button, which
republishes the site without checking CE.

### Restarting the scheduled run

The repository is public, so GitHub Actions costs nothing. The catch is that
**GitHub pauses scheduled workflows in public repositories after 60 days with
no repository activity**, which can happen over a summer with no new issues.
The site keeps working while paused; only new issues stop being added.

To restart it, open **Extract newsletters** in the Actions tab; if a banner
says the workflow is disabled, click **Enable workflow**. Then run an update
by hand (above) to catch up.

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
administrators with their own logins, so the site does not depend on one
person.

### Links from gvwg.ca

- **Search banner.** The search box on the gvwg.ca Newsletters page is an HTML
  widget in CE. Its source is [`ce/search-banner.html`](ce/search-banner.html);
  paste it into the widget's HTML view if the banner is ever lost or needs to
  go on another page. It sends readers to
  `https://newsletters.gvwg.ca/search?q=<their words>`.
- **Menu links.** Link to https://newsletters.gvwg.ca in the same window, not
  a new tab, so the site's Back button can return readers to the gvwg.ca page
  they came from.

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
| `.github/workflows/extract.yml` ("Extract newsletters") | GitHub Actions, ubuntu-24.04, Python 3.12, apt Tesseract | Cron `17 */3 * * *`, or by hand (optional `limit`, and `force` to re-extract one doc ID) | OCR self-test on `tests/sample.pdf`; `harvest.py`; `extract.py`; commits `data/`; `check.py --github`; calls `deploy.yml` if it committed anything |
| `.github/workflows/deploy.yml` ("Build and deploy search site") | GitHub Actions, Node 24 | Called by an extraction run that committed data (`workflow_call`), pushes to `main` touching site or build files, or by hand | `npm ci`, `npm run build`, `wrangler deploy` (skipped with a warning if the Cloudflare secrets are absent) |
| `wrangler.jsonc` | Cloudflare Workers | Deploy | Assets-only Worker serving `dist/`, custom domain `newsletters.gvwg.ca` |
| `site/_headers` | Cloudflare | Every request | `frame-ancestors https://gvwg.ca https://www.gvwg.ca` (so the page may be iframed on gvwg.ca only) and `nosniff` |
| `site/index.html` | Reader's browser | Page load | Template for the issue list at `/`; `build.mjs` writes the list into it. Search box (submits to `/search`) and a From/To year range that also filters the list; reads `?from=&to=` |
| `site/search.html` | Reader's browser | Page load | Search page, served at `/search`, on the Pagefind JS API; reads `?q=&from=&to=` |
| `site/site.css` | Reader's browser | Page load | Look shared by both pages (header, search panel, footer) |
| `site/site.js` | Reader's browser | Page load | Shared by both pages: the Back link (browser history when the reader came from gvwg.ca or this site) and the back-to-top button |
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

### Site notes

- The issue list at `/` is static HTML written at build time; its script
  (year range, Expand/Collapse all, year links) only enhances it, so the list
  works without JavaScript.
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
