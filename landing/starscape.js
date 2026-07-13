import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const TWO_PI = Math.PI * 2;

function makeDotTexture() {
    const textureCanvas = document.createElement('canvas');
    textureCanvas.width = 64;
    textureCanvas.height = 64;
    const context = textureCanvas.getContext('2d');
    context.clearRect(0, 0, 64, 64);
    context.fillStyle = '#ffffff';
    context.beginPath();
    context.arc(32, 32, 27, 0, TWO_PI);
    context.fill();
    return new THREE.CanvasTexture(textureCanvas);
}

function makeRingTexture() {
    const textureCanvas = document.createElement('canvas');
    textureCanvas.width = 64;
    textureCanvas.height = 64;
    const context = textureCanvas.getContext('2d');
    context.clearRect(0, 0, 64, 64);
    context.strokeStyle = '#ffffff';
    context.lineWidth = 4;
    context.beginPath();
    context.arc(32, 32, 25, 0, TWO_PI);
    context.stroke();
    return new THREE.CanvasTexture(textureCanvas);
}

function createPointCloud(nodes, options, dotTexture) {
    const positions = new Float32Array(nodes.length * 3);
    for (let index = 0; index < nodes.length; index += 1) {
        const position = nodes[index].position;
        positions[index * 3] = position.x;
        positions[index * 3 + 1] = position.y;
        positions[index * 3 + 2] = position.z;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.computeBoundingSphere();

    const material = new THREE.PointsMaterial({
        color: options.color,
        size: options.size,
        map: dotTexture,
        alphaTest: 0.2,
        transparent: true,
        opacity: options.opacity,
        sizeAttenuation: true
    });

    const pointCloud = new THREE.Points(geometry, material);
    pointCloud.userData.nodes = nodes;
    pointCloud.renderOrder = options.renderOrder;
    return pointCloud;
}

function createConnections(edgeIndexes, nodes, isMobile) {
    const edgeCount = edgeIndexes.length / 2;
    const positions = new Float32Array(edgeCount * 6);

    for (let index = 0; index < edgeCount; index += 1) {
        const from = nodes[edgeIndexes[index * 2]].position;
        const to = nodes[edgeIndexes[index * 2 + 1]].position;
        const offset = index * 6;
        positions[offset] = from.x;
        positions[offset + 1] = from.y;
        positions[offset + 2] = from.z;
        positions[offset + 3] = to.x;
        positions[offset + 4] = to.y;
        positions[offset + 5] = to.z;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.computeBoundingSphere();

    const material = new THREE.LineBasicMaterial({
        color: 0xa8c7b1,
        transparent: true,
        opacity: isMobile ? 0.075 : 0.1,
        depthWrite: false
    });

    return new THREE.LineSegments(geometry, material);
}

export async function initStarscape({
    container,
    canvas,
    loadingIndicator,
    graphUrl,
    homeNodeId
}) {
    if (!container || !canvas || !loadingIndicator) {
        throw new Error('The starscape container is incomplete.');
    }

    const isMobile = window.matchMedia('(max-width: 768px), (pointer: coarse)').matches;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const tooltip = document.getElementById('graph-tooltip');
    const tooltipLabel = document.getElementById('graph-tooltip-label');
    const tooltipKind = document.getElementById('graph-tooltip-kind');
    const labelCanvas = document.getElementById('graph-label-canvas');
    const labelContext = labelCanvas?.getContext('2d');
    if (!labelCanvas || !labelContext) throw new Error('The label canvas is missing.');

    loadingIndicator.textContent = 'Loading graph data...';
    const response = await fetch(graphUrl, { credentials: 'omit' });
    if (!response.ok) throw new Error(`Graph data request failed with ${response.status}.`);
    const graph = await response.json();
    if (!Array.isArray(graph.n) || !Array.isArray(graph.e) || !Number.isInteger(graph.h)) {
        throw new Error('The graph data has an unexpected format.');
    }

    const nodes = graph.n.map(node => ({
        id: node[0],
        label: node[0],
        type: node[1] === 1 ? 'file' : 'concept',
        position: { x: node[2], y: node[3], z: node[4] },
        degree: 0,
        pages: []
    }));
    for (let edgeIndex = 0; edgeIndex < graph.e.length; edgeIndex += 2) {
        const firstNode = nodes[graph.e[edgeIndex]];
        const secondNode = nodes[graph.e[edgeIndex + 1]];
        firstNode.degree += 1;
        secondNode.degree += 1;
        if (firstNode.type === 'file' && secondNode.type !== 'file') secondNode.pages.push(firstNode.label);
        if (secondNode.type === 'file' && firstNode.type !== 'file') firstNode.pages.push(secondNode.label);
    }
    for (const node of nodes) {
        if (node.pages.length > 1) node.pages = [...new Set(node.pages)].sort((first, second) => first.localeCompare(second));
    }
    const homeNode = nodes[graph.h];
    if (!homeNode || homeNode.id !== homeNodeId) {
        throw new Error('The starscape home node is missing.');
    }
    const conceptNodes = nodes
        .filter(node => node.type !== 'file')
        .sort((first, second) => second.degree - first.degree || first.label.localeCompare(second.label));
    const fileNodes = nodes
        .filter(node => node.type === 'file' && node.id !== homeNodeId)
        .sort((first, second) => second.degree - first.degree || first.label.localeCompare(second.label));

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);

    const camera = new THREE.PerspectiveCamera(52, 1, 1, 6000);
    camera.position.set(118, 170, 1022);

    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: !isMobile,
        alpha: false,
        powerPreference: 'high-performance'
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobile ? 1 : 1.5));

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = !reducedMotion;
    controls.dampingFactor = 0.065;
    controls.enablePan = true;
    controls.screenSpacePanning = true;
    controls.minDistance = 90;
    controls.maxDistance = 3900;
    controls.rotateSpeed = 0.58;
    controls.autoRotate = !reducedMotion;
    controls.autoRotateSpeed = 0.35;
    controls.zoomSpeed = 0.82;
    controls.panSpeed = 0.68;
    controls.target.set(0, 0, 0);
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.touches.ONE = THREE.TOUCH.ROTATE;
    controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
    controls.update();
    controls.saveState();

    const dotTexture = makeDotTexture();
    const conceptPoints = createPointCloud(conceptNodes, {
        color: 0x777777,
        size: isMobile ? 4.2 : 4.8,
        opacity: 0.82,
        renderOrder: 1
    }, dotTexture);
    const filePoints = createPointCloud(fileNodes, {
        color: 0x86efac,
        size: isMobile ? 9.5 : 11,
        opacity: 1,
        renderOrder: 2
    }, dotTexture);
    const homePoints = homeNode ? createPointCloud([homeNode], {
        color: 0xffcc00,
        size: isMobile ? 16 : 19,
        opacity: 1,
        renderOrder: 3
    }, dotTexture) : null;
    const connections = createConnections(graph.e, nodes, isMobile);

    scene.add(connections, conceptPoints, filePoints);
    if (homePoints) scene.add(homePoints);

    const ringTexture = makeRingTexture();
    const highlight = new THREE.Sprite(new THREE.SpriteMaterial({
        color: 0xffffff,
        map: ringTexture,
        transparent: true,
        depthTest: false,
        depthWrite: false
    }));
    highlight.visible = false;
    highlight.renderOrder = 10;
    scene.add(highlight);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const viewProjection = new THREE.Matrix4();
    const labelPixelRatio = Math.min(window.devicePixelRatio || 1, isMobile ? 1 : 1.25);
    let width = 1;
    let height = 1;
    let renderFrame = 0;
    let labelFrame = 0;
    let labelsReady = false;
    let forceLabelDraw = false;
    let lastLabelDraw = 0;
    let isOrbiting = false;
    let pointerStart = null;
    let lastMouseEvent = null;
    let hoverFrame = 0;

    function projectLabel(node, verticalOffset) {
        const matrix = viewProjection.elements;
        const { x, y, z } = node.position;
        const clipX = matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12];
        const clipY = matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13];
        const clipZ = matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14];
        const clipW = matrix[3] * x + matrix[7] * y + matrix[11] * z + matrix[15];
        if (clipW <= 0 || clipZ < -clipW || clipZ > clipW) return null;

        const xPosition = (clipX / clipW * 0.5 + 0.5) * width;
        const yPosition = (-clipY / clipW * 0.5 + 0.5) * height - verticalOffset;
        if (xPosition < -100 || xPosition > width + 100 || yPosition < -20 || yPosition > height + 20) {
            return null;
        }
        return {
            node,
            x: xPosition,
            y: yPosition,
            depthScale: Math.min(1.4, Math.max(0.18, 520 / clipW))
        };
    }

    function reserveLabel(label, fontSize, occupiedCells) {
        const approximateWidth = Math.min(260, Math.max(24, label.node.label.length * fontSize * 0.56));
        const cellSize = 18;
        const leftCell = Math.floor((label.x - approximateWidth / 2 - 3) / cellSize);
        const rightCell = Math.floor((label.x + approximateWidth / 2 + 3) / cellSize);
        const topCell = Math.floor((label.y - fontSize - 4) / cellSize);
        const bottomCell = Math.floor((label.y + 3) / cellSize);

        for (let row = topCell; row <= bottomCell; row += 1) {
            for (let column = leftCell; column <= rightCell; column += 1) {
                if (occupiedCells.has(`${column}:${row}`)) return false;
            }
        }
        for (let row = topCell; row <= bottomCell; row += 1) {
            for (let column = leftCell; column <= rightCell; column += 1) {
                occupiedCells.add(`${column}:${row}`);
            }
        }
        return true;
    }

    function collectLabels(group, limit, fontSize, verticalOffset, occupiedCells) {
        const accepted = [];
        const candidateCount = Math.min(group.length, limit);
        for (let index = 0; index < candidateCount; index += 1) {
            const label = projectLabel(group[index], verticalOffset);
            if (label && reserveLabel(label, fontSize, occupiedCells)) accepted.push(label);
        }
        return accepted;
    }

    function paintLabels(labels, font, color) {
        labelContext.font = font;
        labelContext.fillStyle = color;
        labelContext.strokeStyle = 'rgba(0, 0, 0, 0.9)';
        labelContext.lineWidth = 2.5;
        labelContext.textAlign = 'center';
        labelContext.textBaseline = 'bottom';
        for (const label of labels) {
            labelContext.strokeText(label.node.label, label.x, label.y);
            labelContext.fillText(label.node.label, label.x, label.y);
        }
    }

    function paintScaleLabels(group, limit, font, verticalOffset, color) {
        labelContext.font = font;
        labelContext.fillStyle = color;
        labelContext.textAlign = 'center';
        labelContext.textBaseline = 'bottom';
        const candidateCount = Math.min(group.length, limit);

        for (let index = 0; index < candidateCount; index += 1) {
            const label = projectLabel(group[index], verticalOffset);
            if (label) labelContext.fillText(label.node.label, label.x, label.y);
        }
    }

    function drawLabels() {
        viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
        labelContext.setTransform(labelPixelRatio, 0, 0, labelPixelRatio, 0, 0);
        labelContext.clearRect(0, 0, width, height);

        const occupiedCells = new Set();
        const homeFontSize = isMobile ? 12 : 14;
        const fileFontSize = isMobile ? 10 : 11;
        const conceptFontSize = 9;
        const homeLabels = collectLabels([homeNode], 1, homeFontSize, isMobile ? 12 : 14, occupiedCells);
        const zoomRatio = Math.max(0.35, 1560 / camera.position.distanceTo(controls.target));
        const labelScale = Math.pow(zoomRatio, 1.65);
        const fileLimit = Math.min(
            fileNodes.length,
            Math.max(isMobile ? 250 : fileNodes.length, Math.round((isMobile ? 250 : fileNodes.length) * labelScale))
        );
        const conceptLimit = Math.min(
            conceptNodes.length,
            Math.max(isMobile ? 120 : 250, Math.round((isMobile ? 120 : 250) * labelScale))
        );
        const conceptLabels = collectLabels(
            conceptNodes,
            conceptLimit,
            conceptFontSize,
            isMobile ? 4 : 5,
            occupiedCells
        );
        const fileLabels = collectLabels(fileNodes, fileLimit, fileFontSize, isMobile ? 8 : 9, occupiedCells);

        paintScaleLabels(
            conceptNodes,
            5000,
            `${isMobile ? 6 : 7}px Inter, "Noto Sans", sans-serif`,
            isMobile ? 3 : 4,
            'rgba(205, 205, 205, 0.52)'
        );
        paintScaleLabels(
            fileNodes,
            fileNodes.length,
            `500 ${isMobile ? 7 : 8}px Inter, "Noto Sans", sans-serif`,
            isMobile ? 6 : 7,
            'rgba(166, 245, 190, 0.76)'
        );
        paintLabels(conceptLabels, `${conceptFontSize}px Inter, "Noto Sans", sans-serif`, '#bdbdbd');
        paintLabels(fileLabels, `600 ${fileFontSize}px Inter, "Noto Sans", sans-serif`, '#d6fbe0');
        paintLabels(homeLabels, `700 ${homeFontSize}px Inter, "Noto Sans", sans-serif`, '#ffcc00');
    }

    function scheduleLabelDraw(force = false) {
        if (!labelsReady) return;
        forceLabelDraw ||= force;
        if (labelFrame) return;

        labelFrame = window.requestAnimationFrame(timestamp => {
            labelFrame = 0;
            if (!forceLabelDraw && timestamp - lastLabelDraw < (isMobile ? 120 : 75)) {
                scheduleLabelDraw();
                return;
            }
            forceLabelDraw = false;
            lastLabelDraw = timestamp;
            drawLabels();
        });
    }

    function render() {
        renderer.render(scene, camera);
        scheduleLabelDraw();
    }

    function animateUntilSettled() {
        renderFrame = 0;
        const changed = controls.update();
        render();
        if (changed || controls.autoRotate) scheduleRender();
    }

    function scheduleRender() {
        if (!renderFrame) renderFrame = window.requestAnimationFrame(animateUntilSettled);
    }

    function resize() {
        const nextWidth = Math.max(1, container.clientWidth);
        const nextHeight = Math.max(1, container.clientHeight);
        if (nextWidth === width && nextHeight === height) return;
        width = nextWidth;
        height = nextHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
        labelCanvas.width = Math.max(1, Math.round(width * labelPixelRatio));
        labelCanvas.height = Math.max(1, Math.round(height * labelPixelRatio));
        scheduleLabelDraw(true);
        scheduleRender();
    }

    function pickNode(event) {
        const bounds = canvas.getBoundingClientRect();
        pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
        pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
        raycaster.setFromCamera(pointer, camera);
        raycaster.params.Points.threshold = Math.min(
            24,
            Math.max(5, camera.position.distanceTo(controls.target) * 0.008)
        );

        const targets = homePoints
            ? [homePoints, filePoints, conceptPoints]
            : [filePoints, conceptPoints];
        const hit = raycaster.intersectObjects(targets, false)[0];
        if (!hit) return null;
        return hit.object.userData.nodes[hit.index] || null;
    }

    function positionTooltip(event) {
        if (!tooltip) return;
        const bounds = container.getBoundingClientRect();
        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;
        const left = Math.min(
            Math.max(8, event.clientX - bounds.left + 12),
            Math.max(8, bounds.width - tooltipWidth - 8)
        );
        const top = Math.min(
            Math.max(8, event.clientY - bounds.top + 12),
            Math.max(8, bounds.height - tooltipHeight - 8)
        );
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
    }

    function showNode(node, event) {
        if (!node) {
            highlight.visible = false;
            if (tooltip) tooltip.hidden = true;
            canvas.style.cursor = '';
            scheduleRender();
            return;
        }

        highlight.position.set(node.position.x, node.position.y, node.position.z);
        const size = node.id === homeNodeId ? 34 : (node.type === 'file' ? 26 : 18);
        highlight.scale.set(size, size, 1);
        highlight.material.color.set(node.type === 'file' ? 0x86efac : 0xffffff);
        highlight.visible = true;

        if (tooltip && tooltipLabel && tooltipKind) {
            tooltipLabel.textContent = node.label;
            if (node.type === 'file') {
                tooltipKind.textContent = 'Village · click to open';
            } else {
                const visiblePages = node.pages.slice(0, 12);
                const remainingCount = node.pages.length - visiblePages.length;
                tooltipKind.textContent = `In: ${visiblePages.join(', ')}${remainingCount > 0 ? ` · +${remainingCount} more` : ''}`;
            }
            tooltip.hidden = false;
            positionTooltip(event);
        }

        canvas.style.cursor = node.type === 'file' ? 'pointer' : '';
        scheduleRender();
    }

    function inspectMousePosition() {
        hoverFrame = 0;
        if (!lastMouseEvent || pointerStart) return;
        showNode(pickNode(lastMouseEvent), lastMouseEvent);
    }

    canvas.addEventListener('pointermove', event => {
        if (event.pointerType !== 'mouse') return;
        lastMouseEvent = event;
        if (!hoverFrame) hoverFrame = window.requestAnimationFrame(inspectMousePosition);
    });

    canvas.addEventListener('pointerleave', () => {
        lastMouseEvent = null;
        if (!pointerStart) showNode(null);
    });

    canvas.addEventListener('pointerdown', event => {
        pointerStart = { id: event.pointerId, x: event.clientX, y: event.clientY };
        if (tooltip) tooltip.hidden = true;
    });

    canvas.addEventListener('pointerup', event => {
        if (!pointerStart || pointerStart.id !== event.pointerId) return;
        const distance = Math.hypot(
            event.clientX - pointerStart.x,
            event.clientY - pointerStart.y
        );
        pointerStart = null;

        if (distance <= 7) {
            const node = pickNode(event);
            showNode(node, event);
            if (node && node.type === 'file') {
                const filename = `${encodeURIComponent(node.id)}.html`;
                window.open(`village_sites/${filename}`, '_blank', 'noopener');
            }
        }
    });

    canvas.addEventListener('pointercancel', () => {
        pointerStart = null;
    });
    canvas.addEventListener('contextmenu', event => event.preventDefault());

    controls.addEventListener('start', () => {
        isOrbiting = true;
        container.classList.add('is-orbiting');
        canvas.style.cursor = 'grabbing';
        if (tooltip) tooltip.hidden = true;
        scheduleRender();
    });
    controls.addEventListener('change', scheduleRender);
    controls.addEventListener('end', () => {
        isOrbiting = false;
        container.classList.remove('is-orbiting');
        canvas.style.cursor = '';
        scheduleLabelDraw(true);
        scheduleRender();
    });

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();
    render();
    loadingIndicator.style.display = 'none';

    const enableLabels = () => {
        labelsReady = true;
        scheduleLabelDraw(true);
    };
    if ('requestIdleCallback' in window) {
        window.requestIdleCallback(enableLabels, { timeout: 250 });
    } else {
        window.setTimeout(enableLabels, 0);
    }
    document.fonts?.ready.then(() => scheduleLabelDraw(true));

    canvas.addEventListener('webglcontextlost', event => {
        event.preventDefault();
        loadingIndicator.textContent = 'The 3D view paused. Reload the page to restore it.';
        loadingIndicator.style.display = 'block';
    });
}
