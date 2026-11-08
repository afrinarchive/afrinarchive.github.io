import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const directory = path.join(root, 'assets/maps');
const config = JSON.parse(await fs.readFile(path.join(root, 'scripts/map-data-config.json'), 'utf8'));
await fs.mkdir(directory, { recursive: true });
let manifest;
try { manifest = JSON.parse(await fs.readFile(path.join(directory, 'manifest.json'), 'utf8')); }
catch (error) { if (error.code !== 'ENOENT') throw error; manifest = { bounds: config.bounds, files: {} }; }
const sha = contents => createHash('sha256').update(contents).digest('hex');
let downloads = 0;

async function saveManifest() {
    await fs.writeFile(path.join(directory, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
}

async function download(url, filename) {
    const target = path.join(directory, filename);
    const previous = manifest.files[filename];
    if (previous) {
        try {
            if (sha(await fs.readFile(target)) !== previous.sha256) throw new Error(`Changed map file: ${filename}`);
            return;
        } catch (error) {
            if (error.code !== 'ENOENT') throw error;
        }
    }
    let response;
    for (let attempt = 0; attempt < 3; attempt += 1) {
        response = await fetch(url, { signal: AbortSignal.timeout(45000) });
        if (response.ok) break;
        if (response.status < 500) throw new Error(`${response.status}: ${url}`);
    }
    if (!response.ok) throw new Error(`${response.status}: ${url}`);
    const contents = Buffer.from(await response.arrayBuffer());
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, contents);
    manifest.files[filename] = { source: url, bytes: contents.length, sha256: sha(contents) };
    downloads += 1;
    if (downloads % 50 === 0) { await saveManifest(); console.log(`Saved ${downloads} map files.`); }
}

async function pool(jobs, concurrency = 6) {
    let next = 0;
    const results = await Promise.allSettled(Array.from({ length: concurrency }, async () => {
        while (next < jobs.length) await jobs[next++]();
    }));
    await saveManifest();
    const failure = results.find(result => result.status === 'rejected');
    if (failure) throw failure.reason;
}

// The small regional archive is extracted at build time. Visitors only read
// our copy; they never contact the source's daily-build server.
const streets = path.join(directory, 'streets.pmtiles');
try { await fs.access(streets); }
catch {
    if (process.platform !== 'win32') throw new Error('Put a regional streets.pmtiles in assets/maps, using the bounds in map-data-config.json.');
    const tools = path.join(os.tmpdir(), 'afrin-map-build/pmtiles');
    await fs.mkdir(tools, { recursive: true });
    const executable = path.join(tools, 'pmtiles.exe');
    try { await fs.access(executable); }
    catch {
        const zip = path.join(os.tmpdir(), 'afrin-map-build/pmtiles.zip');
        const url = 'https://github.com/protomaps/go-pmtiles/releases/download/v1.31.2/go-pmtiles_1.31.2_Windows_x86_64.zip';
        const response = await fetch(url);
        if (!response.ok) throw new Error(`${response.status}: PMTiles tool download`);
        await fs.writeFile(zip, Buffer.from(await response.arrayBuffer()));
        const quote = value => `'${value.replaceAll("'", "''")}'`;
        const unpack = spawnSync('powershell.exe', ['-NoProfile', '-Command', `Expand-Archive -LiteralPath ${quote(zip)} -DestinationPath ${quote(tools)} -Force`], { stdio: 'inherit', windowsHide: true });
        if (unpack.status !== 0) throw new Error('Could not unpack the PMTiles tool.');
    }
    const extract = spawnSync(executable, ['extract', config.streetsSource, streets, `--bbox=${config.bounds.join(',')}`, '--maxzoom=15', '--download-threads=4'], { stdio: 'inherit', windowsHide: true });
    if (extract.status !== 0) throw new Error('Regional street data extraction failed.');
}
const streetBytes = await fs.readFile(streets);
if (manifest.files['streets.pmtiles'] && sha(streetBytes) !== manifest.files['streets.pmtiles'].sha256) throw new Error('Street archive checksum mismatch.');
manifest.files['streets.pmtiles'] = { source: config.streetsSource, bytes: streetBytes.length, sha256: sha(streetBytes) };

await download(config.styleSource, 'voyager-source.json');
const original = JSON.parse(await fs.readFile(path.join(directory, 'voyager-source.json'), 'utf8'));
const stacks = new Set(original.layers.flatMap(layer => layer.layout?.['text-font'] ? [layer.layout['text-font'].join(',')] : []));
stacks.add('Noto Sans Regular');
const jobs = [];
for (const stack of stacks) for (const start of config.glyphRanges) {
    const range = `${start}-${start + 255}`;
    const source = original.glyphs.replace('{fontstack}', encodeURIComponent(stack)).replace('{range}', range);
    jobs.push(() => download(source, `glyphs/${stack}/${range}.pbf`));
}
for (const suffix of ['.json', '.png', '@2x.json', '@2x.png']) jobs.push(() => download(`${original.sprite}${suffix}`, `sprites/voyager${suffix}`));
for (const [source, filename] of [
    ['https://unpkg.com/pmtiles@4.5.0/dist/pmtiles.js', 'vendor/pmtiles-4.5.0.js'],
    ['https://raw.githubusercontent.com/protomaps/PMTiles/main/LICENSE', 'licenses/pmtiles-LICENSE'],
    ['https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.0.22/leaflet-maplibre-gl.js', 'vendor/leaflet-maplibre-gl-0.0.22.js'],
    ['https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.0.22/LICENSE', 'licenses/leaflet-maplibre-gl-LICENSE'],
    ['https://unpkg.com/@mapbox/mapbox-gl-rtl-text@0.2.3/mapbox-gl-rtl-text.min.js', 'vendor/mapbox-gl-rtl-text-0.2.3.js'],
    ['https://unpkg.com/@mapbox/mapbox-gl-rtl-text@0.2.3/LICENSE.md', 'licenses/rtl-text-0.2.3-LICENSE.md'],
    ['https://raw.githubusercontent.com/CartoDB/basemap-styles/master/LICENSE.md', 'licenses/carto-style-LICENSE.md'],
    ['https://raw.githubusercontent.com/tilezen/joerd/master/docs/attribution.md', 'licenses/terrain-attribution.md'],
    ['https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/OFL.txt', 'licenses/montserrat-OFL.txt'],
    ['https://raw.githubusercontent.com/google/fonts/main/ofl/opensans/OFL.txt', 'licenses/opensans-OFL.txt'],
    ['https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/OFL.txt', 'licenses/notosans-OFL.txt'],
    ['https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/OFL.txt', 'licenses/notosansjp-OFL.txt']
]) jobs.push(() => download(source, filename));

const tileX = (lon, zoom) => Math.floor((lon + 180) / 360 * 2 ** zoom);
const tileY = (lat, zoom) => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * 2 ** zoom);
const [west, south, east, north] = config.bounds;
for (let zoom = 0; zoom <= 13; zoom += 1) {
    for (let x = tileX(west, zoom); x <= tileX(east, zoom); x += 1) {
        for (let y = tileY(north, zoom); y <= tileY(south, zoom); y += 1) {
            const suffix = `${zoom}/${x}/${y}.png`;
            jobs.push(() => download(`https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${suffix}`, `terrain/${suffix}`));
        }
    }
}
console.log(`Preparing ${jobs.length} glyph, terrain and supporting files; cached downloads are reused.`);
await pool(jobs);

// The published CARTO style is BSD-licensed. Its data and font requests are
// replaced with our regional OSM archive and local glyphs and sprites.
const style = structuredClone(original);
style.sources = { protomaps: { type: 'vector', url: 'STREETS_ARCHIVE', bounds: config.bounds, attribution: '&copy; OpenStreetMap contributors; cartography &copy; CARTO' } };
style.glyphs = 'LOCAL_GLYPHS';
style.sprite = 'LOCAL_SPRITE';
await fs.writeFile(path.join(directory, 'style.js'), `window.AfrinLocalMapStyle = ${JSON.stringify(style)};\n`, 'utf8');
manifest.bounds = config.bounds;
manifest.terrainEncoding = 'terrarium';
manifest.terrainMaxZoom = 13;
manifest.streetMaxZoom = 15;
await saveManifest();
console.log(`Map files ready. Downloaded ${downloads} files this run.`);
