'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const excluded = new Set(['node_modules', 'pagefind', 'assets', 'village_photos']);
const remoteAsset = /(?:fonts\.(?:googleapis|gstatic)\.com|cdn\.tailwindcss\.com|cdn-tailwindcss\.vercel\.app|unpkg\.com|cdnjs\.cloudflare\.com|d3js\.org)/;

function htmlFiles(directory) {
    return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
        if (entry.name.startsWith('.') || excluded.has(entry.name)) return [];
        const filename = path.join(directory, entry.name);
        if (entry.isDirectory()) return htmlFiles(filename);
        return entry.name.endsWith('.html') ? [filename] : [];
    });
}

function existingFile(filename) {
    assert.ok(fs.statSync(filename).isFile(), filename);
    // The public host treats case differently from Windows.
    let directory = root;
    for (const part of path.relative(root, filename).split(path.sep)) {
        assert.ok(fs.readdirSync(directory).includes(part), `Incorrect filename case: ${filename}`);
        directory = path.join(directory, part);
    }
}

test('all pages load fonts and libraries locally', () => {
    for (const filename of htmlFiles(root)) {
        const html = fs.readFileSync(filename, 'utf8');
        const resourceTags = html.match(/<(?:script|link)\b[^>]*>/gi) || [];
        for (const tag of resourceTags) {
            const url = tag.match(/\b(?:src|href)=["']([^"']+)["']/i)?.[1];
            if (!url) continue;
            assert.ok(!remoteAsset.test(url), `External asset in ${filename}: ${url}`);
            if (/(?:^|\/)assets\//.test(url)) existingFile(path.resolve(path.dirname(filename), url));
        }
        for (const match of html.matchAll(/@import\s+url\(['"]?([^)'"\s]+)/g)) {
            assert.ok(!remoteAsset.test(match[1]), `External font import in ${filename}`);
            existingFile(path.resolve(path.dirname(filename), match[1]));
        }
    }
});

test('downloaded libraries, fonts and licenses match their saved checksums', () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(root, 'assets/vendor/manifest.json'), 'utf8'));
    for (const { path: filename, sha256 } of Object.values(manifest.files)) {
        const absolute = path.join(root, filename);
        existingFile(absolute);
        assert.equal(createHash('sha256').update(fs.readFileSync(absolute)).digest('hex'), sha256, filename);
    }
    const stylesheets = [
        ...Object.values(manifest.fontStylesheets),
        'assets/vendor/leaflet-1.9.4/leaflet.css',
        'assets/vendor/maplibre-gl-4.3.2/maplibre-gl.css',
        'assets/vendor/fontawesome-6.4.0/css/all.min.css'
    ];
    for (const filename of stylesheets) {
        const absolute = path.join(root, filename);
        for (const match of fs.readFileSync(absolute, 'utf8').matchAll(/url\(\s*['"]?([^)'"\s]+)/g)) {
            const url = match[1];
            if (url.startsWith('data:') || url.startsWith('#')) continue;
            assert.ok(!/^https?:/.test(url), `External CSS resource: ${filename}: ${url}`);
            existingFile(path.resolve(path.dirname(absolute), url));
        }
    }
});

test('compiled Tailwind includes responsive page spacing', () => {
    const css = fs.readFileSync(path.join(root, 'assets/css/tailwind.css'), 'utf8');
    assert.ok(css.includes('.sm\\:p-6{padding:1.5rem}'));
    assert.ok(css.includes('.md\\:p-8{padding:2rem}'));
    assert.ok(css.includes('.max-w-4xl{max-width:56rem}'));
});

test('GoatCounter remains on the homepage and archive pages', () => {
    for (const filename of ['index.html', 'shrine_sites/Kozê Qey.html', "village_sites/Abû Ke'bê Xerbî.html", 'smart-search/index.html', 'by-air/index.html']) {
        const html = fs.readFileSync(path.join(root, filename), 'utf8');
        assert.match(html, /data-goatcounter="https:\/\/afrinarchive\.goatcounter\.com\/count"/);
        assert.match(html, /src="\/\/gc\.zgo\.at\/count\.js"/);
    }
});
