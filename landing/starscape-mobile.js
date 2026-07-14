(function () {
    'use strict';

    const BASE_WIDTH = 900;
    const BASE_HEIGHT = 700;
    const MIN_ZOOM = 1;
    const MAX_ZOOM = 4;

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
        const projectedX = new Float32Array(nodeCount);
        const projectedY = new Float32Array(nodeCount);
        const degree = new Uint16Array(nodeCount);
        let minX = Infinity;
        let maxX = -Infinity;
        let minY = Infinity;
        let maxY = -Infinity;

        for (let index = 0; index < nodeCount; index += 1) {
            const node = nodes[index];
            const x = Number(node[2]) * 0.82 + Number(node[4]) * 0.34;
            const y = Number(node[3]) * 0.86 - Number(node[4]) * 0.2;
            projectedX[index] = x;
            projectedY[index] = y;
            minX = Math.min(minX, x);
            maxX = Math.max(maxX, x);
            minY = Math.min(minY, y);
            maxY = Math.max(maxY, y);
        }

        for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 2) {
            degree[edges[edgeIndex]] += 1;
            degree[edges[edgeIndex + 1]] += 1;
        }

        const padding = 34;
        const scaleX = (BASE_WIDTH - padding * 2) / Math.max(1, maxX - minX);
        const scaleY = (BASE_HEIGHT - padding * 2) / Math.max(1, maxY - minY);
        const projectionScale = Math.min(scaleX, scaleY);
        const usedWidth = (maxX - minX) * projectionScale;
        const usedHeight = (maxY - minY) * projectionScale;
        const startX = (BASE_WIDTH - usedWidth) / 2;
        const startY = (BASE_HEIGHT - usedHeight) / 2;

        for (let index = 0; index < nodeCount; index += 1) {
            projectedX[index] = startX + (projectedX[index] - minX) * projectionScale;
            projectedY[index] = startY + (projectedY[index] - minY) * projectionScale;
        }

        const baseCanvas = document.createElement('canvas');
        baseCanvas.width = BASE_WIDTH;
        baseCanvas.height = BASE_HEIGHT;
        const baseContext = baseCanvas.getContext('2d', { alpha: false });
        baseContext.fillStyle = '#000000';
        baseContext.fillRect(0, 0, BASE_WIDTH, BASE_HEIGHT);

        baseContext.beginPath();
        for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 2) {
            const first = edges[edgeIndex];
            const second = edges[edgeIndex + 1];
            baseContext.moveTo(projectedX[first], projectedY[first]);
            baseContext.lineTo(projectedX[second], projectedY[second]);
        }
        baseContext.strokeStyle = 'rgba(168, 199, 177, 0.12)';
        baseContext.lineWidth = 0.7;
        baseContext.stroke();

        baseContext.fillStyle = '#777777';
        for (let index = 0; index < nodeCount; index += 1) {
            if (nodes[index][1] === 1 || index === graph.h) continue;
            baseContext.fillRect(projectedX[index] - 0.8, projectedY[index] - 0.8, 1.6, 1.6);
        }

        baseContext.fillStyle = '#86efac';
        for (let index = 0; index < nodeCount; index += 1) {
            if (nodes[index][1] !== 1 || index === graph.h) continue;
            const size = Math.min(4.5, 2.2 + degree[index] * 0.08);
            baseContext.fillRect(projectedX[index] - size / 2, projectedY[index] - size / 2, size, size);
        }

        baseContext.beginPath();
        baseContext.arc(projectedX[graph.h], projectedY[graph.h], 6, 0, Math.PI * 2);
        baseContext.fillStyle = '#ffcc00';
        baseContext.fill();

        const labelIndexes = Array.from({ length: nodeCount }, (_, index) => index)
            .filter(index => degree[index] > 0 && index !== graph.h)
            .sort((first, second) => degree[second] - degree[first])
            .slice(0, 26);
        labelIndexes.unshift(graph.h);
        baseContext.font = '600 11px system-ui, sans-serif';
        baseContext.textBaseline = 'middle';
        for (const index of labelIndexes) {
            const label = String(nodes[index][0]);
            const x = projectedX[index] + 7;
            const y = projectedY[index];
            baseContext.lineWidth = 3;
            baseContext.strokeStyle = '#000000';
            baseContext.strokeText(label, x, y);
            baseContext.fillStyle = index === graph.h ? '#ffcc00' : (nodes[index][1] === 1 ? '#d6fbe0' : '#c8c8c8');
            baseContext.fillText(label, x, y);
        }

        let zoom = 1;
        let panX = 0;
        let panY = 0;
        let selectedIndex = -1;
        const activePointers = new Map();
        let pinchState = null;
        let renderFrame = 0;

        function getView() {
            const fitScale = Math.min(canvas.width / BASE_WIDTH, canvas.height / BASE_HEIGHT);
            const scale = fitScale * zoom;
            const width = BASE_WIDTH * scale;
            const height = BASE_HEIGHT * scale;
            return {
                scale,
                x: (canvas.width - width) / 2 + panX,
                y: (canvas.height - height) / 2 + panY,
                width,
                height
            };
        }

        function renderNow() {
            renderFrame = 0;
            const view = getView();
            context.fillStyle = '#000000';
            context.fillRect(0, 0, canvas.width, canvas.height);
            context.imageSmoothingEnabled = true;
            context.drawImage(baseCanvas, view.x, view.y, view.width, view.height);

            if (selectedIndex >= 0) {
                const x = view.x + projectedX[selectedIndex] * view.scale;
                const y = view.y + projectedY[selectedIndex] * view.scale;
                context.beginPath();
                context.arc(x, y, 12, 0, Math.PI * 2);
                context.strokeStyle = '#ffffff';
                context.lineWidth = 2;
                context.stroke();
            }
        }

        function scheduleRender() {
            if (!renderFrame) renderFrame = window.requestAnimationFrame(renderNow);
        }

        function resize() {
            const width = Math.max(1, Math.round(container.clientWidth));
            const height = Math.max(1, Math.round(container.clientHeight));
            if (canvas.width === width && canvas.height === height) return;
            canvas.width = width;
            canvas.height = height;
            scheduleRender();
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
            const pointX = (clientX - bounds.left) * (canvas.width / Math.max(1, bounds.width));
            const pointY = (clientY - bounds.top) * (canvas.height / Math.max(1, bounds.height));
            const view = getView();
            const graphX = (pointX - view.x) / view.scale;
            const graphY = (pointY - view.y) / view.scale;
            const threshold = 18 / view.scale;
            const thresholdSquared = threshold * threshold;
            let nearest = -1;
            let nearestDistance = thresholdSquared;

            for (let index = 0; index < nodeCount; index += 1) {
                const dx = projectedX[index] - graphX;
                const dy = projectedY[index] - graphY;
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
                if (linked >= 0 && nodes[linked][1] === 1) villages.push(String(nodes[linked][0]));
            }
            return villages;
        }

        function selectNode(index, event) {
            if (index < 0) {
                selectedIndex = -1;
                if (tooltip) tooltip.hidden = true;
                scheduleRender();
                return;
            }

            const wasSelected = selectedIndex === index;
            selectedIndex = index;
            const node = nodes[index];
            const isVillage = node[1] === 1;

            if (wasSelected && isVillage) {
                window.open(`village_sites/${encodeURIComponent(node[0])}.html`, '_blank', 'noopener');
                return;
            }

            if (tooltip && tooltipLabel && tooltipKind) {
                tooltipLabel.textContent = String(node[0]);
                if (isVillage) {
                    tooltipKind.textContent = 'Village · tap again to open';
                } else {
                    const villages = linkedVillages(index);
                    tooltipKind.textContent = villages.length ? `In: ${villages.join(', ')}` : 'Archive term';
                }
                tooltip.hidden = false;
                positionTooltip(event.clientX, event.clientY);
            }
            scheduleRender();
        }

        function setZoom(nextZoom) {
            const clamped = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
            const change = clamped / zoom;
            panX *= change;
            panY *= change;
            zoom = clamped;
            if (tooltip) tooltip.hidden = true;
            scheduleRender();
        }

        function setZoomAt(nextZoom, clientX, clientY) {
            const bounds = canvas.getBoundingClientRect();
            const pointX = (clientX - bounds.left) * (canvas.width / Math.max(1, bounds.width));
            const pointY = (clientY - bounds.top) * (canvas.height / Math.max(1, bounds.height));
            const oldView = getView();
            const graphX = (pointX - oldView.x) / oldView.scale;
            const graphY = (pointY - oldView.y) / oldView.scale;
            zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
            const newView = getView();
            panX += pointX - (newView.x + graphX * newView.scale);
            panY += pointY - (newView.y + graphY * newView.scale);
            if (tooltip) tooltip.hidden = true;
            scheduleRender();
        }

        function isFullscreen() {
            return container.classList.contains('is-mobile-fullscreen');
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
            activePointers.set(event.pointerId, {
                x: event.clientX,
                y: event.clientY,
                startX: event.clientX,
                startY: event.clientY,
                horizontal: false,
                dragged: false
            });
            if (isFullscreen() && canvas.setPointerCapture) {
                try { canvas.setPointerCapture(event.pointerId); } catch (error) { /* The pointer may already be gone. */ }
            }
            if (activePointers.size >= 2 && isFullscreen()) {
                activePointers.forEach(pointer => { pointer.dragged = true; });
                pinchState = getPinchDetails();
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

            if (activePointers.size >= 2 && isFullscreen()) {
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
            if (isFullscreen()) {
                if (Math.hypot(totalX, totalY) > 6) pointer.dragged = true;
                event.preventDefault();
                panX += event.clientX - previousX;
                panY += event.clientY - previousY;
            } else {
                if (!pointer.horizontal && Math.hypot(totalX, totalY) > 6) {
                    pointer.horizontal = event.pointerType === 'mouse' || Math.abs(totalX) > Math.abs(totalY);
                }
                if (!pointer.horizontal) return;
                pointer.dragged = true;
                event.preventDefault();
                panX += event.clientX - previousX;
                if (event.pointerType === 'mouse') panY += event.clientY - previousY;
            }
            scheduleRender();
        });

        canvas.addEventListener('pointerup', event => {
            const pointer = activePointers.get(event.pointerId);
            if (!pointer) return;
            const distance = Math.hypot(event.clientX - pointer.startX, event.clientY - pointer.startY);
            activePointers.delete(event.pointerId);
            if (activePointers.size < 2) pinchState = null;
            if (!pointer.dragged && distance <= 7 && activePointers.size === 0) {
                selectNode(findNearestNode(event.clientX, event.clientY), event);
            }
        });

        canvas.addEventListener('pointercancel', event => {
            activePointers.delete(event.pointerId);
            if (activePointers.size < 2) pinchState = null;
        });
        canvas.addEventListener('contextmenu', event => event.preventDefault());

        container.querySelectorAll('.graph-mobile-control').forEach(button => {
            button.addEventListener('click', () => {
                const action = button.dataset.graphAction;
                if (action === 'zoom-in') setZoom(zoom * 1.35);
                if (action === 'zoom-out') setZoom(zoom / 1.35);
                if (action === 'reset') {
                    zoom = 1;
                    panX = 0;
                    panY = 0;
                    selectedIndex = -1;
                    if (tooltip) tooltip.hidden = true;
                    scheduleRender();
                }
                if (action === 'fullscreen') {
                    const open = !isFullscreen();
                    container.classList.toggle('is-mobile-fullscreen', open);
                    document.body.classList.toggle('graph-fullscreen-open', open);
                    canvas.style.touchAction = open ? 'none' : 'pan-y pinch-zoom';
                    button.textContent = open ? 'Close' : 'Full screen';
                    button.setAttribute('aria-label', open ? 'Close full screen graph' : 'Open graph full screen');
                    activePointers.clear();
                    pinchState = null;
                    if (tooltip) tooltip.hidden = true;
                    window.requestAnimationFrame(() => {
                        resize();
                        scheduleRender();
                    });
                }
            });
        });

        if ('ResizeObserver' in window) {
            const resizeObserver = new ResizeObserver(resize);
            resizeObserver.observe(container);
        } else {
            window.addEventListener('resize', resize);
        }
        resize();
        renderNow();
        loadingIndicator.style.display = 'none';

        if (nodes[graph.h]?.[0] !== homeNodeId) {
            console.warn('The expected graph home node was not found.');
        }
    }

    window.AfrinMobileGraph = { initMobileGraph };
})();
