(function () {
    'use strict';

    const base = new URL('../assets/maps/', document.currentScript.src);
    const bounds = [36.3, 36.0, 37.35, 37.1];
    const registered = new WeakSet();
    const url = filename => new URL(filename, base).href.replaceAll('%7B', '{').replaceAll('%7D', '}');

    // The public host supports byte ranges. This fallback also lets ordinary
    // local preview servers read the regional archive without range support.
    class ArchiveSource {
        constructor(filename) { this.url = filename; this.complete = null; }
        getKey() { return this.url; }
        async getBytes(offset, length, signal) {
            if (this.complete) return { data: (await this.complete).slice(offset, offset + length) };
            const response = await fetch(this.url, { headers: { Range: `bytes=${offset}-${offset + length - 1}` }, signal });
            if (response.status === 200) {
                this.complete ||= response.arrayBuffer();
                return { data: (await this.complete).slice(offset, offset + length) };
            }
            if (response.status !== 206) throw new Error(`Local map archive could not load (${response.status}).`);
            return { data: await response.arrayBuffer(), etag: response.headers.get('etag') || undefined };
        }
    }

    function register(renderer) {
        if (registered.has(renderer)) return;
        const protocol = new pmtiles.Protocol();
        protocol.add(new pmtiles.PMTiles(new ArchiveSource(url('streets.pmtiles'))));
        renderer.addProtocol('pmtiles', protocol.tile);
        if (renderer.getRTLTextPluginStatus() === 'unavailable') {
            renderer.setRTLTextPlugin(url('vendor/mapbox-gl-rtl-text-0.2.3.js'), true);
        }
        registered.add(renderer);
    }

    function streetStyle() {
        const style = structuredClone(window.AfrinLocalMapStyle);
        style.sources.protomaps.url = `pmtiles://${url('streets.pmtiles')}`;
        style.glyphs = url('glyphs/{fontstack}/{range}.pbf');
        style.sprite = url('sprites/voyager');
        return style;
    }

    function terrainSource() {
        return {
            type: 'raster-dem',
            tiles: [url('terrain/{z}/{x}/{y}.png')],
            tileSize: 256,
            encoding: 'terrarium',
            maxzoom: 13,
            bounds,
            attribution: 'Terrain: Mapzen / USGS SRTM, GMTED2010 / NOAA ETOPO1'
        };
    }

    // Satellite pictures are stored on this site; see assets/maps/README.md.
    function satelliteSource() {
        return {
            type: 'raster',
            tiles: [url('satellite/{z}/{x}/{y}.webp')],
            tileSize: 256,
            minzoom: 8,
            maxzoom: 14,
            bounds,
            attribution: 'Contains modified Copernicus Sentinel data'
        };
    }

    const terrain = { source: 'terrainSource', exaggeration: 1.2 };

    function satelliteStyle() {
        return {
            version: 8,
            sources: { satellite: satelliteSource(), terrainSource: terrainSource() },
            layers: [
                { id: 'background', type: 'background', paint: { 'background-color': '#8f7f63' } },
                { id: 'satellite-layer', type: 'raster', source: 'satellite' }
            ],
            terrain
        };
    }

    // The archive's own markers name every place, so the street map's different
    // spellings of the same villages are left out.
    function villageStreetStyle(renderer) {
        register(renderer);
        const style = streetStyle();
        style.sources.terrainSource = terrainSource();
        style.terrain = terrain;
        style.layers = style.layers.filter(layer => !layer.id.startsWith('place_'));
        return style;
    }

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Could not load ${src}`));
            document.head.appendChild(script);
        });
    }

    let streetFiles = null;
    function loadStreetFiles() {
        if (!streetFiles) {
            const ready = window.pmtiles ? Promise.resolve() : loadScript(url('vendor/pmtiles-4.5.0.js'));
            streetFiles = ready.then(() => window.AfrinLocalMapStyle ? null : loadScript(url('style.js')));
            streetFiles.catch(() => { streetFiles = null; });
        }
        return streetFiles;
    }

    // Keeps the map inside the saved area and adds a button that changes
    // between the satellite pictures and the street map.
    function setUpMap(renderer, map) {
        map.setMinZoom(8);
        map.setMaxZoom(18);
        map.setMaxBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]]);

        let street = false;
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = 'Street Map';
        button.style.cssText = 'width:auto;height:auto;padding:7px 12px;font:600 14px Inter,sans-serif;color:#222;';
        button.addEventListener('click', async () => {
            button.disabled = true;
            try {
                if (!street) await loadStreetFiles();
                map.setStyle(street ? satelliteStyle() : villageStreetStyle(renderer), { diff: false });
                street = !street;
                button.textContent = street ? 'Satellite' : 'Street Map';
            } catch (error) {
                console.error('Could not change the map:', error);
            } finally {
                button.disabled = false;
            }
        });
        const group = document.createElement('div');
        group.className = 'maplibregl-ctrl maplibregl-ctrl-group';
        group.appendChild(button);
        map.addControl({ onAdd: () => group, onRemove: () => group.remove() }, 'top-left');
    }

    function flyoverStyle(renderer) {
        register(renderer);
        const style = streetStyle();
        style.sources['satellite-tiles'] = satelliteSource();
        style.layers = [
            { id: 'background', type: 'background', paint: { 'background-color': '#8f7f63' } },
            { id: 'satellite-layer', type: 'raster', source: 'satellite-tiles' },
            // Existing overlays insert themselves before this transparent anchor.
            { id: 'labels-layer', type: 'background', paint: { 'background-opacity': 0 } },
            ...style.layers.filter(layer => layer.type === 'symbol')
        ];
        return style;
    }

    window.AfrinMaps = Object.freeze({ bounds, register, streetStyle, terrainSource, satelliteSource, satelliteStyle, setUpMap, flyoverStyle });
})();
