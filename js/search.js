// js/search.js

const AfrinArchiveSearch = {
    isReady: false,
    villageData: [],
    edgeSearchMap: new Map(),

    /**
     * Initializes the search module by fetching and processing the graph data.
     * @param {string} pathToGraphData - The relative path to 'graph-data.json' from the HTML file.
     * @returns {Promise<void>} A promise that resolves when the data is ready.
     */
    async init(pathToGraphData) {
        if (this.isReady) return;

        try {
            const graph = await (await fetch(pathToGraphData)).json();

            // Prepare village data for searching
            this.villageData = graph.nodes.filter(node => node.type === 'file').map(node => ({
                name: node.label,
                id: node.id,
                filename: node.id + '.html'
            }));

            // Prepare edge data for searching related content
            graph.edges.forEach(edge => {
                const village = this.villageData.find(v => v.id === edge.from);
                if (village) {
                    const key = edge.to.toLowerCase();
                    if (!this.edgeSearchMap.has(key)) {
                        this.edgeSearchMap.set(key, []);
                    }
                    this.edgeSearchMap.get(key).push(village);
                }
            });

            this.isReady = true;
            console.log("Search module initialized successfully.");
        } catch (error) {
            console.error("Failed to initialize search module:", error);
        }
    },

    /**
     * Performs a fuzzy search on villages and related content.
     * @param {string} query - The search term.
     * @returns {Array<Object>} A sorted array of result objects.
     */
    search(query) {
        if (!this.isReady || !query) return [];

        const lowerCaseQuery = query.toLowerCase();
        const results = new Map();
        const FUZZY_THRESHOLD = lowerCaseQuery.length > 4 ? 2 : 1;

        const addOrUpdateResult = (village, score, matchInfo) => {
            const existing = results.get(village.id);
            if (!existing || score > existing.score) {
                results.set(village.id, { score, ...matchInfo });
            }
        };

        // Search village names (highest priority)
        this.villageData.forEach(village => {
            const lowerCaseName = village.name.toLowerCase();
            if (lowerCaseName.startsWith(lowerCaseQuery)) {
                addOrUpdateResult(village, 100, { village, matchType: 'Village Name', matchText: village.name, query: lowerCaseQuery });
            } else if (lowerCaseName.includes(lowerCaseQuery)) {
                addOrUpdateResult(village, 90, { village, matchType: 'Village Name', matchText: village.name, query: lowerCaseQuery });
            } else {
                const nameParts = lowerCaseName.split(/\s+/);
                for (const part of nameParts) {
                    const distance = this._levenshtein(part, lowerCaseQuery);
                    if (distance <= FUZZY_THRESHOLD) {
                        const score = 50 - (distance * 10);
                        addOrUpdateResult(village, score, { village, matchType: 'Village Name (similar)', matchText: village.name, query: part });
                        break;
                    }
                }
            }
        });

        // Search related content (lower priority)
        this.edgeSearchMap.forEach((villages, edgeText) => {
            if (edgeText.includes(lowerCaseQuery)) {
                villages.forEach(village => {
                    addOrUpdateResult(village, 25, { village, matchType: 'Related Content', matchText: edgeText, query: lowerCaseQuery });
                });
            }
        });

        return Array.from(results.values()).sort((a, b) => b.score - a.score);
    },

    /**
     * Calculates Levenshtein distance for fuzzy matching. (Internal helper)
     */
    _levenshtein(s1, s2) {
        if (s1.length < s2.length) { return this._levenshtein(s2, s1); }
        if (s2.length === 0) { return s1.length; }
        let previousRow = Array.from({ length: s2.length + 1 }, (_, i) => i);
        for (let i = 0; i < s1.length; i++) {
            let currentRow = [i + 1];
            for (let j = 0; j < s2.length; j++) {
                let insertions = previousRow[j + 1] + 1;
                let deletions = currentRow[j] + 1;
                let substitutions = previousRow[j] + (s1[i] !== s2[j]);
                currentRow.push(Math.min(insertions, deletions, substitutions));
            }
            previousRow = currentRow;
        }
        return previousRow[previousRow.length - 1];
    }
};