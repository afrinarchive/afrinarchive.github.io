(function () {
    'use strict';

    // Set this to false to keep the crisp graph but remove the opening turn.
    // A full rollback is: git checkout HEAD~1 -- landing/starscape-mobile.js
    const ENABLE_INTRO_SPIN = true;

    const BASE_WIDTH = 900;
    const BASE_HEIGHT = 700;
    const BASE_PADDING = 30;
    const MIN_ZOOM = 1;
    const MAX_ZOOM = 12;
    const MAX_PIXEL_RATIO = 2;

    // Camera. TILT leans the cloud so the turn reads as depth rather than a
    // sideways slide. PERSPECTIVE is the distance to the eye; larger is flatter.
    const TILT = 0.22;
    const PERSPECTIVE = 3600;

    // The opening turn: one full revolution, then it stops for good.
    const INTRO_DURATION = 8000;
    const SETTLED_ZOOM = 1.65;

    // If frames cost more than this, the turn is abandoned and the graph
    // snaps to its resting state. A slow phone gets the static picture.
    const SLOW_FRAME_MS = 25;
    const WARMUP_FRAMES = 3;
    const SAMPLE_FRAMES = 12;

    const GLIDE_DURATION = 700;

    // How many names to allow at zoom 1, before the steep climb with zoom and
    // before collisions cut it down. Raise or lower these four numbers to make
    // the graph busier or quieter. Names are only ever drawn when the graph is
    // still, so none of this affects the turn or a drag.
    const VILLAGE_LABEL_BASE_SMALL = 30;
    const VILLAGE_LABEL_BASE = 52;
    const TERM_LABEL_BASE_SMALL = 12;
    const TERM_LABEL_BASE = 22;
    const LABEL_CELL = 18;
    const SCREEN_MARGIN = 8;

    const BACKGROUND = '#100e0b';
    const EDGE_COLOUR = 'rgba(158, 196, 168, 0.11)';
    const TAG_COLOUR = '198, 168, 132';
    const VILLAGE_COLOUR = '134, 239, 172';
    const HOME_COLOUR = '#ffcc00';

    const TAG_ALPHA = [0.58, 0.4, 0.26];
    const VILLAGE_ALPHA = [1, 0.74, 0.48];
    const BAND_SIZE = [1.15, 1, 0.85];

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function median(values) {
        const sorted = [...values].sort((a, b) => a - b);
        return sorted[Math.floor(sorted.length / 2)];
    }

    async function initMobileGraph({
        container,
        canvas,
        loadingIndicator,
        graphUrl,
        homeNodeId
    }) {
        if (!container || !canvas || !loadingIndicator) {
            throw new Error('The mobile graph container is incomplete.');
        }

        const context = canvas.getContext('2d', { alpha: false });
        if (!context) throw new Error('This browser cannot draw the mobile graph.');

        const tooltip = document.getElementById('graph-tooltip');
        const tooltipLabel = document.getElementById('graph-tooltip-label');
        const tooltipKind = document.getElementById('graph-tooltip-kind');
        const labelCanvas = document.getElementById('graph-label-canvas');
        if (labelCanvas) labelCanvas.style.display = 'none';

        loadingIndicator.textContent = 'Loading graph data...';
        const response = await fetch(graphUrl, { credentials: 'omit', priority: 'low' });
        if (!response.ok) throw new Error(`Graph data request failed with ${response.status}.`);
        const graph = await response.json();
        if (!Array.isArray(graph.n) || !Array.isArray(graph.e) || !Number.isInteger(graph.h)) {
            throw new Error('The graph data has an unexpected format.');
        }

        const nodes = graph.n;
        const edges = graph.e;
        const nodeCount = nodes.length;
        const homeIndex = graph.h;

        const rawX = new Float32Array(nodeCount);
        const rawY = new Float32Array(nodeCount);
        const rawZ = new Float32Array(nodeCount);
        const isVillage = new Uint8Array(nodeCount);
        const degree = new Uint16Array(nodeCount);
        const baseX = new Float32Array(nodeCount);
        const baseY = new Float32Array(nodeCount);
        const band = new Uint8Array(nodeCount);
        const screenX = new Float32Array(nodeCount);
        const screenY = new Float32Array(nodeCount);
        const outcode = new Uint8Array(nodeCount);

        for (let index = 0; index < nodeCount; index += 1) {
            const node = nodes[index];
            rawX[index] = Number(node[2]);
            rawY[index] = Number(node[3]);
            rawZ[index] = Number(node[4]);
            isVillage[index] = node[1] === 1 ? 1 : 0;
        }

        for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 2) {
            degree[edges[edgeIndex]] += 1;
            degree[edges[edgeIndex + 1]] += 1;
        }

        // The edges drawn while the graph is moving. Village to village only,
        // which is 1,459 of the 7,895 lines. The rest come back when it stops.
        const liteEdges = [];
        for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 2) {
            const first = edges[edgeIndex];
            const second = edges[edgeIndex + 1];
            if (isVillage[first] && isVillage[second]) liteEdges.push(first, second);
        }

        // The turn must not make the graph swell and shrink, so the fit is
        // measured across a whole revolution and then held fixed.
        const cosTilt = Math.cos(TILT);
        const sinTilt = Math.sin(TILT);
        let halfWidth = 1;
        let halfHeight = 1;
        const depthSamples = [];
        for (let step = 0; step < 32; step += 1) {
            const angle = (step / 32) * Math.PI * 2;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);
            for (let index = 0; index < nodeCount; index += 1) {
                const rotatedX = rawX[index] * cos + rawZ[index] * sin;
                const rotatedZ = rawZ[index] * cos - rawX[index] * sin;
                const tiltedY = rawY[index] * cosTilt - rotatedZ * sinTilt;
                const tiltedZ = rawY[index] * sinTilt + rotatedZ * cosTilt;
                const k = PERSPECTIVE / (PERSPECTIVE + tiltedZ);
                halfWidth = Math.max(halfWidth, Math.abs(rotatedX * k));
                halfHeight = Math.max(halfHeight, Math.abs(tiltedY * k));
                if (step % 4 === 0) depthSamples.push(tiltedZ);
            }
        }

        const modelScale = Math.min(
            (BASE_WIDTH / 2 - BASE_PADDING) / halfWidth,
            (BASE_HEIGHT / 2 - BASE_PADDING) / halfHeight
        );

        // The cloud is far denser in the middle than at its edges, so evenly
        // spaced depth cuts would put nearly everything in one band and the
        // near-and-far shading would not show. These cuts are read off the
        // data instead, which keeps them right if the graph is ever rebuilt.
        depthSamples.sort((first, second) => first - second);
        const nearCut = depthSamples[Math.floor(depthSamples.length / 3)];
        const farCut = depthSamples[Math.floor((depthSamples.length * 2) / 3)];

        let projectedAngle = NaN;

        function project(angle) {
            if (angle === projectedAngle) return;
            projectedAngle = angle;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);
            for (let index = 0; index < nodeCount; index += 1) {
                const rotatedX = rawX[index] * cos + rawZ[index] * sin;
                const rotatedZ = rawZ[index] * cos - rawX[index] * sin;
                const tiltedY = rawY[index] * cosTilt - rotatedZ * sinTilt;
                const tiltedZ = rawY[index] * sinTilt + rotatedZ * cosTilt;
                const k = PERSPECTIVE / (PERSPECTIVE + tiltedZ);
                baseX[index] = BASE_WIDTH / 2 + rotatedX * k * modelScale;
                baseY[index] = BASE_HEIGHT / 2 + tiltedY * k * modelScale;
                band[index] = tiltedZ < nearCut ? 0 : (tiltedZ < farCut ? 1 : 2);
            }
        }

        // Every node is a label candidate, ranked once by how many things it
        // connects to. Village names are kept apart from archive terms so that
        // villages get first claim on the space, the way the desktop graph
        // labels every village page it can fit.
        const ranked = Array.from({ length: nodeCount }, (_, index) => index)
            .filter(index => index !== homeIndex && degree[index] > 0)
            .sort((first, second) => degree[second] - degree[first]);
        const villageLabels = ranked.filter(index => isVillage[index]);
        const termLabels = ranked.filter(index => !isVillage[index]);

        let cssWidth = 1;
        let cssHeight = 1;
        let zoom = MIN_ZOOM;
        let panX = 0;
        let panY = 0;
        let angle = 0;
        let selectedIndex = -1;
        let lowPower = false;
        let gestureActive = false;
        let frameHandle = 0;

        let intro = null;
        let glide = null;
        let frameTimes = [];
        let framesSeen = 0;

        const activePointers = new Map();
        let pinchState = null;

        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        function getView() {
            const fitScale = Math.min(cssWidth / BASE_WIDTH, cssHeight / BASE_HEIGHT);
            const scale = fitScale * zoom;
            const width = BASE_WIDTH * scale;
            const height = BASE_HEIGHT * scale;
            return {
                scale,
                x: (cssWidth - width) / 2 + panX,
                y: (cssHeight - height) / 2 + panY
            };
        }

        // One pass turns the fixed layout into screen positions and records
        // which edge of the screen each node falls outside. A line whose two
        // ends are off the same edge cannot cross the screen, so it is dropped
        // before it is ever drawn. Zooming in therefore gets cheaper, not dearer.
        function toScreen(view) {
            for (let index = 0; index < nodeCount; index += 1) {
                const x = view.x + baseX[index] * view.scale;
                const y = view.y + baseY[index] * view.scale;
                screenX[index] = x;
                screenY[index] = y;
                let code = 0;
                if (x < -SCREEN_MARGIN) code = 1;
                else if (x > cssWidth + SCREEN_MARGIN) code = 2;
                if (y < -SCREEN_MARGIN) code |= 4;
                else if (y > cssHeight + SCREEN_MARGIN) code |= 8;
                outcode[index] = code;
            }
        }

        function drawEdges(moving) {
            const list = moving ? liteEdges : edges;
            let drawn = 0;
            context.beginPath();
            for (let edgeIndex = 0; edgeIndex < list.length; edgeIndex += 2) {
                const first = list[edgeIndex];
                const second = list[edgeIndex + 1];
                if (outcode[first] & outcode[second]) continue;
                context.moveTo(screenX[first], screenY[first]);
                context.lineTo(screenX[second], screenY[second]);
                drawn += 1;
            }
            context.strokeStyle = EDGE_COLOUR;
            context.lineWidth = 0.6;
            context.stroke();
            return drawn;
        }

        function drawDots(dotScale) {
            for (let type = 0; type < 2; type += 1) {
                const colour = type === 1 ? VILLAGE_COLOUR : TAG_COLOUR;
                const alphas = type === 1 ? VILLAGE_ALPHA : TAG_ALPHA;
                for (let bandIndex = 0; bandIndex < 3; bandIndex += 1) {
                    context.beginPath();
                    let drew = false;
                    for (let index = 0; index < nodeCount; index += 1) {
                        if (isVillage[index] !== type || band[index] !== bandIndex) continue;
                        if (index === homeIndex || outcode[index]) continue;
                        const x = screenX[index];
                        const y = screenY[index];
                        const radius = type === 1
                            ? (1.8 + Math.min(2.2, degree[index] * 0.045)) * dotScale * BAND_SIZE[bandIndex]
                            : 1.15 * dotScale * BAND_SIZE[bandIndex];
                        context.moveTo(x + radius, y);
                        context.arc(x, y, radius, 0, Math.PI * 2);
                        drew = true;
                    }
                    if (!drew) continue;
                    context.fillStyle = `rgba(${colour}, ${alphas[bandIndex]})`;
                    context.fill();
                }
            }
        }

        function drawHome(dotScale) {
            const x = screenX[homeIndex];
            const y = screenY[homeIndex];
            const radius = 5 * dotScale;
            const glow = context.createRadialGradient(x, y, 0, x, y, radius * 4);
            glow.addColorStop(0, 'rgba(255, 204, 0, 0.42)');
            glow.addColorStop(1, 'rgba(255, 204, 0, 0)');
            context.fillStyle = glow;
            context.beginPath();
            context.arc(x, y, radius * 4, 0, Math.PI * 2);
            context.fill();
            context.fillStyle = HOME_COLOUR;
            context.beginPath();
            context.arc(x, y, radius, 0, Math.PI * 2);
            context.fill();
        }

        // A name is placed only if every grid square it needs is still free.
        // Numeric keys, so no strings are built while placing labels.
        const occupied = new Set();

        function reserve(x, y, width, fontSize) {
            const left = Math.floor((x - width / 2 - 3) / LABEL_CELL) + 512;
            const right = Math.floor((x + width / 2 + 3) / LABEL_CELL) + 512;
            const top = Math.floor((y - fontSize - 4) / LABEL_CELL) + 512;
            const bottom = Math.floor((y + 3) / LABEL_CELL) + 512;
            for (let row = top; row <= bottom; row += 1) {
                for (let column = left; column <= right; column += 1) {
                    if (occupied.has(row * 1024 + column)) return false;
                }
            }
            for (let row = top; row <= bottom; row += 1) {
                for (let column = left; column <= right; column += 1) {
                    occupied.add(row * 1024 + column);
                }
            }
            return true;
        }

        // The width the desktop graph uses. Estimating it costs nothing and
        // avoids asking the browser to measure hundreds of names every frame.
        function estimateWidth(label, fontSize) {
            return Math.min(260, Math.max(24, label.length * fontSize * 0.56));
        }

        function placeLabels(candidates, limit, fontSize, offset, colour, weight) {
            if (limit < 1) return 0;
            context.font = `${weight}${fontSize}px Inter, "Noto Sans", system-ui, sans-serif`;
            context.fillStyle = colour;
            let drawn = 0;
            // Three passes, so the nearest names claim their space first and
            // the ones behind the cloud only fill the gaps that are left.
            for (let pass = 0; pass < 3 && drawn < limit; pass += 1) {
                for (let position = 0; position < candidates.length && drawn < limit; position += 1) {
                    const index = candidates[position];
                    if (band[index] !== pass) continue;
                    const x = screenX[index];
                    const y = screenY[index] - offset;
                    if (x < -140 || x > cssWidth + 140 || y < -20 || y > cssHeight + 20) continue;
                    const label = String(nodes[index][0]);
                    if (!reserve(x, y, estimateWidth(label, fontSize), fontSize)) continue;
                    drawn += 1;
                    context.globalAlpha = pass === 2 ? 0.62 : 1;
                    context.strokeText(label, x, y);
                    context.fillText(label, x, y);
                }
            }
            context.globalAlpha = 1;
            return drawn;
        }

        function drawLabels() {
            occupied.clear();
            context.textAlign = 'center';
            context.textBaseline = 'bottom';
            context.strokeStyle = 'rgba(0, 0, 0, 0.9)';
            context.lineWidth = 2.2;

            // Zooming in is how you see the size of the archive, so the
            // allowance climbs steeply with the zoom, as it does on the desktop.
            const growth = Math.pow(zoom, 1.65);
            const small = cssWidth < 500;

            const homeX = screenX[homeIndex];
            const homeY = screenY[homeIndex] - 12;
            context.font = `700 13px Inter, "Noto Sans", system-ui, sans-serif`;
            context.fillStyle = HOME_COLOUR;
            reserve(homeX, homeY, estimateWidth(String(nodes[homeIndex][0]), 13), 13);
            context.strokeText(String(nodes[homeIndex][0]), homeX, homeY);
            context.fillText(String(nodes[homeIndex][0]), homeX, homeY);

            placeLabels(
                villageLabels,
                Math.round((small ? VILLAGE_LABEL_BASE_SMALL : VILLAGE_LABEL_BASE) * growth),
                small ? 11.5 : 12.5, 8, '#d6fbe0', '600 '
            );
            placeLabels(
                termLabels,
                Math.round((small ? TERM_LABEL_BASE_SMALL : TERM_LABEL_BASE) * growth),
                small ? 10.5 : 11.5, 7, '#c6b092', ''
            );

            context.textAlign = 'left';
        }

        function render(moving) {
            const view = getView();
            const dotScale = Math.min(1.5, Math.max(0.85, view.scale / 0.7));
            context.fillStyle = BACKGROUND;
            context.fillRect(0, 0, cssWidth, cssHeight);
            toScreen(view);
            drawEdges(moving);
            drawDots(dotScale);
            drawHome(dotScale);
            if (!moving) drawLabels();

            if (selectedIndex >= 0) {
                context.beginPath();
                context.arc(screenX[selectedIndex], screenY[selectedIndex], 12, 0, Math.PI * 2);
                context.strokeStyle = 'rgba(255, 255, 255, 0.85)';
                context.lineWidth = 1.5;
                context.stroke();
            }
        }

        function finishIntro() {
            intro = null;
            angle = 0;
            zoom = SETTLED_ZOOM;
            panX = 0;
            panY = 0;
            project(angle);
            requestFrame();
        }

        function measureFrame(cost) {
            if (!intro) return;
            framesSeen += 1;
            if (framesSeen <= WARMUP_FRAMES) return;
            frameTimes.push(cost);
            if (frameTimes.length < SAMPLE_FRAMES) return;
            if (median(frameTimes) > SLOW_FRAME_MS) {
                lowPower = true;
                finishIntro();
            }
            frameTimes = [];
        }

        function frame() {
            frameHandle = 0;
            const now = performance.now();
            let moving = gestureActive;

            if (intro) {
                const progress = Math.min(1, (now - intro.start) / INTRO_DURATION);
                const eased = easeInOutCubic(progress);
                angle = eased * Math.PI * 2;
                zoom = MIN_ZOOM + (SETTLED_ZOOM - MIN_ZOOM) * eased;
                moving = true;
                if (progress >= 1) {
                    intro = null;
                    angle = 0;
                    zoom = SETTLED_ZOOM;
                    moving = false;
                }
            } else if (glide) {
                const progress = Math.min(1, (now - glide.start) / GLIDE_DURATION);
                angle = glide.from + glide.distance * easeOutCubic(progress);
                moving = true;
                if (progress >= 1) {
                    glide = null;
                    moving = gestureActive;
                }
            }

            project(angle);
            const started = performance.now();
            render(moving);
            const cost = performance.now() - started;
            measureFrame(cost);

            if (intro || glide) requestFrame();
        }

        function requestFrame() {
            if (!frameHandle) frameHandle = window.requestAnimationFrame(frame);
        }

        function stopMotion() {
            intro = null;
            glide = null;
        }

        function resize() {
            const width = Math.max(1, Math.round(container.clientWidth));
            const height = Math.max(1, Math.round(container.clientHeight));
            const ratio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
            const pixelWidth = Math.round(width * ratio);
            const pixelHeight = Math.round(height * ratio);
            if (canvas.width === pixelWidth && canvas.height === pixelHeight && cssWidth === width) return;
            cssWidth = width;
            cssHeight = height;
            canvas.width = pixelWidth;
            canvas.height = pixelHeight;
            context.setTransform(ratio, 0, 0, ratio, 0, 0);
            requestFrame();
        }

        function positionTooltip(clientX, clientY) {
            if (!tooltip) return;
            const bounds = container.getBoundingClientRect();
            const tooltipWidth = tooltip.offsetWidth;
            const tooltipHeight = tooltip.offsetHeight;
            tooltip.style.left = `${Math.min(Math.max(8, clientX - bounds.left + 12), Math.max(8, bounds.width - tooltipWidth - 8))}px`;
            tooltip.style.top = `${Math.min(Math.max(8, clientY - bounds.top + 12), Math.max(8, bounds.height - tooltipHeight - 8))}px`;
        }

        function findNearestNode(clientX, clientY) {
            const bounds = canvas.getBoundingClientRect();
            const pointX = clientX - bounds.left;
            const pointY = clientY - bounds.top;
            const view = getView();
            let nearest = -1;
            let nearestDistance = 22 * 22;
            for (let index = 0; index < nodeCount; index += 1) {
                const dx = view.x + baseX[index] * view.scale - pointX;
                const dy = view.y + baseY[index] * view.scale - pointY;
                const distance = dx * dx + dy * dy;
                if (distance < nearestDistance) {
                    nearest = index;
                    nearestDistance = distance;
                }
            }
            return nearest;
        }

        function linkedVillages(index) {
            const villages = [];
            for (let edgeIndex = 0; edgeIndex < edges.length && villages.length < 12; edgeIndex += 2) {
                const first = edges[edgeIndex];
                const second = edges[edgeIndex + 1];
                const linked = first === index ? second : (second === index ? first : -1);
                if (linked >= 0 && isVillage[linked]) villages.push(String(nodes[linked][0]));
            }
            return villages;
        }

        function selectNode(index, event) {
            if (index < 0) {
                selectedIndex = -1;
                if (tooltip) tooltip.hidden = true;
                requestFrame();
                return;
            }

            const wasSelected = selectedIndex === index;
            selectedIndex = index;
            const node = nodes[index];

            if (wasSelected && isVillage[index]) {
                window.open(`village_sites/${encodeURIComponent(node[0])}.html`, '_blank', 'noopener');
                return;
            }

            if (tooltip && tooltipLabel && tooltipKind) {
                tooltipLabel.textContent = String(node[0]);
                if (isVillage[index]) {
                    tooltipKind.textContent = 'Village · tap again to open';
                } else {
                    const villages = linkedVillages(index);
                    tooltipKind.textContent = villages.length ? `In: ${villages.join(', ')}` : 'Archive term';
                }
                tooltip.hidden = false;
                positionTooltip(event.clientX, event.clientY);
            }
            requestFrame();
        }

        function setZoomAt(nextZoom, clientX, clientY) {
            const bounds = canvas.getBoundingClientRect();
            const pointX = clientX - bounds.left;
            const pointY = clientY - bounds.top;
            const oldView = getView();
            const graphX = (pointX - oldView.x) / oldView.scale;
            const graphY = (pointY - oldView.y) / oldView.scale;
            zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
            const newView = getView();
            panX += pointX - (newView.x + graphX * newView.scale);
            panY += pointY - (newView.y + graphY * newView.scale);
            if (tooltip) tooltip.hidden = true;
            requestFrame();
        }

        function getPinchDetails() {
            const pointers = [...activePointers.values()].slice(0, 2);
            if (pointers.length < 2) return null;
            return {
                distance: Math.max(1, Math.hypot(pointers[1].x - pointers[0].x, pointers[1].y - pointers[0].y)),
                x: (pointers[0].x + pointers[1].x) / 2,
                y: (pointers[0].y + pointers[1].y) / 2
            };
        }

        canvas.addEventListener('pointerdown', event => {
            stopMotion();
            activePointers.set(event.pointerId, {
                x: event.clientX,
                y: event.clientY,
                startX: event.clientX,
                startY: event.clientY,
                lastTime: performance.now(),
                velocity: 0,
                horizontal: false,
                dragged: false
            });
            if (activePointers.size >= 2) {
                activePointers.forEach(pointer => { pointer.dragged = true; });
                pinchState = getPinchDetails();
                gestureActive = true;
                if (canvas.setPointerCapture) {
                    activePointers.forEach((pointer, pointerId) => {
                        try { canvas.setPointerCapture(pointerId); } catch (error) { /* The pointer may already be gone. */ }
                    });
                }
            }
            if (tooltip) tooltip.hidden = true;
        });

        canvas.addEventListener('pointermove', event => {
            const pointer = activePointers.get(event.pointerId);
            if (!pointer) return;
            const previousX = pointer.x;
            const previousY = pointer.y;
            pointer.x = event.clientX;
            pointer.y = event.clientY;

            if (activePointers.size >= 2) {
                event.preventDefault();
                const nextPinch = getPinchDetails();
                if (pinchState && nextPinch) {
                    panX += nextPinch.x - pinchState.x;
                    panY += nextPinch.y - pinchState.y;
                    setZoomAt(zoom * (nextPinch.distance / pinchState.distance), nextPinch.x, nextPinch.y);
                }
                pinchState = nextPinch;
                activePointers.forEach(activePointer => { activePointer.dragged = true; });
                return;
            }

            const totalX = event.clientX - pointer.startX;
            const totalY = event.clientY - pointer.startY;
            if (!pointer.horizontal && Math.hypot(totalX, totalY) > 6) {
                pointer.horizontal = event.pointerType === 'mouse' || Math.abs(totalX) > Math.abs(totalY);
                if (pointer.horizontal && canvas.setPointerCapture) {
                    try { canvas.setPointerCapture(event.pointerId); } catch (error) { /* The pointer may already be gone. */ }
                }
            }
            if (!pointer.horizontal) return;

            // A sideways drag turns the graph, the same as dragging the desktop one.
            pointer.dragged = true;
            gestureActive = true;
            event.preventDefault();
            const deltaX = event.clientX - previousX;
            const step = (deltaX / Math.max(1, cssWidth)) * Math.PI;
            angle += step;
            const now = performance.now();
            const elapsed = Math.max(1, now - pointer.lastTime);
            pointer.velocity = step / elapsed;
            pointer.lastTime = now;
            if (event.pointerType === 'mouse') panY += event.clientY - previousY;
            requestFrame();
        });

        canvas.addEventListener('pointerup', event => {
            const pointer = activePointers.get(event.pointerId);
            if (!pointer) return;
            const distance = Math.hypot(event.clientX - pointer.startX, event.clientY - pointer.startY);
            activePointers.delete(event.pointerId);
            if (activePointers.size < 2) pinchState = null;
            activePointers.forEach(activePointer => {
                activePointer.startX = activePointer.x;
                activePointer.startY = activePointer.y;
                activePointer.dragged = true;
            });

            if (activePointers.size === 0) {
                gestureActive = false;
                const speed = pointer.horizontal ? pointer.velocity : 0;
                if (!lowPower && !reducedMotion && Math.abs(speed) > 0.0004) {
                    const travel = Math.max(-1.4, Math.min(1.4, speed * GLIDE_DURATION * 0.5));
                    glide = { start: performance.now(), from: angle, distance: travel };
                }
                requestFrame();
            }

            if (!pointer.dragged && distance <= 7 && activePointers.size === 0) {
                selectNode(findNearestNode(event.clientX, event.clientY), event);
            }
        });

        canvas.addEventListener('pointercancel', event => {
            activePointers.delete(event.pointerId);
            if (activePointers.size < 2) pinchState = null;
            if (activePointers.size === 0) {
                gestureActive = false;
                requestFrame();
            }
        });
        canvas.addEventListener('contextmenu', event => event.preventDefault());

        canvas.addEventListener('wheel', event => {
            event.preventDefault();
            stopMotion();
            setZoomAt(zoom * Math.exp(-event.deltaY * 0.0015), event.clientX, event.clientY);
        }, { passive: false });

        if ('ResizeObserver' in window) {
            new ResizeObserver(resize).observe(container);
        } else {
            window.addEventListener('resize', resize);
        }

        // Resting state first, so the graph is correct even if the turn never runs.
        zoom = SETTLED_ZOOM;
        resize();
        project(0);
        render(false);
        loadingIndicator.style.display = 'none';

        function startIntro() {
            if (!ENABLE_INTRO_SPIN || reducedMotion || lowPower || intro) return;
            zoom = MIN_ZOOM;
            panX = 0;
            panY = 0;
            frameTimes = [];
            framesSeen = 0;
            intro = { start: performance.now() };
            requestFrame();
        }

        // Nothing animates until the graph is actually on screen, and nothing
        // keeps animating once it leaves.
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver(entries => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        startIntro();
                        observer.disconnect();
                    }
                }
            }, { threshold: 0.35 });
            observer.observe(container);
        } else {
            startIntro();
        }

        document.addEventListener('visibilitychange', () => {
            if (document.hidden && intro) finishIntro();
        });

        if (nodes[homeIndex]?.[0] !== homeNodeId) {
            console.warn('The expected graph home node was not found.');
        }
    }

    window.AfrinMobileGraph = { initMobileGraph };
})();
