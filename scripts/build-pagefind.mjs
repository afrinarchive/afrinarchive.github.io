import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const root = path.resolve(path.dirname(__filename), "..");
const appData = process.env.APPDATA || "";
const candidates = [
  path.join(root, "node_modules", "pagefind", "lib", "runner", "bin.cjs"),
  path.join(appData, "npm", "node_modules", "pagefind", "lib", "runner", "bin.cjs"),
];

const runner = candidates.find((candidate) => {
  try {
    return candidate && fs.statSync(candidate).size > 0;
  } catch {
    return false;
  }
});

if (!runner) {
  console.error("Pagefind is not available. Install it locally or globally, then try again.");
  process.exit(1);
}

const result = spawnSync(
  process.execPath,
  [
    runner,
    "--site",
    ".",
    "--glob",
    "{village_sites,village_transcripts,shrine_sites}/*.html",
    "--verbose",
  ],
  {
    cwd: root,
    stdio: "inherit",
    windowsHide: true,
  },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
