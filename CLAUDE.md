# Afrin Archive — Guide for LLMs

This file explains how the Afrin Archive website works, where its data comes from,
and the rules to follow when changing anything. Read this before editing.

## What this is

A static HTML archive preserving the villages, oral history, and cultural heritage of
Afrin, Syria. Live at **https://www.afrinarchive.com** via **GitHub Pages** (see `CNAME`).
Deployment = commit + push to `main` (commits are usually "Automated update of website content").
GitHub Pages URLs are **case-sensitive** and this repo is developed on Windows (case-insensitive),
so a link that works locally can 404 in production if the case is wrong.

## The most important thing to understand

**Most of this site is GENERATED. Do not hand-edit generated files and stop there —
the next pipeline run will overwrite your work.** Fix the *source* (vault notes,
master list, or generator scripts), or fix both the source and the generated file.

The generation pipeline lives OUTSIDE this repo:

```
C:\Users\Zachar\Desktop\update_site_Afrin_Archive\
```

| Script | Reads (source of truth) | Writes (generated) |
| :--- | :--- | :--- |
| `0_md_to_html_transcripts_and_subtitles.py` | vault transcript notes | `village_transcripts/*.html` |
| `1_md_to_html_villages.py` | vault village notes (incl. each note's `leaflet` block for coordinates) | `village_sites/*.html` |
| `2_make_village_list.py` | generated village pages | `00_names_nahiyas.md` (back into vault) |
| `3_00_village_names_creator.py` | village pages | `village_site_files/00_village_names.html` |
| `4_make_graph.py` | village pages | `village_site_files/graph-data.json`, `js/internal-link-graph-data.js` |
| `5_make_locations.py` | **master list note** (see below) | `village_sites/afrin_locations.json` |
| `6_calculate_stats.py` | transcripts + name list | stats injected into `index.html` |

`site_update_gui.py` / `update_afrin_archive.bat` run the pipeline.

## Where the source data lives (Obsidian vaults)

```
C:\Users\Zachar\Documents\Hatra\obsdian_vaults\Afrin Vault\Villages\          ← 366 village notes (primary)
C:\Users\Zachar\Documents\Hatra\obsdian_vaults\Afrin Vault\Villages_Transcripts\
C:\Users\Zachar\Documents\Hatra\obsdian_vaults\Zachar\1 - PhD\Villages\       ← copy of the village notes
C:\Users\Zachar\Documents\Hatra\obsdian_vaults\Zachar\1 - PhD\Villages_backup\ ← another copy
C:\Users\Zachar\Documents\Hatra\obsdian_vaults\Zachar\Files\for leaflet\000 Afrin Villages and Landmarks Master List 000.md
```

- Each village note has a `leaflet` code block with `lat:` / `long:` — this is where
  the village page's coordinates come from. **Exact values, no name lookup.**
- The **master list note** (last path above) is the single source of truth for
  `afrin_locations.json` (the markers shown on every village map). It contains the
  same 462 markers twice: once as YAML frontmatter `mapmarkers:` lines
  (`- [type, [lat, lng], "Name"]` — this is what `5_make_locations.py` parses) and
  once as `marker:` lines inside a ```leaflet block (used by Obsidian itself).
  **If you change one block, change both.**
- The village notes exist in three copies (paths above). When correcting note data,
  correct all three.

## Repo layout

| Path | What it is | Generated? |
| :--- | :--- | :--- |
| `index.html` | Homepage (cards link to all sections) | Hand-made; stats numbers injected by script 6 |
| `village_sites/` | 366 village pages + `afrin_locations.json` | **Generated** (scripts 1 and 5) |
| `village_transcripts/` | 379 transcript pages | **Generated** (script 0) |
| `village_site_files/` | `00_village_names.html`, `graph-data.json` | **Generated** (scripts 3, 4) |
| `js/` | `internal-link-graph-data.js` + graph code | data file **generated** (script 4) |
| `nahiyas/` | 8 nahiya (subdistrict) pages + `All_Nahiyas_Clickable_Maps.html` | Hand-made (script 1 *reads* the clickable maps for minimaps) |
| `village-directory/` | Searchable village directory with embedded dataset | Hand-made |
| `village_subtitles/` | `.srt` subtitle files + how-to page | `.srt` generated, page hand-made |
| `village_photos/` | Photos used by village pages | Source assets |
| `dialogue_project/` | Proverb-card gallery (`index.html` + `pics/`) | Hand-made |
| `archive-research-tools/`, `smart-search/`, `updates/`, `by-air/`, `sharafname/` | Standalone hand-made pages | Hand-made |
| `village_sites copy/` | Old backup of village pages. Not linked from anywhere; ignore it (do not bother updating it) | — |
| `landing/` | Homepage images/assets | Source assets |
| `CNAME` | Custom domain for GitHub Pages | Hand-made |

## Naming rules (critical)

- Village names with Kurdish characters (ê î û ç ş Ĥ) and apostrophes are used **as-is**
  in filenames, page names, note names, and `afrin_locations.json`. Never "normalize" them.
- Several distinct villages share a name. They are disambiguated with a ` - ` suffix:
  `Çobana - Reco` / `Çobana - Cindires`, `Elcara - Mabeta` / `Elcara - Bilbilê`,
  `Çolaqa - Bilbilê` / `Çolaqa - Cindires`, `Gazê - Erfîn` / `Gazê - Reco` / `Gazê - Şera`,
  `Zivingê - Bilbilê` / `Zivingê - Cindires`, `Gundê Mezin - above Ma'rata` /
  `Gundê Mezin - Shirawa area`, `Şêx - Mt Hawar`. This convention is **how the whole
  system differentiates them** — notes, pages, and database all use the identical string.
- **Match names exactly. Never use substring matching.** A substring match once gave
  four villages the coordinates of longer-named look-alikes (`Şera` matched `Xirabî Şera`, etc.).
- Non-settlement markers may legitimately repeat a name (two Roman bridges, two rail
  bridges, two SyriaTel towers). Settlement names are unique (modulo the ` - ` suffixes).

## How a village page's map works

Each generated village page contains:
- `const villageLat / villageLng` — hardcoded from the note's leaflet block; centers the map.
- `const mainVillageName = "<exact page name>"` — compared with `===` against `name`
  fields in `afrin_locations.json` to highlight the village's own marker.
  In the generator this must be written as a **raw JS string via `json.dumps`**, NOT
  HTML-escaped — `html.escape` turns `'` into `&#x27;` inside the script and the
  comparison silently fails (this was a real bug; it is fixed, keep it fixed).
- A `fetch('afrin_locations.json')` that draws every marker in the database.
  Adding extra JSON fields is safe (the JS reads only `name`, `lat`, `lng`, `type`).

## Transcripts covering two villages

Some videos cover a pair of villages; their transcript H1 is "X and Y" and the note/page
filename is `X_Y_<source>_<n>.html`. There is **no combined village page** — the
generator (script 0) creates one "Go to … Village Site" button per village.
Do not link to `../village_sites/X_Y.html`; it does not exist.

## Analytics

Every page carries (invisible, cookieless — no cookie banner needed):
```html
<script data-goatcounter="https://afrinarchive.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
```
Dashboard: https://afrinarchive.goatcounter.com. The tag is baked into the generator
templates (scripts 0, 1, 3). **Any new hand-made page must include it manually**, and
if a new generator/template is added, add the tag to it.

## Checklist before/after changing things

1. Editing village/transcript content? → Edit the **vault notes** (all 3 copies of
   village notes), then regenerate. Don't edit the generated HTML only.
2. Editing locations/markers? → Edit the **master list note** (both blocks!), then run
   `5_make_locations.py`. Don't edit `afrin_locations.json` only.
3. Editing generator output format? → Edit the scripts on the Desktop.
4. Adding a hand-made page? → Include the GoatCounter tag; use exact existing names
   for any village references; add a link from `index.html` if appropriate.
5. After bigger changes, a full-site link check is worthwhile: verify every internal
   `href`/`src` resolves to an existing file (mind URL-encoding and HTML entities in
   hrefs) and that no case mismatches exist (GitHub Pages is case-sensitive).
6. Deploy = commit + push to `main`.

## Known external/loose ends (as of 2026-06-12)

- **tirejafrin.com** has an expired SSL certificate — 339 outbound links show a browser
  warning. External site; nothing to do on our side.
- Some YouTube links are dead; they are rendered as non-clickable text with a
  "(no longer available)" note on the village pages. Six of those videos are *private*
  rather than deleted and could be restored if made public.
- **Qetlebiye** (Şera, `36.675264, 36.963866`) is a real village with a database entry
  and a clickable-map area, but no website page; its vault note is an empty stub.
  It is a *different place* from neighbouring **Qerqîna** (whose aliases confusingly
  include "Qetlebiye").
- The site theme: warm paper background (`#f7f5f3`), Kurdish-flag accents
  (green `#009A3D`, yellow `#FFCC00`, red `#F32837`), brown subtext `#8b7355`,
  Inter for UI text, translucent rounded cards. New pages should match it.
