// Preview dist/ locally at http://localhost:8765 (npm run serve).
//
// Sets content types explicitly: Python's http.server on Windows takes them
// from the registry, which can map .js to text/plain, and browsers then
// refuse to load Pagefind's module and worker scripts. Cloudflare serves the
// deployed site; this is for local testing only.

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DIST = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "dist");
const PORT = 8765;
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".pdf": "application/pdf",
};

createServer(async (req, res) => {
  let rel = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (rel.endsWith("/")) rel += "index.html";
  const file = path.join(DIST, rel);
  if (!file.startsWith(DIST + path.sep)) { res.writeHead(403).end(); return; }
  try {
    const body = await readFile(file);
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end("Not found");
  }
}).listen(PORT, () => console.log(`Serving ${DIST} at http://localhost:${PORT}`));
