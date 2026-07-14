const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');

const html = fs.readFileSync('index.html', 'utf8');
const inlineScripts = [...html.matchAll(/<script\b(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)];
const homepageScript = inlineScripts
    .map(match => match[1])
    .find(script => script.includes('function setupGraph()'));

assert.ok(homepageScript, 'Could not find the homepage script.');

function makeGraphEnvironment(useMobileRenderer) {
    const loadedScripts = [];
    const animationFrames = [];
    let mobileInitializationCount = 0;
    let desktopInitializationCount = 0;
    const elements = {
        'graph-container': {},
        'graph-canvas': {},
        'loading-indicator': { textContent: '', style: {} }
    };

    global.window = {
        AfrinMobileGraph: null,
        AfrinStarscape: null,
        matchMedia() {
            return { matches: useMobileRenderer };
        },
        requestAnimationFrame(callback) {
            animationFrames.push(callback);
            return animationFrames.length;
        }
    };
    global.document = {
        addEventListener() {},
        createElement() {
            return {};
        },
        getElementById(id) {
            return elements[id];
        },
        head: {
            appendChild(script) {
                loadedScripts.push(script.src);
                global.window.AfrinMobileGraph = {
                    async initMobileGraph() {
                        mobileInitializationCount += 1;
                    }
                };
                global.window.AfrinStarscape = {
                    async initStarscape() {
                        desktopInitializationCount += 1;
                    }
                };
                script.onload();
            }
        }
    };

    const api = new Function(`${homepageScript}\nreturn { setupGraph, initializeGraph };`)();
    return {
        api,
        loadedScripts,
        flushAnimationFrame() {
            const callbacks = animationFrames.splice(0, animationFrames.length);
            callbacks.forEach(callback => callback());
        },
        getMobileInitializationCount: () => mobileInitializationCount,
        getDesktopInitializationCount: () => desktopInitializationCount
    };
}

test('mobile automatically uses the lightweight renderer', async () => {
    const environment = makeGraphEnvironment(true);
    environment.api.setupGraph();

    assert.equal(environment.loadedScripts.length, 0, 'The graph must wait for the first screen to paint.');
    environment.flushAnimationFrame();
    assert.equal(environment.loadedScripts.length, 0, 'The graph must wait for a second paint frame.');
    environment.flushAnimationFrame();
    await environment.api.initializeGraph();

    assert.equal(environment.loadedScripts.length, 1);
    assert.match(environment.loadedScripts[0], /starscape-mobile\.js/);
    assert.equal(environment.getMobileInitializationCount(), 1);
    assert.equal(environment.getDesktopInitializationCount(), 0);
});

test('desktop automatically uses the Three.js renderer', async () => {
    const environment = makeGraphEnvironment(false);
    environment.api.setupGraph();
    await environment.api.initializeGraph();

    assert.equal(environment.loadedScripts.length, 1);
    assert.match(environment.loadedScripts[0], /starscape\.bundle\.js/);
    assert.equal(environment.getMobileInitializationCount(), 0);
    assert.equal(environment.getDesktopInitializationCount(), 1);
});

test('the graph renderer is loaded only once', async () => {
    const environment = makeGraphEnvironment(true);
    environment.api.setupGraph();
    environment.flushAnimationFrame();
    environment.flushAnimationFrame();
    await environment.api.initializeGraph();
    await environment.api.initializeGraph();

    assert.equal(environment.loadedScripts.length, 1);
    assert.equal(environment.getMobileInitializationCount(), 1);
});

test('card photographs use native lazy loading', () => {
    const pictures = [...html.matchAll(/<picture class="section-picture"[\s\S]*?<\/picture>/g)];
    assert.equal(pictures.length, 12);
    pictures.forEach(picture => {
        assert.match(picture[0], /loading="lazy"/);
        assert.match(picture[0], /decoding="async"/);
        assert.match(picture[0], /fetchpriority="low"/);
        assert.match(picture[0], /media="\(max-width: 768px\)"/);
    });
});

test('the phone graph keeps every village without shipping desktop-level clutter', () => {
    const desktopGraph = JSON.parse(fs.readFileSync('landing/starscape-data.json', 'utf8'));
    const mobileGraph = JSON.parse(fs.readFileSync('landing/starscape-mobile-data.json', 'utf8'));
    const desktopVillages = desktopGraph.n.filter(node => node[1] === 1).map(node => node[0]).sort();
    const mobileVillages = mobileGraph.n.filter(node => node[1] === 1).map(node => node[0]).sort();
    const mobileDegree = new Uint16Array(mobileGraph.n.length);

    for (let edgeIndex = 0; edgeIndex < mobileGraph.e.length; edgeIndex += 2) {
        mobileDegree[mobileGraph.e[edgeIndex]] += 1;
        mobileDegree[mobileGraph.e[edgeIndex + 1]] += 1;
    }

    assert.deepEqual(mobileVillages, desktopVillages, 'Every village must remain in the phone graph.');
    assert.ok(mobileGraph.n.length < desktopGraph.n.length * 0.1, 'The phone graph should contain less than 10% of the desktop nodes.');
    assert.ok(
        mobileGraph.n.every((node, index) => node[1] !== 1 || mobileDegree[index] > 0),
        'Every village in the phone graph must remain connected.'
    );
    assert.ok(
        fs.statSync('landing/starscape-mobile-data.json').size < 125000,
        'The uncompressed phone graph data must remain below 125 KB.'
    );
});

test('the original mobile layout remains unchanged around the graph', () => {
    assert.ok(
        html.indexOf('class="graph-column"') < html.indexOf('class="content-column"'),
        'The graph must remain before the title and search area.'
    );
    assert.match(html, /@media \(max-width: 1024px\)[\s\S]*?\.layout-container\s*\{[\s\S]*?gap: 30px;/);
    assert.match(html, /@media \(max-width: 768px\)[\s\S]*?\.main-section\s*\{\s*padding: 30px 15px;/);
    assert.doesNotMatch(html, /\.content-column\s*\{\s*order:/);
    assert.doesNotMatch(html, /\.graph-column\s*\{\s*order:/);
});

test('the phone graph has no buttons and uses direct gestures', () => {
    const rendererSource = fs.readFileSync('landing/starscape-mobile.js', 'utf8');
    assert.doesNotMatch(html, /graph-mobile-control|data-graph-action/);
    assert.doesNotMatch(rendererSource, /is-mobile-fullscreen|graph-fullscreen-open/);
    assert.match(html, /#graph-canvas\s*\{\s*touch-action: pan-y;/);
});

test('the mobile canvas renderer initializes without WebGL or a render loop', async () => {
    const rendererSource = fs.readFileSync('landing/starscape-mobile.js', 'utf8');
    const eventHandlers = new Map();
    const drawCalls = [];
    let animationFrameCount = 0;
    let pointerCaptureCount = 0;
    const context = {
        arc() {},
        beginPath() {},
        clearRect() {},
        drawImage(...argumentsList) {
            drawCalls.push(argumentsList);
        },
        fill() {},
        fillRect() {},
        fillText() {},
        lineTo() {},
        moveTo() {},
        stroke() {},
        strokeText() {}
    };
    const canvas = {
        width: 0,
        height: 0,
        style: {},
        addEventListener(type, handler) {
            eventHandlers.set(type, handler);
        },
        getBoundingClientRect() {
            return { left: 0, top: 0, width: 360, height: 320 };
        },
        getContext(type) {
            assert.equal(type, '2d');
            return context;
        },
        setPointerCapture() {
            pointerCaptureCount += 1;
        }
    };
    const container = {
        clientWidth: 360,
        clientHeight: 320,
        getBoundingClientRect() {
            return { left: 0, top: 0, width: 360, height: 320 };
        }
    };
    const loadingIndicator = { textContent: '', style: {} };
    const tooltip = { hidden: true, offsetWidth: 100, offsetHeight: 40, style: {} };
    const labelCanvas = { style: {} };
    const elements = {
        'graph-tooltip': tooltip,
        'graph-tooltip-label': { textContent: '' },
        'graph-tooltip-kind': { textContent: '' },
        'graph-label-canvas': labelCanvas
    };
    const graph = JSON.parse(fs.readFileSync('landing/starscape-mobile-data.json', 'utf8'));

    global.fetch = async () => ({ ok: true, async json() { return graph; } });
    global.window = {
        addEventListener() {},
        open() {},
        requestAnimationFrame(callback) {
            animationFrameCount += 1;
            callback();
            return animationFrameCount;
        }
    };
    global.document = {
        body: {},
        createElement() {
            return { width: 0, height: 0, getContext: () => context };
        },
        getElementById(id) {
            return elements[id];
        }
    };
    global.ResizeObserver = class {
        observe() {}
    };
    global.window.ResizeObserver = global.ResizeObserver;

    new Function(rendererSource)();
    await global.window.AfrinMobileGraph.initMobileGraph({
        container,
        canvas,
        loadingIndicator,
        graphUrl: 'graph.json',
        homeNodeId: graph.n[graph.h][0]
    });

    assert.equal(canvas.width, 360);
    assert.equal(canvas.height, 320);
    assert.equal(loadingIndicator.style.display, 'none');
    assert.ok(eventHandlers.has('pointerdown'));
    assert.ok(eventHandlers.has('pointermove'));
    assert.ok(eventHandlers.has('pointerup'));
    assert.ok(eventHandlers.has('wheel'));
    assert.ok(animationFrameCount <= 2, 'The mobile graph should not animate continuously.');

    const initialGraphWidth = drawCalls.at(-1)[3];
    eventHandlers.get('pointerdown')({ pointerId: 1, pointerType: 'touch', clientX: 100, clientY: 140 });
    eventHandlers.get('pointerdown')({ pointerId: 2, pointerType: 'touch', clientX: 200, clientY: 140 });
    let pinchPrevented = false;
    eventHandlers.get('pointermove')({
        pointerId: 2,
        pointerType: 'touch',
        clientX: 250,
        clientY: 140,
        preventDefault() { pinchPrevented = true; }
    });
    assert.equal(pinchPrevented, true, 'Pinching the graph should control the graph instead of the page.');
    assert.ok(pointerCaptureCount >= 2, 'Both fingers should remain attached to the graph during a pinch.');
    assert.ok(drawCalls.at(-1)[3] > initialGraphWidth, 'Moving two fingers apart should zoom into the graph.');
});
