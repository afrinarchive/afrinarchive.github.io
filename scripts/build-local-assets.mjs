import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = path.join(root, 'assets/vendor/manifest.json');
const hash = value => createHash('sha256').update(value).digest('hex');
const userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36';
const excluded = new Set(['node_modules', 'pagefind', 'assets', 'village_photos']);
let manifest;
try {
    manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
} catch (error) {
    if (error.code !== 'ENOENT') throw error;
    manifest = { files: {}, replacements: {}, fontStylesheets: {} };
}

async function pagesIn(directory) {
    const pages = [];
    for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
        if (entry.name.startsWith('.') || excluded.has(entry.name)) continue;
        const filename = path.join(directory, entry.name);
        if (entry.isDirectory()) pages.push(...await pagesIn(filename));
        else if (entry.name.endsWith('.html')) pages.push(filename);
    }
    return pages;
}

async function write(filename, contents) {
    const target = path.join(root, filename);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, contents);
}

async function get(url) {
    const response = await fetch(url, { headers: { 'User-Agent': userAgent }, signal: AbortSignal.timeout(45000) });
    if (!response.ok) throw new Error(`${response.status}: ${url}`);
    return Buffer.from(await response.arrayBuffer());
}

async function download(url, filename) {
    for (const [previousUrl, previousFile] of Object.entries(manifest.files)) {
        if (previousUrl !== url && previousFile.path === filename) delete manifest.files[previousUrl];
    }
    const previous = manifest.files[url];
    if (previous) {
        const contents = await fs.readFile(path.join(root, previous.path));
        if (hash(contents) !== previous.sha256) throw new Error(`Local asset changed: ${previous.path}`);
        return previous.path;
    }
    const contents = await get(url);
    await write(filename, contents);
    manifest.files[url] = { path: filename, sha256: hash(contents) };
    await write('assets/vendor/manifest.json', `${JSON.stringify(manifest, null, 2)}\n`);
    console.log(`Saved ${filename}`);
    return filename;
}

// Keep the versions already used by the pages. Leaflet and Font Awesome also
// need the images and font files referenced from their CSS.
const libraries = [
    ['https://unpkg.com/maplibre-gl@4.3.2/dist/maplibre-gl.js', 'assets/vendor/maplibre-gl-4.3.2/maplibre-gl.js'],
    ['https://unpkg.com/maplibre-gl@4.3.2/dist/maplibre-gl.css', 'assets/vendor/maplibre-gl-4.3.2/maplibre-gl.css'],
    ['https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', 'assets/vendor/leaflet-1.9.4/leaflet.js'],
    ['https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'assets/vendor/leaflet-1.9.4/leaflet.css'],
    ['https://d3js.org/d3.v7.min.js', 'assets/vendor/d3-7.9.2/d3.min.js'],
    ['https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css', 'assets/vendor/fontawesome-6.4.0/css/all.min.css']
];
for (const [url, filename] of libraries) {
    manifest.replacements[url] = await download(url, filename);
}
for (const name of ['layers.png', 'layers-2x.png', 'marker-icon.png', 'marker-icon-2x.png', 'marker-shadow.png']) {
    await download(`https://unpkg.com/leaflet@1.9.4/dist/images/${name}`, `assets/vendor/leaflet-1.9.4/images/${name}`);
}
const iconCss = await fs.readFile(path.join(root, 'assets/vendor/fontawesome-6.4.0/css/all.min.css'), 'utf8');
for (const filename of new Set([...iconCss.matchAll(/url\((?:['"])?\.\.\/webfonts\/([^)'"\s]+)/g)].map(match => match[1]))) {
    await download(`https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/${filename}`, `assets/vendor/fontawesome-6.4.0/webfonts/${filename}`);
}
for (const [url, filename] of [
    ['https://unpkg.com/maplibre-gl@4.3.2/LICENSE.txt', 'assets/vendor/maplibre-gl-4.3.2/LICENSE.txt'],
    ['https://unpkg.com/leaflet@1.9.4/LICENSE', 'assets/vendor/leaflet-1.9.4/LICENSE'],
    ['https://unpkg.com/d3@7.9.2/LICENSE', 'assets/vendor/d3-7.9.2/LICENSE'],
    ['https://unpkg.com/@fortawesome/fontawesome-free@6.4.0/LICENSE.txt', 'assets/vendor/fontawesome-6.4.0/LICENSE.txt'],
    ['https://unpkg.com/tailwindcss@3.4.17/LICENSE', 'assets/vendor/tailwindcss-LICENSE']
]) await download(url, filename);

const pages = await Promise.all((await pagesIn(root)).map(async filename => ({
    filename, original: await fs.readFile(filename, 'utf8')
})));
const fontUrls = new Set(pages.flatMap(page => [...page.original.matchAll(/https:\/\/fonts\.googleapis\.com\/[^\s"'<>)]*/g)].map(match => match[0].replaceAll('&amp;', '&'))));
for (const url of fontUrls) {
    const filename = `assets/fonts/fonts-${hash(url).slice(0, 12)}.css`;
    if (!manifest.fontStylesheets[url]) {
        let css = (await get(url)).toString('utf8');
        const fontFiles = new Set([...css.matchAll(/https:\/\/fonts\.gstatic\.com\/[^\s)'";]+/g)].map(match => match[0]));
        for (const fontUrl of fontFiles) {
            const local = await download(fontUrl, `assets/fonts/${hash(fontUrl).slice(0, 20)}${path.posix.extname(new URL(fontUrl).pathname)}`);
            css = css.replaceAll(fontUrl, `./${path.posix.basename(local)}`);
        }
        await write(filename, css);
        manifest.fontStylesheets[url] = filename;
        await write('assets/vendor/manifest.json', `${JSON.stringify(manifest, null, 2)}\n`);
    } else {
        await fs.access(path.join(root, manifest.fontStylesheets[url]));
    }
    manifest.replacements[url] = filename;
}

// Keep font licenses beside the downloaded fonts, including all language
// subsets returned by Google Fonts (no text-only or Latin-only subsetting).
const families = new Set(Object.keys(manifest.fontStylesheets).flatMap(url => new URL(url).searchParams.getAll('family').map(value => value.split(':')[0])));
for (const family of families) {
    const slug = family.toLowerCase().replaceAll(' ', '');
    await download(`https://raw.githubusercontent.com/google/fonts/main/ofl/${slug}/OFL.txt`, `assets/fonts/licenses/${slug}-OFL.txt`);
}

// Finish every download before changing any page. Replace asset references
// only: page text, inline styles, scripts, map providers and GoatCounter stay.
let changed = 0;
for (const page of pages) {
    const relative = filename => path.relative(path.dirname(page.filename), path.join(root, filename)).replaceAll('\\', '/');
    let html = page.original.replace(/<script\b[^>]*\bsrc=["']https:\/\/(?:cdn\.tailwindcss\.com\/?|cdn-tailwindcss\.vercel\.app\/?)['"][^>]*>\s*<\/script>/gi,
        `<link rel="stylesheet" href="${relative('assets/css/tailwind.css')}">`);
    html = html.replace(/<link\b[^>]*\brel=["']preconnect["'][^>]*\bhref=["']https:\/\/fonts\.(?:googleapis|gstatic)\.com\/?["'][^>]*>\r?\n?/gi, '');
    for (const [remote, local] of Object.entries(manifest.replacements)) {
        html = html.replaceAll(remote, relative(local)).replaceAll(remote.replaceAll('&', '&amp;'), relative(local));
    }
    if (html !== page.original) {
        await fs.writeFile(page.filename, html, 'utf8');
        changed += 1;
    }
}
await write('assets/vendor/manifest.json', `${JSON.stringify(manifest, null, 2)}\n`);
const result = spawnSync(process.execPath, [
    path.join(root, 'node_modules/tailwindcss/lib/cli.js'),
    '-c', 'tailwind.config.cjs', '-i', 'styles/tailwind.css', '-o', 'assets/css/tailwind.css', '--minify'
], { cwd: root, stdio: 'inherit' });
if (result.status !== 0) throw new Error('Tailwind CSS build failed.');
let mapsAvailable = false;
try {
    await fs.access(path.join(root, 'assets/maps/manifest.json'));
    mapsAvailable = true;
} catch (error) {
    if (error.code !== 'ENOENT') throw error;
}
if (mapsAvailable) await import('./link-local-maps.mjs');
console.log(`Updated asset references in ${changed} pages. Local assets and Tailwind CSS are ready.`);
