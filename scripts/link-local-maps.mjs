import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const previewIndex = process.argv.indexOf('--preview');
const preview = previewIndex >= 0 ? path.resolve(process.argv[previewIndex + 1]) : null;
await fs.access(path.join(root, 'assets/maps/style.js'));
await fs.access(path.join(root, 'assets/maps/streets.pmtiles'));
let changed = 0;

async function write(relative, original, updated) {
    if (original === updated) return;
    const target = path.join(preview || root, relative);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, updated, 'utf8');
    changed += 1;
}

// Existing village and shrine pages are switched to the pictures stored on this
// site. Pages that already use them are left alone, so this is safe to repeat.
for (const folder of ['village_sites', 'shrine_sites']) {
    for (const entry of await fs.readdir(path.join(root, folder))) {
        if (!entry.endsWith('.html')) continue;
        const relative = `${folder}/${entry}`;
        const original = await fs.readFile(path.join(root, relative), 'utf8');
        if (!original.includes('arcgisonline.com/')) continue;
        const updated = original
            .replace(/style:\s*\{\s*version:\s*8,[\s\S]*?terrain:\s*\{[^}]*\}\s*\}/, 'style: window.AfrinMaps.satelliteStyle()')
            .replace(/const initialZoom = 13\.5;/, 'const initialZoom = 13;')
            .replace(/zoom: 13\.5,/, 'zoom: 13,')
            .replace(/^([ \t]*)(\w+)\.addControl\(new maplibregl\.NavigationControl\(\)\);/m, '$1window.AfrinMaps.setUpMap(maplibregl, $2);\n$&');
        if (updated.includes('arcgisonline.com/') || !updated.includes('AfrinMaps.setUpMap(')) throw new Error(`Map replacement failed: ${relative}`);
        await write(relative, original, updated);
    }
}

const smartFilename = 'smart-search/app.js';
const smartOriginal = await fs.readFile(path.join(root, smartFilename), 'utf8');
const smartUpdated = smartOriginal.replace('state.map = L.map("map", { attributionControl: false });', 'state.map = L.map("map", { attributionControl: false, minZoom: 6, maxZoom: 19, maxBounds: [[36.0, 36.3], [37.1, 37.35]], maxBoundsViscosity: 1 });')
    .replace(/L\.tileLayer\("https:\/\/\{s\}\.basemaps\.cartocdn\.com\/rastertiles\/voyager\/\{z\}\/\{x\}\/\{y\}\.png",\s*\{[\s\S]*?\}\)\.addTo\(state\.map\);/, 'window.AfrinMaps.register(maplibregl);\n  L.maplibreGL({ style: window.AfrinMaps.streetStyle(), interactive: false }).addTo(state.map);');
if (smartUpdated.includes('basemaps.cartocdn.com/')) throw new Error('Smart Search map replacement failed.');
await write(smartFilename, smartOriginal, smartUpdated);

const additions = [
    '<script src="../assets/maps/vendor/pmtiles-4.5.0.js"></script>',
    '<script src="../assets/maps/style.js"></script>',
    '<script src="../js/local-maps.js"></script>'
].join('\n    ');
for (const relative of ['smart-search/index.html', 'by-air/index.html']) {
    const original = await fs.readFile(path.join(root, relative), 'utf8');
    if (original.includes('assets/maps/style.js')) continue;
    let updated;
    if (relative.startsWith('smart-search')) {
        updated = original.replace('</head>', '  <link rel="stylesheet" href="../assets/vendor/maplibre-gl-4.3.2/maplibre-gl.css">\n</head>')
            .replace('<script type="module" src="./app.js"></script>', `<script src="../assets/vendor/maplibre-gl-4.3.2/maplibre-gl.js"></script>\n    ${additions}\n    <script src="../assets/maps/vendor/leaflet-maplibre-gl-0.0.22.js"></script>\n  <script type="module" src="./app.js"></script>`);
    } else {
        updated = original.replace(/(<script type="module" crossorigin src="\.\/assets\/[^"\n]+\.js"><\/script>)/, `${additions}\n    $1`);
    }
    await write(relative, original, updated);
}

const flyoverHtml = await fs.readFile(path.join(root, 'by-air/index.html'), 'utf8');
const flyoverFilename = `by-air/${flyoverHtml.match(/<script type="module" crossorigin src="\.\/([^"\n]+\.js)"/)[1]}`;
const flyoverOriginal = await fs.readFile(path.join(root, flyoverFilename), 'utf8');
if (!flyoverOriginal.includes('S7=window.AfrinMaps.flyoverStyle(I6),')) {
    const start = flyoverOriginal.search(/S7=(?:\{version:8,|window\.AfrinMaps\.flyoverStyle\()/);
    const end = flyoverOriginal.indexOf(',Nr={reset:', start);
    if (start < 0 || end < 0) throw new Error('Could not locate the flyover style.');
    let updated = `${flyoverOriginal.slice(0, start)}S7=window.AfrinMaps.flyoverStyle(I6)${flyoverOriginal.slice(end)}`;
    updated = updated.replace(/oe\.addSource\("terrain-source",\{type:"raster-dem",tiles:\["https:\/\/s3\.amazonaws\.com\/elevation-tiles-prod\/terrarium\/\{z\}\/\{x\}\/\{y\}\.png"\],tileSize:256,encoding:"terrarium",maxzoom:13\}\)/, 'oe.addSource("terrain-source",window.AfrinMaps.terrainSource())');
    if (updated.includes('elevation-tiles-prod/terrarium/')) throw new Error('Flyover terrain replacement failed.');
    await write(flyoverFilename, flyoverOriginal, updated);
}

console.log(`${preview ? 'Prepared preview copies of' : 'Updated'} ${changed} map files.`);
