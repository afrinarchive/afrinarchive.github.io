import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const SOURCE_VILLAGE_DIR = String.raw`C:\Users\Zachar\Desktop\Vault Backup\1 - PhD\Villages`;
const SOURCE_TRANSCRIPT_DIR = String.raw`C:\Users\Zachar\Desktop\Vault Backup\1 - PhD\Villages_Transcripts`;
const OUTPUT_DIR = path.join(ROOT, "smart-search", "data");
const OUTPUT_FILE = path.join(OUTPUT_DIR, "search-documents.json");

const ENTITY_MAP = new Map([
  ["amp", "&"],
  ["lt", "<"],
  ["gt", ">"],
  ["quot", '"'],
  ["apos", "'"],
  ["nbsp", " "],
  ["middot", "·"],
  ["ndash", "-"],
  ["mdash", "-"],
  ["hellip", "..."],
  ["rsquo", "'"],
  ["lsquo", "'"],
  ["rdquo", '"'],
  ["ldquo", '"'],
  ["copy", "©"],
  ["bull", "•"],
  ["trade", "™"],
]);

const FRONTMATTER_RE = /^---\s*\r?\n([\s\S]*?)\r?\n---\s*\r?\n?/;
const LEAFLET_RE = /```leaflet\s*([\s\S]*?)```/i;
const LAT_RE = /^\s*lat\s*:\s*([\-0-9.]+)/im;
const LON_RE = /^\s*long\s*:\s*([\-0-9.]+)/im;

function decodeHtmlEntities(text) {
  return text.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (full, entity) => {
    if (entity.startsWith("#x") || entity.startsWith("#X")) {
      const code = Number.parseInt(entity.slice(2), 16);
      return Number.isNaN(code) ? full : String.fromCodePoint(code);
    }
    if (entity.startsWith("#")) {
      const code = Number.parseInt(entity.slice(1), 10);
      return Number.isNaN(code) ? full : String.fromCodePoint(code);
    }
    return ENTITY_MAP.get(entity) ?? full;
  });
}

function normalizeWhitespace(text) {
  return text
    .replace(/\r/g, "")
    .replace(/[ \t\f\v]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .trim();
}

function parseFrontmatter(text) {
  const match = text.match(FRONTMATTER_RE);
  if (!match) {
    return { fields: new Map(), raw: "", body: text };
  }

  const raw = match[1];
  const body = text.slice(match[0].length);
  const fields = new Map();
  let currentKey = "";
  let currentList = null;

  for (const line of raw.split(/\r?\n/)) {
    const keyMatch = line.match(/^([^:#][^:]*?):\s*(.*)$/);
    if (keyMatch) {
      currentKey = keyMatch[1].trim();
      currentList = null;
      const value = keyMatch[2].trim();
      if (value) {
        fields.set(currentKey, value);
      } else {
        fields.set(currentKey, []);
        currentList = fields.get(currentKey);
      }
      continue;
    }

    const listMatch = line.match(/^\s*-\s*(.*)$/);
    if (listMatch && currentKey) {
      if (!Array.isArray(fields.get(currentKey))) {
        fields.set(currentKey, []);
      }
      currentList = fields.get(currentKey);
      currentList.push(listMatch[1].trim());
    }
  }

  return { fields, raw, body };
}

function stringifyFrontmatterFields(fields) {
  const lines = [];
  for (const [key, value] of fields.entries()) {
    if (Array.isArray(value)) {
      if (!value.length) {
        continue;
      }
      lines.push(`${key}: ${value.join(", ")}`);
      continue;
    }
    if (value) {
      lines.push(`${key}: ${value}`);
    }
  }
  return lines.join("\n");
}

function cleanMarkdown(text) {
  return normalizeWhitespace(
    decodeHtmlEntities(
      text
        .replace(/<!--[\s\S]*?-->/g, " ")
        .replace(/```leaflet[\s\S]*?```/gi, " ")
        .replace(/```[\s\S]*?```/g, " ")
        .replace(/^---[\s\S]*?---\s*/m, " ")
        .replace(/!\[\[.*?\]\]/g, " ")
        .replace(/!\[.*?\]\(.*?\)/g, " ")
        .replace(/\[\[([^|\]]+)\|([^\]]+)\]\]/g, "$2")
        .replace(/\[\[([^\]]+)\]\]/g, "$1")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 $2")
        .replace(/^#{1,6}\s*/gm, "")
        .replace(/^\s*>\s?/gm, "")
        .replace(/[*_~`]+/g, "")
    )
  );
}

function parseLeafletCoords(text) {
  const block = text.match(LEAFLET_RE)?.[1];
  if (!block) {
    return { lat: null, lon: null };
  }
  const lat = block.match(LAT_RE)?.[1];
  const lon = block.match(LON_RE)?.[1];
  return {
    lat: lat ? Number.parseFloat(lat) : null,
    lon: lon ? Number.parseFloat(lon) : null,
  };
}

function toSiteRelativeUrl(folder, basename) {
  return `../${folder}/${encodeURIComponent(`${basename}.html`)}`;
}

function resolveLinkedVillages(village, villageNames) {
  if (villageNames.has(village)) {
    return [village];
  }

  const candidates = village
    .split(/\s+and\s+/i)
    .map((part) => normalizeWhitespace(part))
    .filter(Boolean);
  const matches = candidates.filter((candidate) => villageNames.has(candidate));
  return matches.length ? matches : [village];
}

async function loadMarkdownFilenames(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
}

async function buildVillageDocs(filenames) {
  const docs = [];
  const names = new Set();

  for (const filename of filenames) {
    const basename = path.basename(filename, ".md");
    const fullPath = path.join(SOURCE_VILLAGE_DIR, filename);
    const rawText = await fs.readFile(fullPath, "utf8");
    const frontmatter = parseFrontmatter(rawText);
    const coords = parseLeafletCoords(rawText);
    const displayText = cleanMarkdown(
      [stringifyFrontmatterFields(frontmatter.fields), frontmatter.body].filter(Boolean).join("\n\n")
    );

    docs.push({
      id: `village:${basename}`,
      kind: "village",
      name: basename,
      village: basename,
      linkedVillages: [basename],
      url: toSiteRelativeUrl("village_sites", basename),
      source: "",
      lat: coords.lat,
      lon: coords.lon,
      searchText: rawText,
      text: displayText,
    });
    names.add(basename);
  }

  return { docs, names };
}

async function buildTranscriptDocs(filenames, villageNames) {
  const docs = [];

  for (const filename of filenames) {
    const basename = path.basename(filename, ".md");
    const fullPath = path.join(SOURCE_TRANSCRIPT_DIR, filename);
    const rawText = await fs.readFile(fullPath, "utf8");
    const frontmatter = parseFrontmatter(rawText);
    const transcriptVillageRaw = frontmatter.fields.get("transcript village");
    const transcriptVillage = typeof transcriptVillageRaw === "string"
      ? transcriptVillageRaw
      : basename.split("_")[0];
    const transcriptSourceRaw = frontmatter.fields.get("transcript source");
    const transcriptSource = typeof transcriptSourceRaw === "string" ? transcriptSourceRaw : "";
    const displayText = cleanMarkdown(
      [stringifyFrontmatterFields(frontmatter.fields), frontmatter.body].filter(Boolean).join("\n\n")
    );

    docs.push({
      id: `transcript:${basename}`,
      kind: "transcript",
      name: basename,
      village: transcriptVillage,
      linkedVillages: resolveLinkedVillages(transcriptVillage, villageNames),
      url: toSiteRelativeUrl("village_transcripts", basename),
      source: transcriptSource,
      lat: null,
      lon: null,
      searchText: rawText,
      text: displayText,
    });
  }

  return docs;
}

async function build() {
  const [villageFiles, transcriptFiles] = await Promise.all([
    loadMarkdownFilenames(SOURCE_VILLAGE_DIR),
    loadMarkdownFilenames(SOURCE_TRANSCRIPT_DIR),
  ]);

  const villageBuild = await buildVillageDocs(villageFiles);
  const transcriptDocs = await buildTranscriptDocs(transcriptFiles, villageBuild.names);
  const documents = [...villageBuild.docs, ...transcriptDocs];
  const resolvedVillageNames = new Set(villageBuild.docs.map((doc) => doc.village));
  const villagesWithCoords = villageBuild.docs.filter(
    (doc) => typeof doc.lat === "number" && typeof doc.lon === "number"
  ).length;
  const transcriptVillageMisses = transcriptDocs.filter(
    (doc) => !doc.linkedVillages.some((name) => resolvedVillageNames.has(name))
  ).length;

  const payload = {
    version: 2,
    builtAt: new Date().toISOString(),
    stats: {
      villageCount: villageBuild.docs.length,
      transcriptCount: transcriptDocs.length,
      villagesWithCoords,
      transcriptVillageMisses,
      documentCount: documents.length,
      source: "original_markdown_vault",
    },
    documents,
  };

  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.writeFile(OUTPUT_FILE, JSON.stringify(payload), "utf8");
  console.log(
    `Built smart-search data from markdown: ${payload.stats.villageCount} villages, ${payload.stats.transcriptCount} transcripts, ${payload.stats.villagesWithCoords} villages with coordinates.`
  );
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
