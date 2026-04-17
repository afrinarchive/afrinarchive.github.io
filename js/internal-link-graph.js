(function () {
    const OVERLAY_ID = "term-graph-overlay";
    const STYLE_ID = "term-graph-styles";
    const DATA_KEY = "INTERNAL_LINK_GRAPH_INDEX";

    function normalizeTerm(value) {
        return String(value || "")
            .normalize("NFKC")
            .toLowerCase()
            .replace(/[‘’`´]/g, "'")
            .replace(/[‐‑‒–—―]/g, "-")
            .replace(/\s+/g, " ")
            .trim();
    }

    function getCurrentVillageName() {
        const path = window.location.pathname || "";
        const filename = decodeURIComponent(path.split("/").pop() || "");
        return filename.replace(/\.html$/i, "");
    }

    function getCanvasContext() {
        if (!getCanvasContext.ctx) {
            const canvas = document.createElement("canvas");
            getCanvasContext.ctx = canvas.getContext("2d");
        }
        return getCanvasContext.ctx;
    }

    function measureText(text, font) {
        const ctx = getCanvasContext();
        ctx.font = font;
        return ctx.measureText(text).width;
    }

    function wrapLabel(text, options) {
        const { font, maxWidth, maxLines } = options;
        const words = String(text || "").split(/\s+/).filter(Boolean);
        if (!words.length) {
            return [String(text || "")];
        }

        const lines = [];
        let current = "";

        for (const word of words) {
            const candidate = current ? `${current} ${word}` : word;
            if (!current || measureText(candidate, font) <= maxWidth) {
                current = candidate;
                continue;
            }

            lines.push(current);
            current = word;

            if (lines.length === maxLines - 1) {
                break;
            }
        }

        if (lines.length < maxLines && current) {
            lines.push(current);
        }

        const consumed = lines.join(" ").split(/\s+/).filter(Boolean).length;
        if (consumed < words.length && lines.length) {
            let lastLine = lines[lines.length - 1];
            while (lastLine.length > 1 && measureText(`${lastLine}...`, font) > maxWidth) {
                lastLine = lastLine.slice(0, -1);
            }
            lines[lines.length - 1] = `${lastLine}...`;
        }

        return lines;
    }

    function getPalette() {
        const root = getComputedStyle(document.documentElement);
        const isDark = document.documentElement.classList.contains("dark");
        return {
            overlay: isDark ? "rgba(7, 10, 14, 0.84)" : "rgba(15, 23, 42, 0.6)",
            panel: root.getPropertyValue("--card-bg-color").trim() || (isDark ? "#232323" : "#f8f4e7"),
            text: root.getPropertyValue("--text-color").trim() || (isDark ? "#f8fafc" : "#111827"),
            muted: root.getPropertyValue("--subtext-color").trim() || (isDark ? "#cbd5e1" : "#475569"),
            border: root.getPropertyValue("--border-color").trim() || (isDark ? "#666666" : "#111827"),
            centerFill: isDark ? "#234534" : "#e7d59d",
            centerText: isDark ? "#f8fafc" : "#17202a",
            nodeFill: isDark ? "#2d2d2d" : "#fffdf8",
            nodeText: root.getPropertyValue("--text-color").trim() || (isDark ? "#f8fafc" : "#111827"),
            edge: isDark ? "rgba(191, 219, 254, 0.72)" : "rgba(100, 116, 139, 0.52)",
            shadow: isDark ? "rgba(0, 0, 0, 0.36)" : "rgba(15, 23, 42, 0.18)"
        };
    }

    function ensureStyles() {
        if (document.getElementById(STYLE_ID)) {
            return;
        }

        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
            #${OVERLAY_ID} {
                position: fixed;
                inset: 0;
                display: none;
                align-items: center;
                justify-content: center;
                padding: 18px;
                z-index: 2000;
                background: var(--term-graph-overlay);
                backdrop-filter: blur(6px);
            }
            #${OVERLAY_ID}.open {
                display: flex;
            }
            #${OVERLAY_ID} .term-graph-panel {
                width: min(1320px, 100%);
                height: min(92vh, 960px);
                display: flex;
                flex-direction: column;
                border: 1px solid var(--term-graph-border);
                border-radius: 20px;
                background: var(--term-graph-panel);
                color: var(--term-graph-text);
                box-shadow: 0 22px 70px rgba(0, 0, 0, 0.28);
                overflow: hidden;
            }
            #${OVERLAY_ID} .term-graph-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
                padding: 16px 20px 14px;
                border-bottom: 1px solid var(--term-graph-border);
            }
            #${OVERLAY_ID} .term-graph-title {
                margin: 0;
                font-size: 1.28rem;
                font-weight: 700;
                line-height: 1.2;
            }
            #${OVERLAY_ID} .term-graph-subtitle {
                margin: 6px 0 0;
                color: var(--term-graph-muted);
                font-size: 0.94rem;
            }
            #${OVERLAY_ID} .term-graph-close {
                border: 1px solid var(--term-graph-border);
                border-radius: 999px;
                padding: 8px 14px;
                background: transparent;
                color: var(--term-graph-text);
                cursor: pointer;
                font: inherit;
            }
            #${OVERLAY_ID} .term-graph-close:hover {
                background: rgba(148, 163, 184, 0.12);
            }
            #${OVERLAY_ID} .term-graph-body {
                min-height: 0;
                flex: 1;
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                gap: 16px;
                padding: 14px 16px 16px;
            }
            #${OVERLAY_ID} .term-graph-stage {
                min-width: 0;
                min-height: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #${OVERLAY_ID} .term-graph-canvas {
                width: 100%;
                max-width: 100%;
                max-height: 100%;
                aspect-ratio: 1 / 1;
                border: 1px solid var(--term-graph-border);
                border-radius: 16px;
                overflow: hidden;
                background:
                    radial-gradient(circle at top, rgba(148, 163, 184, 0.10), transparent 32%),
                    linear-gradient(180deg, rgba(148, 163, 184, 0.06), rgba(148, 163, 184, 0.02));
            }
            #${OVERLAY_ID} .term-graph-side {
                min-width: 0;
                min-height: 0;
                display: flex;
                flex-direction: column;
                border: 1px solid var(--term-graph-border);
                border-radius: 16px;
                overflow: hidden;
                background: rgba(148, 163, 184, 0.05);
            }
            #${OVERLAY_ID} .term-graph-side-header {
                padding: 14px 16px 12px;
                border-bottom: 1px solid var(--term-graph-border);
            }
            #${OVERLAY_ID} .term-graph-side-title {
                margin: 0;
                font-size: 1rem;
                font-weight: 700;
                line-height: 1.2;
            }
            #${OVERLAY_ID} .term-graph-side-meta {
                margin: 6px 0 0;
                color: var(--term-graph-muted);
                font-size: 0.92rem;
            }
            #${OVERLAY_ID} .term-graph-list {
                flex: 1;
                min-height: 0;
                overflow-y: auto;
                padding: 8px 10px 10px;
            }
            #${OVERLAY_ID} .term-graph-link {
                display: block;
                padding: 10px 12px;
                border-radius: 12px;
                color: var(--term-graph-text);
                text-decoration: none;
                line-height: 1.3;
            }
            #${OVERLAY_ID} .term-graph-link:hover {
                background: rgba(148, 163, 184, 0.14);
            }
            #${OVERLAY_ID} .term-graph-empty {
                padding: 14px 12px;
                color: var(--term-graph-muted);
                font-size: 0.94rem;
            }
            #${OVERLAY_ID} .term-graph-svg {
                display: block;
                width: 100%;
                height: 100%;
                touch-action: none;
            }
            .internal-link.term-graph-bound:hover {
                text-decoration: underline;
                text-underline-offset: 0.14em;
            }
            .internal-link.term-graph-no-results {
                color: var(--text-color);
            }
            @media (max-width: 900px) {
                #${OVERLAY_ID} {
                    padding: 10px;
                }
                #${OVERLAY_ID} .term-graph-panel {
                    width: 100%;
                    height: min(94vh, 94dvh);
                    border-radius: 16px;
                }
                #${OVERLAY_ID} .term-graph-header {
                    padding: 14px 14px 12px;
                }
                #${OVERLAY_ID} .term-graph-title {
                    font-size: 1.1rem;
                }
                #${OVERLAY_ID} .term-graph-subtitle {
                    font-size: 0.9rem;
                }
                #${OVERLAY_ID} .term-graph-body {
                    display: flex;
                    flex-direction: column;
                    padding: 12px;
                    gap: 12px;
                    overflow: hidden;
                }
                #${OVERLAY_ID} .term-graph-stage {
                    flex: 0 0 auto;
                    align-items: center;
                    justify-content: center;
                }
                #${OVERLAY_ID} .term-graph-canvas {
                    width: min(100%, 360px);
                    max-height: min(34vh, 360px);
                    margin: 0 auto;
                }
                #${OVERLAY_ID} .term-graph-side {
                    flex: 1 1 auto;
                    min-height: 0;
                }
                #${OVERLAY_ID} .term-graph-side-header {
                    padding: 12px 14px 10px;
                }
                #${OVERLAY_ID} .term-graph-list {
                    min-height: 0;
                    padding: 6px 8px 8px;
                    -webkit-overflow-scrolling: touch;
                }
                #${OVERLAY_ID} .term-graph-link {
                    padding: 12px;
                }
            }
            @media (max-width: 560px) {
                #${OVERLAY_ID} {
                    padding: 0;
                }
                #${OVERLAY_ID} .term-graph-panel {
                    height: 100dvh;
                    max-height: none;
                    border-radius: 0;
                    border-left: 0;
                    border-right: 0;
                    border-bottom: 0;
                }
                #${OVERLAY_ID} .term-graph-header {
                    gap: 10px;
                }
                #${OVERLAY_ID} .term-graph-close {
                    padding: 7px 12px;
                }
                #${OVERLAY_ID} .term-graph-body {
                    padding: 10px;
                    gap: 10px;
                }
                #${OVERLAY_ID} .term-graph-canvas {
                    width: min(100%, 280px);
                    max-height: min(26vh, 280px);
                    aspect-ratio: 1 / 1;
                }
                #${OVERLAY_ID} .term-graph-side-header {
                    padding: 10px 12px 8px;
                }
                #${OVERLAY_ID} .term-graph-side-title {
                    font-size: 0.95rem;
                }
                #${OVERLAY_ID} .term-graph-side-meta {
                    font-size: 0.88rem;
                }
                #${OVERLAY_ID} .term-graph-list {
                    padding: 4px 6px 8px;
                }
            }
        `;

        document.head.appendChild(style);
    }

    function ensureOverlay() {
        let overlay = document.getElementById(OVERLAY_ID);
        if (overlay) {
            return overlay;
        }

        overlay = document.createElement("div");
        overlay.id = OVERLAY_ID;
        overlay.innerHTML = `
            <div class="term-graph-panel" role="dialog" aria-modal="true" aria-labelledby="term-graph-title">
                <div class="term-graph-header">
                    <div>
                        <h2 class="term-graph-title" id="term-graph-title"></h2>
                        <p class="term-graph-subtitle"></p>
                    </div>
                    <button type="button" class="term-graph-close">Close</button>
                </div>
                <div class="term-graph-body">
                    <div class="term-graph-stage">
                        <div class="term-graph-canvas"></div>
                    </div>
                    <div class="term-graph-side">
                        <div class="term-graph-side-header">
                            <h3 class="term-graph-side-title">Linked Villages</h3>
                            <p class="term-graph-side-meta"></p>
                        </div>
                        <div class="term-graph-list"></div>
                    </div>
                </div>
            </div>
        `;

        const close = () => {
            overlay.classList.remove("open");
            document.body.style.overflow = "";
        };

        overlay.querySelector(".term-graph-close").addEventListener("click", close);
        overlay.addEventListener("click", (event) => {
            if (event.target === overlay) {
                close();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && overlay.classList.contains("open")) {
                close();
            }
        });

        overlay.closeGraph = close;
        document.body.appendChild(overlay);
        return overlay;
    }

    function buildNodeBox(label, isCenter) {
        const font = isCenter ? "700 20px Inter, sans-serif" : "600 14px Inter, sans-serif";
        const maxWidth = isCenter ? 260 : 132;
        const maxLines = isCenter ? 3 : 2;
        const lineHeight = isCenter ? 24 : 17;
        const paddingX = isCenter ? 26 : 14;
        const paddingY = isCenter ? 20 : 11;
        const lines = wrapLabel(label, { font, maxWidth, maxLines });
        const textWidth = Math.max(...lines.map((line) => measureText(line, font)), isCenter ? 80 : 50);
        return {
            label,
            lines,
            width: Math.ceil(textWidth + (paddingX * 2)),
            height: Math.ceil((lines.length * lineHeight) + (paddingY * 2)),
            lineHeight,
            fontSize: isCenter ? 20 : 14,
            fontWeight: isCenter ? 700 : 600,
            isCenter
        };
    }

    function appendMultiLineText(selection, node, color) {
        const startY = (-((node.lines.length - 1) * node.lineHeight) / 2) + 5;
        const text = selection.append("text")
            .attr("text-anchor", "middle")
            .attr("fill", color)
            .attr("font-size", node.fontSize)
            .attr("font-weight", node.fontWeight)
            .attr("font-family", "Inter, sans-serif");

        node.lines.forEach((line, index) => {
            text.append("tspan")
                .attr("x", 0)
                .attr("dy", index === 0 ? startY : node.lineHeight)
                .text(line);
        });
    }

    function computeBounds(nodes) {
        const xs = [];
        const ys = [];
        nodes.forEach((node) => {
            const halfWidth = node.width / 2;
            const halfHeight = node.height / 2;
            xs.push(node.x - halfWidth, node.x + halfWidth);
            ys.push(node.y - halfHeight, node.y + halfHeight);
        });
        return {
            minX: Math.min(...xs),
            maxX: Math.max(...xs),
            minY: Math.min(...ys),
            maxY: Math.max(...ys)
        };
    }

    function fitGraph(svgSelection, zoomBehavior, width, height, nodes) {
        const bounds = computeBounds(nodes);
        const graphWidth = Math.max(200, bounds.maxX - bounds.minX);
        const graphHeight = Math.max(200, bounds.maxY - bounds.minY);
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        const padding = 56;
        const scale = Math.min(
            (width - (padding * 2)) / graphWidth,
            (height - (padding * 2)) / graphHeight
        );

        const transform = window.d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(Math.max(0.15, Math.min(scale, 1.4)))
            .translate(-centerX, -centerY);

        svgSelection.call(zoomBehavior.transform, transform);
    }

    function renderEmptyState(canvas, palette, term) {
        canvas.innerHTML = `
            <svg class="term-graph-svg" viewBox="0 0 760 320" xmlns="http://www.w3.org/2000/svg">
                <rect x="1" y="1" width="758" height="318" rx="20" fill="${palette.nodeFill}" stroke="${palette.border}" />
                <text x="380" y="136" text-anchor="middle" fill="${palette.text}" font-size="28" font-weight="700" font-family="Inter, sans-serif">${term}</text>
                <text x="380" y="188" text-anchor="middle" fill="${palette.muted}" font-size="18" font-family="Inter, sans-serif">No other village pages are linked to this term yet.</text>
            </svg>
        `;
    }

    function renderVillageList(listElement, metaElement, villages) {
        const sortedVillages = [...villages].sort((a, b) => a.localeCompare(b));
        metaElement.textContent = sortedVillages.length === 1
            ? "1 village"
            : `${sortedVillages.length} villages`;

        if (!sortedVillages.length) {
            listElement.innerHTML = `<div class="term-graph-empty">No linked villages found.</div>`;
            return sortedVillages;
        }

        listElement.innerHTML = sortedVillages.map((village) => {
            const href = `${encodeURIComponent(village)}.html`;
            return `<a class="term-graph-link" href="${href}" target="_blank" rel="noopener noreferrer">${village}</a>`;
        }).join("");

        return sortedVillages;
    }

    function renderGraph(term, villages) {
        const overlay = ensureOverlay();
        const palette = getPalette();
        const title = overlay.querySelector(".term-graph-title");
        const subtitle = overlay.querySelector(".term-graph-subtitle");
        const canvas = overlay.querySelector(".term-graph-canvas");
        const list = overlay.querySelector(".term-graph-list");
        const sideMeta = overlay.querySelector(".term-graph-side-meta");

        overlay.style.setProperty("--term-graph-overlay", palette.overlay);
        overlay.style.setProperty("--term-graph-panel", palette.panel);
        overlay.style.setProperty("--term-graph-text", palette.text);
        overlay.style.setProperty("--term-graph-muted", palette.muted);
        overlay.style.setProperty("--term-graph-border", palette.border);

        title.textContent = term;
        subtitle.textContent = villages.length === 1
            ? "1 other village page mentions this term."
            : `${villages.length} other village pages mention this term.`;

        overlay.classList.add("open");
        document.body.style.overflow = "hidden";

        const sortedVillages = renderVillageList(list, sideMeta, villages);

        if (!sortedVillages.length) {
            renderEmptyState(canvas, palette, term);
            return;
        }

        canvas.innerHTML = `<svg class="term-graph-svg"></svg>`;

        requestAnimationFrame(() => {
            if (!window.d3) {
                renderEmptyState(canvas, palette, "D3 failed to load");
                return;
            }

            const svgElement = canvas.querySelector("svg");
            const width = Math.max(420, canvas.clientWidth);
            const height = Math.max(420, canvas.clientHeight);
            const centerNode = {
                id: "__center__",
                ...buildNodeBox(term, true),
                x: 0,
                y: 0,
                fx: 0,
                fy: 0
            };

            const outerNodes = sortedVillages.map((name, index) => {
                const angle = (Math.PI * 2 * index) / sortedVillages.length;
                const radius = 220 + ((index % 7) * 18);
                return {
                    id: name,
                    ...buildNodeBox(name, false),
                    x: Math.cos(angle) * radius,
                    y: Math.sin(angle) * radius
                };
            });

            const nodes = [centerNode, ...outerNodes];
            const links = outerNodes.map((node) => ({ source: centerNode.id, target: node.id }));

            const svg = window.d3.select(svgElement)
                .attr("viewBox", `0 0 ${width} ${height}`);

            svg.selectAll("*").remove();

            const defs = svg.append("defs");
            const filter = defs.append("filter")
                .attr("id", "term-graph-shadow")
                .attr("x", "-20%")
                .attr("y", "-20%")
                .attr("width", "140%")
                .attr("height", "140%");
            filter.append("feDropShadow")
                .attr("dx", 0)
                .attr("dy", 10)
                .attr("stdDeviation", 10)
                .attr("flood-color", palette.shadow);

            const viewport = svg.append("g");
            const edgeLayer = viewport.append("g");
            const nodeLayer = viewport.append("g");

            const zoom = window.d3.zoom()
                .scaleExtent([0.15, 5])
                .on("zoom", (event) => {
                    viewport.attr("transform", event.transform);
                });

            svg.call(zoom).on("dblclick.zoom", null);

            const linkSelection = edgeLayer.selectAll("line")
                .data(links)
                .join("line")
                .attr("stroke", palette.edge)
                .attr("stroke-width", 2.1)
                .attr("stroke-linecap", "round");

            const nodeSelection = nodeLayer.selectAll("g")
                .data(nodes)
                .join("g")
                .attr("cursor", (d) => d.isCenter ? "default" : "pointer")
                .on("click", function (event, d) {
                    if (d.isCenter) {
                        return;
                    }
                    event.stopPropagation();
                    window.open(`${encodeURIComponent(d.label)}.html`, "_blank");
                });

            nodeSelection.each(function (d) {
                const group = window.d3.select(this);
                if (d.isCenter) {
                    group.append("ellipse")
                        .attr("rx", d.width / 2)
                        .attr("ry", d.height / 2)
                        .attr("fill", palette.centerFill)
                        .attr("stroke", palette.border)
                        .attr("stroke-width", 2)
                        .attr("filter", "url(#term-graph-shadow)");
                    appendMultiLineText(group, d, palette.centerText);
                } else {
                    group.append("rect")
                        .attr("x", -d.width / 2)
                        .attr("y", -d.height / 2)
                        .attr("width", d.width)
                        .attr("height", d.height)
                        .attr("rx", 16)
                        .attr("fill", palette.nodeFill)
                        .attr("stroke", palette.border)
                        .attr("stroke-width", 1.5)
                        .attr("filter", "url(#term-graph-shadow)");
                    appendMultiLineText(group, d, palette.nodeText);
                }
            });

            const simulation = window.d3.forceSimulation(nodes)
                .force("link", window.d3.forceLink(links).id((d) => d.id).distance((d) => (
                    d.target.width > 170 ? 230 : 190
                )).strength(0.34))
                .force("charge", window.d3.forceManyBody().strength((d) => d.isCenter ? -90 : -320))
                .force("collision", window.d3.forceCollide().radius((d) => (
                    Math.sqrt((d.width * d.width) + (d.height * d.height)) / 2 + 18
                )).iterations(2))
                .force("x", window.d3.forceX(0).strength((d) => d.isCenter ? 0.16 : 0.03))
                .force("y", window.d3.forceY(0).strength((d) => d.isCenter ? 0.16 : 0.03))
                .stop();

            for (let i = 0; i < 320; i += 1) {
                simulation.tick();
            }

            nodeSelection.attr("transform", (d) => `translate(${d.x},${d.y})`);
            linkSelection
                .attr("x1", (d) => d.source.x)
                .attr("y1", (d) => d.source.y)
                .attr("x2", (d) => d.target.x)
                .attr("y2", (d) => d.target.y);

            fitGraph(svg, zoom, width, height, nodes);
        });
    }

    function bindLinks() {
        ensureStyles();
        ensureOverlay();

        const data = window[DATA_KEY] || {};
        const currentVillageKey = normalizeTerm(getCurrentVillageName());

        document.querySelectorAll(".internal-link").forEach((element) => {
            if (element.dataset.termGraphBound === "1") {
                return;
            }

            const rawTerm = element.textContent.trim();
            const key = normalizeTerm(rawTerm);
            const villages = (data[key] || []).filter((name) => normalizeTerm(name) !== currentVillageKey);

            element.dataset.termGraphBound = "1";
            element.classList.add("term-graph-bound");
            if (!villages.length) {
                element.classList.add("term-graph-no-results");
            }
            element.setAttribute("role", "button");
            element.setAttribute("tabindex", "0");

            const open = (event) => {
                event.preventDefault();
                event.stopPropagation();
                renderGraph(rawTerm, villages);
            };

            element.addEventListener("click", open);
            element.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    open(event);
                }
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindLinks);
    } else {
        bindLinks();
    }
})();
