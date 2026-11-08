# Local map data

Street maps, map labels and terrain are served from this folder. Visitors do
not contact CARTO, AWS terrain tiles or MapLibre's glyph service.

The saved area is Afrin and its surroundings: longitude 36.30 to 37.35,
latitude 36.00 to 37.10. It contains all 463 locations currently in the
archive. Smart Search keeps map panning within this area. Street data goes
to zoom 15 and stays sharp when enlarged; terrain goes to zoom 13.

Esri satellite imagery remains online to preserve the existing close-up
detail. GoatCounter is unchanged. The local files total about 167 MB.

## Sources

- `streets.pmtiles`: regional extract of the 2026-11-07 Protomaps build,
  based on OpenStreetMap. OpenStreetMap attribution is retained on the maps.
- `voyager-source.json`: the published CARTO Voyager style. Its BSD license
  is in `licenses/`. The generated `style.js` replaces its hosted data,
  font and sprite addresses with local files at runtime.
- `glyphs/`: label font files for the character ranges used by the map's
  name fields, including Kurdish and Arabic. The original Montserrat,
  Open Sans and Noto font licenses are included.
- `terrain/`: Mapzen Terrarium elevation tiles saved from the public
  elevation-tiles-prod dataset. The maps retain terrain attribution.
- `vendor/`: local PMTiles, Leaflet–MapLibre adapter and RTL text plugin.
  The RTL plugin version works with the site's existing MapLibre 4.3.2.

Download URLs, sizes and checksums are recorded in `manifest.json` for
reproducibility. Those source URLs are used during data preparation, not
when visitors use a map.

## Building

```powershell
npm run build:maps
```

This reuses the saved files, restores missing downloads, generates the map
style and updates the page references. Preparing a fresh street archive
requires the PMTiles extraction tool; the script can obtain it on Windows
when the archive is absent. Configuration is in `scripts/map-data-config.json`.

The normal site updater runs `build:assets`, which also reapplies local map
references after pages are regenerated. It does not download map data again.
The village and shrine source templates also reference the local terrain.

Serving `streets.pmtiles` with HTTP byte-range support avoids downloading
the whole archive for a map. The current public host supports this. Local
preview servers without byte ranges work too, using one cached full download.
