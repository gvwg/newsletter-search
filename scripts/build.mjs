// Build the newsletters site into dist/: copy site/, write the issue list into
// index.html, and write a Pagefind index with one record per newsletter page.
//
// Each record links to https://gvwg.ca/docs.ashx?id=N#page=P, so a result
// opens the PDF at the matching page. Only issues listed in data/catalog.json
// are indexed; titles, years and months come from the catalog.
//
// Usage: npm run build

import { existsSync } from "node:fs";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as pagefind from "pagefind";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(ROOT, "dist");
const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];

const catalog = JSON.parse(await readFile(path.join(ROOT, "data", "catalog.json"), "utf8"));

await rm(DIST, { recursive: true, force: true });
await mkdir(DIST, { recursive: true });
await cp(path.join(ROOT, "site"), DIST, { recursive: true });
// Page-1 thumbnails made by extract.py, shown in the issue list.
if (existsSync(path.join(ROOT, "data", "thumbs"))) {
  await cp(path.join(ROOT, "data", "thumbs"), path.join(DIST, "thumbs"), { recursive: true });
}
// The search page is served at /search (Workers drops the .html).
await writeFile(path.join(DIST, "index.html"),
  issueListPage(await readFile(path.join(ROOT, "site", "index.html"), "utf8"), catalog));

const { index, errors } = await pagefind.createIndex({ forceLanguage: "en" });
if (!index) throw new Error(`Pagefind createIndex failed: ${errors.join("; ")}`);

let issues = 0, records = 0;
const missing = [];
for (const issue of catalog) {
  let data;
  try {
    data = JSON.parse(await readFile(path.join(ROOT, "data", "issues", `${issue.id}.json`), "utf8"));
  } catch {
    missing.push(issue.id);   // not extracted yet; the next extraction run adds it
    continue;
  }
  issues++;
  // Sort key: YYYY-MM, so newer issues can be listed first.
  const date = `${issue.year}-${String(issue.month ?? 1).padStart(2, "0")}`;
  // Short heading for result cards ("October 2013"); CE titles vary in wording.
  const label = issue.month ? `${MONTHS[issue.month - 1]} ${issue.year}` : issue.title;
  // The issue's cover, shown on every result card from that issue.
  const cover = existsSync(path.join(ROOT, "data", "thumbs", `${issue.id}.jpg`))
    ? { image: `/thumbs/${issue.id}.jpg` } : {};
  for (const page of data.pages) {
    if (!page.text.trim()) continue;
    const res = await index.addCustomRecord({
      url: `${issue.url}#page=${page.n}`,
      content: page.text,
      language: "en",
      meta: { title: `${issue.title}, page ${page.n}`, issue: label,
              page: String(page.n), pages: String(data.pages.length), ...cover },
      filters: { year: [String(issue.year)] },
      sort: { date },
    });
    if (res.errors.length) throw new Error(`${issue.id} p${page.n}: ${res.errors.join("; ")}`);
    records++;
  }
}

const { errors: writeErrors } = await index.writeFiles({ outputPath: path.join(DIST, "pagefind") });
if (writeErrors.length) throw new Error(`Pagefind writeFiles failed: ${writeErrors.join("; ")}`);
await pagefind.close();

console.log(`Indexed ${records} pages from ${issues} issues into ${path.relative(ROOT, DIST)}/`);
if (missing.length) console.log(`Not yet extracted, skipped: ${missing.join(", ")}`);

// ---- the issue list (site root) ----

function escapeHtml(text) {
  return text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}

// Fill the build: markers in site/index.html: issues grouped by year, newest
// first; the two most recent years open, older ones folded.
function issueListPage(template, catalog) {
  const byYear = new Map();
  for (const issue of catalog) {
    if (!byYear.has(issue.year)) byYear.set(issue.year, []);
    byYear.get(issue.year).push(issue);
  }
  const years = [...byYear.keys()].sort((a, b) => b - a);
  const sections = years.map((year, i) => {
    // Newest month first; an issue with no month (e.g. a special edition) last.
    const issues = byYear.get(year).sort((a, b) => (b.month ?? 0) - (a.month ?? 0));
    const items = issues.map((issue) => {
      const url = escapeHtml(issue.url);
      const link = `href="${url}" target="_blank" rel="noopener"`;
      // The thumbnail repeats the title link, so it is hidden from screen
      // readers and skipped by the Tab key.
      const thumb = existsSync(path.join(ROOT, "data", "thumbs", `${issue.id}.jpg`))
        ? `<a class="thumb" ${link} tabindex="-1" aria-hidden="true"><img src="/thumbs/${issue.id}.jpg" alt="" width="120" height="155" loading="lazy"></a>`
        : `<span class="thumb"></span>`;
      const n = issue.contents?.length ?? 0;
      const contents = n
        ? `<ul class="contents${n > 6 ? " long" : ""}">${issue.contents.map((c) => `<li>${escapeHtml(c)}</li>`).join("")}</ul>`
        : "";
      // Title on its own line; below it the cover, with the contents beside it.
      return `<li class="issue"><a class="name" ${link}>${escapeHtml(issue.title)}</a><div class="body">${thumb}${contents}</div></li>`;
    });
    const n = issues.length;
    return `<details class="year" id="y${year}" data-year="${year}" data-count="${n}"${i < 2 ? " open" : ""}>
<summary><h3>${year}</h3> <span class="count">${n} issue${n === 1 ? "" : "s"}</span></summary>
<ul class="issues">
${items.join("\n")}
</ul>
</details>`;
  });
  const ascending = [...years].reverse();
  const options = (selected) => ascending
    .map((y) => `<option${y === selected ? " selected" : ""}>${y}</option>`).join("");
  const fills = {
    "from-options": options(ascending[0]),
    "to-options": options(years[0]),
    "count": String(catalog.length),
    "year-links": years.map((y) => `<li><a href="#y${y}">${y}</a></li>`).join(""),
    "issue-list": sections.join("\n"),
  };
  for (const [name, html] of Object.entries(fills)) {
    const marker = `<!-- build:${name} -->`;
    if (!template.includes(marker)) throw new Error(`site/index.html is missing ${marker}`);
    template = template.replace(marker, () => html);
  }
  return template;
}
