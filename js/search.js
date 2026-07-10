// Village-directory search adapter. The shared matching and ranking logic lives
// in directory-search.js so villages and shrines behave consistently.

const AfrinArchiveSearch = {
    isReady: false,
    villageData: [],
    nameIndex: null,
    relatedEntries: [],

    init(villages, pathToGraphData) {
        this.villageData = (villages || []).map(village => ({
            ...village,
            id: village.id || String(village.filename || '').replace(/\.html$/i, '')
        }));

        this.nameIndex = new AfrinDirectorySearch.SearchIndex(this.villageData, {
            fields: [
                { key: 'name', label: 'Village Name', weight: 100 },
                { key: 'alt', label: 'Alternative Name', weight: 94 },
                { key: 'nahiya', label: 'Nahiya', weight: 58 }
            ]
        });

        this.isReady = true;

        // Names and aliases are searchable immediately. Related page content is
        // added in the background instead of delaying the directory search box.
        if (pathToGraphData) this._loadRelatedContent(pathToGraphData);
    },

    async _loadRelatedContent(pathToGraphData) {
        try {
            const graph = await (await fetch(pathToGraphData)).json();
            const villagesById = new Map(this.villageData.map(village => [village.id, village]));
            const relatedByText = new Map();

            graph.edges.forEach(edge => {
                const village = villagesById.get(edge.from);
                if (!village || !edge.to) return;

                const folded = AfrinDirectorySearch.fold(edge.to);
                if (!folded) return;
                if (!relatedByText.has(folded)) {
                    relatedByText.set(folded, { text: edge.to, folded, villages: new Map() });
                }
                relatedByText.get(folded).villages.set(village.id, village);
            });

            this.relatedEntries = Array.from(relatedByText.values());
        } catch (error) {
            console.warn('Related-content search could not be loaded:', error);
        }
    },

    search(query) {
        if (!this.isReady || !query) return [];

        const results = new Map();
        this.nameIndex.search(query).forEach(match => {
            results.set(match.item.id, {
                village: match.item,
                score: match.score,
                matchType: match.matchType,
                matchText: match.matchText,
                query: match.query
            });
        });

        const foldedQuery = AfrinDirectorySearch.fold(query);
        if (foldedQuery.length >= 2) {
            this.relatedEntries.forEach(entry => {
                if (!entry.folded.includes(foldedQuery)) return;
                entry.villages.forEach(village => {
                    if (!results.has(village.id)) {
                        results.set(village.id, {
                            village,
                            score: 25,
                            matchType: 'Related Content',
                            matchText: entry.text,
                            query
                        });
                    }
                });
            });
        }

        return Array.from(results.values()).sort((left, right) =>
            right.score - left.score || left.village.name.localeCompare(right.village.name)
        );
    }
};

if (typeof module !== 'undefined' && module.exports) module.exports = AfrinArchiveSearch;
