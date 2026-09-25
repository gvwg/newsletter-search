// Build the search site into dist/: copy site/ and write a Pagefind index
// with one record per newsletter page.
//
// Each record links to https://gvwg.ca/docs.ashx?id=N#page=P, so a result
// opens the PDF at the matching page. Only issues listed in data/catalog.json
// are indexed; titles, years and months come from the catalog.
//
// Usage: npm run build

import { cp, mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as pagefind from "pagefind";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(ROOT, "dist");

const catalog = JSON.parse(await readFile(path.join(ROOT, "data", "catalog.json"), "utf8"));

await rm(DIST, { recursive: true, force: true });
await mkdir(DIST, { recursive: true });
await cp(path.join(ROOT, "site"), DIST, { recursive: true });

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
  for (const page of data.pages) {
    if (!page.text.trim()) continue;
    const res = await index.addCustomRecord({
      url: `${issue.url}#page=${page.n}`,
      content: page.text,
      language: "en",
      meta: { title: `${issue.title}, page ${page.n}` },
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
