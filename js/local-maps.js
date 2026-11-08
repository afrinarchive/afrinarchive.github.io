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

    function flyoverStyle(renderer, satellite) {
        register(renderer);
        const style = streetStyle();
        style.sources['satellite-tiles'] = satellite;
        style.layers = [
            { id: 'satellite-layer', type: 'raster', source: 'satellite-tiles', minzoom: 0, maxzoom: 20 },
            // Existing overlays insert themselves before this transparent anchor.
            { id: 'labels-layer', type: 'background', paint: { 'background-opacity': 0 } },
            ...style.layers.filter(layer => layer.type === 'symbol')
        ];
        return style;
    }

    window.AfrinMaps = Object.freeze({ bounds, register, streetStyle, terrainSource, flyoverStyle });
})();
