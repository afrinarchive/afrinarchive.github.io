'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const maps = path.join(root, 'assets/maps');
const config = JSON.parse(fs.readFileSync(path.join(root, 'scripts/map-data-config.json'), 'utf8'));

function environment(fetch) {
    let archive;
    const renderer = { addProtocol() {}, getRTLTextPluginStatus: () => 'loaded' };
    const context = vm.createContext({
        window: {}, URL, structuredClone, fetch,
        document: { currentScript: { src: 'https://archive.test/js/local-maps.js' } },
        pmtiles: {
            Protocol: class { add() {} tile() {} },
            PMTiles: class { constructor(source) { archive = source; } }
        }
    });
    vm.runInContext(fs.readFileSync(path.join(maps, 'style.js'), 'utf8'), context);
    vm.runInContext(fs.readFileSync(path.join(root, 'js/local-maps.js'), 'utf8'), context);
    context.window.AfrinMaps.register(renderer);
    return { api: context.window.AfrinMaps, renderer, archive };
}

test('local map files match their saved checksums', () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(maps, 'manifest.json'), 'utf8'));
    for (const [filename, entry] of Object.entries(manifest.files)) {
        const data = fs.readFileSync(path.join(maps, filename));
        assert.equal(data.length, entry.bytes, filename);
        assert.equal(createHash('sha256').update(data).digest('hex'), entry.sha256, filename);
        if (filename.startsWith('terrain/')) {
            assert.equal(data.subarray(1, 4).toString(), 'PNG', filename);
            assert.equal(data.readUInt32BE(16), 256, filename);
            assert.equal(data.readUInt32BE(20), 256, filename);
        }
    }
});

test('local terrain covers every archive location at its highest detail', () => {
    const points = JSON.parse(fs.readFileSync(path.join(root, 'village_sites/afrin_locations.json'), 'utf8'));
    const [west, south, east, north] = config.bounds;
    for (const point of points) {
        assert.ok(point.lng >= west && point.lng <= east && point.lat >= south && point.lat <= north, point.name);
        const x = Math.floor((point.lng + 180) / 360 * 8192);
        const y = Math.floor((1 - Math.asinh(Math.tan(point.lat * Math.PI / 180)) / Math.PI) / 2 * 8192);
        assert.ok(fs.existsSync(path.join(maps, `terrain/13/${x}/${y}.png`)), point.name);
    }
});

test('street styles, labels and terrain use local addresses while satellite imagery stays intact', () => {
    const { api, renderer } = environment();
    const street = api.streetStyle();
    assert.equal(street.sources.protomaps.url, 'pmtiles://https://archive.test/assets/maps/streets.pmtiles');
    assert.equal(street.glyphs, 'https://archive.test/assets/maps/glyphs/{fontstack}/{range}.pbf');
    assert.equal(street.sprite, 'https://archive.test/assets/maps/sprites/voyager');
    const terrain = api.terrainSource();
    assert.equal(terrain.tiles[0], 'https://archive.test/assets/maps/terrain/{z}/{x}/{y}.png');
    assert.equal(terrain.encoding, 'terrarium');
    assert.equal(terrain.maxzoom, 13);
    const satellite = { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] };
    const flyover = api.flyoverStyle(renderer, satellite);
    assert.equal(flyover.sources['satellite-tiles'], satellite);
    assert.ok(flyover.layers.some(layer => layer.id === 'labels-layer'));
    assert.ok(flyover.layers.slice(2).every(layer => layer.type === 'symbol'));
    for (const stack of new Set(street.layers.flatMap(layer => layer.layout?.['text-font'] ? [layer.layout['text-font'].join(',')] : []))) {
        for (const start of config.glyphRanges) assert.ok(fs.existsSync(path.join(maps, `glyphs/${stack}/${start}-${start + 255}.pbf`)));
    }
});

test('a preview server without range support downloads the archive only once', async () => {
    const data = Uint8Array.from([10, 20, 30, 40, 50, 60]).buffer;
    let requests = 0;
    const { archive } = environment(async () => {
        requests += 1;
        return { status: 200, arrayBuffer: async () => data };
    });
    assert.deepEqual([...new Uint8Array((await archive.getBytes(0, 3)).data)], [10, 20, 30]);
    assert.deepEqual([...new Uint8Array((await archive.getBytes(3, 2)).data)], [40, 50]);
    assert.equal(requests, 1);
});

test('range-capable hosting requests only the needed bytes', async () => {
    const requests = [];
    const { archive } = environment(async (_url, options) => {
        requests.push(options.headers.Range);
        return { status: 206, headers: new Map([['etag', 'test']]), arrayBuffer: async () => Uint8Array.from([1, 2]).buffer };
    });
    await archive.getBytes(100, 2);
    await archive.getBytes(500, 2);
    assert.deepEqual(requests, ['bytes=100-101', 'bytes=500-501']);
});

test('generated map pages use local terrain and keep satellite imagery and GoatCounter', () => {
    for (const folder of ['village_sites', 'shrine_sites']) {
        for (const entry of fs.readdirSync(path.join(root, folder))) {
            if (!entry.endsWith('.html')) continue;
            const html = fs.readFileSync(path.join(root, folder, entry), 'utf8');
            if (!html.includes('window.AfrinMaps.terrainSource()')) continue;
            assert.match(html, /src="\.\.\/js\/local-maps\.js"/);
            assert.ok(!html.includes('elevation3d.arcgis.com'));
            assert.ok(html.includes('server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/'));
            assert.ok(html.includes('data-goatcounter="https://afrinarchive.goatcounter.com/count"'));
        }
    }
    const smart = fs.readFileSync(path.join(root, 'smart-search/app.js'), 'utf8');
    assert.ok(!smart.includes('basemaps.cartocdn.com'));
    assert.ok(smart.includes('window.AfrinMaps.streetStyle()'));
    assert.ok(fs.readFileSync(path.join(root, 'assets/css/tailwind.css'), 'utf8').includes('.lightbox-overlay.hidden{display:none}'));
});
