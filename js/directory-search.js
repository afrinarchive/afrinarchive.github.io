(function (global) {
    'use strict';

    const APOSTROPHES = /['’‘ʼʹʻ′‛`´ʿ]/g;
    const DASHES = /[‐‑‒–—―_-]+/g;
    const ARABIC_MARKS = /[\u0640\u064B-\u065F\u0670\u06D6-\u06ED]/g;

    function canonical(value) {
        return String(value || '')
            .normalize('NFC')
            .toLocaleLowerCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    // This is a hidden fallback form used only for matching. Displayed names are
    // never changed, and exact original-spelling matches always rank above it.
    function fold(value) {
        return String(value || '')
            .normalize('NFKD')
            .toLocaleLowerCase()
            .replace(/\p{M}+/gu, '')
            .replace(ARABIC_MARKS, '')
            .replace(/[ٱإأآ]/g, 'ا')
            .replace(/[ؤ]/g, 'و')
            .replace(/[ئىيی]/g, 'ي')
            .replace(/[ک]/g, 'ك')
            .replace(/[ھہ]/g, 'ه')
            .replace(/ı/g, 'i')
            .replace(/æ/g, 'ae')
            .replace(/œ/g, 'oe')
            .replace(/[øö]/g, 'o')
            .replace(/ł/g, 'l')
            .replace(/[đð]/g, 'd')
            .replace(/þ/g, 'th')
            .replace(APOSTROPHES, '')
            .replace(DASHES, ' ')
            .replace(/[^\p{L}\p{N}]+/gu, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function prepare(value) {
        const raw = String(value || '');
        const normalized = canonical(raw);
        const folded = fold(raw);
        return {
            raw,
            canonical: normalized,
            folded,
            compact: folded.replace(/\s+/g, ''),
            tokens: folded ? folded.split(' ') : []
        };
    }

    function allowedDistance(length) {
        if (length < 3) return 0;
        if (length <= 5) return 1;
        if (length <= 8) return 2;
        if (length <= 12) return 3;
        return Math.max(3, Math.floor(length * 0.22));
    }

    function damerauLevenshtein(left, right, maximum) {
        if (left === right) return 0;
        if (!left.length) return right.length;
        if (!right.length) return left.length;
        if (Math.abs(left.length - right.length) > maximum) return maximum + 1;

        const rows = Array.from({ length: left.length + 1 }, () => new Array(right.length + 1));
        for (let i = 0; i <= left.length; i += 1) rows[i][0] = i;
        for (let j = 0; j <= right.length; j += 1) rows[0][j] = j;

        for (let i = 1; i <= left.length; i += 1) {
            let rowMinimum = maximum + 1;
            for (let j = 1; j <= right.length; j += 1) {
                const substitutionCost = left[i - 1] === right[j - 1] ? 0 : 1;
                let distance = Math.min(
                    rows[i - 1][j] + 1,
                    rows[i][j - 1] + 1,
                    rows[i - 1][j - 1] + substitutionCost
                );

                if (
                    i > 1 && j > 1 &&
                    left[i - 1] === right[j - 2] &&
                    left[i - 2] === right[j - 1]
                ) {
                    distance = Math.min(distance, rows[i - 2][j - 2] + 1);
                }

                rows[i][j] = distance;
                rowMinimum = Math.min(rowMinimum, distance);
            }
            if (rowMinimum > maximum) return maximum + 1;
        }

        return rows[left.length][right.length];
    }

    function tokenQuality(queryToken, candidateToken) {
        if (queryToken === candidateToken) return 1;
        if (!queryToken || !candidateToken) return 0;

        if (candidateToken.startsWith(queryToken)) {
            return queryToken.length === 1 ? 0.82 : 0.96;
        }
        if (queryToken.length >= 3 && candidateToken.includes(queryToken)) return 0.9;
        if (queryToken.length < 3) return 0;

        const maximum = allowedDistance(Math.max(queryToken.length, candidateToken.length));
        const distance = damerauLevenshtein(queryToken, candidateToken, maximum);
        if (distance > maximum) return 0;

        const similarity = 1 - (distance / Math.max(queryToken.length, candidateToken.length));
        const minimumSimilarity = queryToken.length <= 4 ? 0.74 : queryToken.length <= 7 ? 0.7 : 0.68;
        return similarity >= minimumSimilarity ? 0.7 + (similarity * 0.25) : 0;
    }

    function valueQuality(query, candidate) {
        if (!candidate.folded) return 0;
        if (query.canonical === candidate.canonical) return 1;
        if (query.folded === candidate.folded) return 0.995;
        if (query.compact && query.compact === candidate.compact) return 0.985;

        if (candidate.folded.startsWith(query.folded)) return query.folded.length === 1 ? 0.82 : 0.97;
        if (query.folded.length >= 2 && candidate.folded.includes(query.folded)) return 0.94;
        if (query.compact.length >= 3 && candidate.compact.includes(query.compact)) return 0.91;

        const tokenScores = query.tokens.map(queryToken => {
            let best = 0;
            candidate.tokens.forEach(candidateToken => {
                best = Math.max(best, tokenQuality(queryToken, candidateToken));
            });
            return best;
        });

        if (tokenScores.length && tokenScores.every(Boolean)) {
            const average = tokenScores.reduce((sum, score) => sum + score, 0) / tokenScores.length;
            return average * (query.tokens.length === 1 ? 0.93 : 0.92);
        }

        if (query.compact.length >= 5 && candidate.compact.length >= 5) {
            const maximum = allowedDistance(Math.max(query.compact.length, candidate.compact.length));
            const distance = damerauLevenshtein(query.compact, candidate.compact, maximum);
            if (distance <= maximum) {
                const similarity = 1 - (distance / Math.max(query.compact.length, candidate.compact.length));
                if (similarity >= 0.74) return similarity * 0.86;
            }
        }

        return 0;
    }

    function fieldValues(item, field) {
        const value = typeof field.get === 'function' ? field.get(item) : item[field.key];
        if (Array.isArray(value)) return value.filter(valueItem => valueItem !== null && valueItem !== undefined && valueItem !== '');
        return value === null || value === undefined || value === '' ? [] : [value];
    }

    class SearchIndex {
        constructor(items, options) {
            this.fields = (options && options.fields ? options.fields : []).map(field => ({
                key: field.key,
                get: field.get,
                label: field.label || field.key,
                weight: Number(field.weight) || 0
            }));
            this.setItems(items || []);
        }

        setItems(items) {
            this.records = items.map((item, order) => ({
                item,
                order,
                values: this.fields.flatMap(field => fieldValues(item, field).map(value => ({
                    field,
                    prepared: prepare(value)
                })))
            }));
        }

        search(query, options) {
            const preparedQuery = prepare(query);
            if (!preparedQuery.folded) return [];
            const limit = options && Number.isFinite(options.limit) ? options.limit : Infinity;
            const results = [];

            this.records.forEach(record => {
                let best = null;

                record.values.forEach(value => {
                    const quality = valueQuality(preparedQuery, value.prepared);
                    if (!quality) return;
                    const score = (quality * 100) + value.field.weight;
                    if (!best || score > best.score) {
                        best = {
                            item: record.item,
                            score,
                            quality,
                            matchType: value.field.label,
                            matchText: value.prepared.raw,
                            query: String(query),
                            order: record.order
                        };
                    }
                });

                if (!best && preparedQuery.tokens.length > 1) {
                    const tokenMatches = preparedQuery.tokens.map(queryToken => {
                        let strongest = null;
                        record.values.forEach(value => {
                            value.prepared.tokens.forEach(candidateToken => {
                                const quality = tokenQuality(queryToken, candidateToken);
                                const score = (quality * 100) + value.field.weight;
                                if (quality && (!strongest || score > strongest.score)) {
                                    strongest = { quality, score, value };
                                }
                            });
                        });
                        return strongest;
                    });

                    if (tokenMatches.every(Boolean)) {
                        const quality = tokenMatches.reduce((sum, match) => sum + match.quality, 0) / tokenMatches.length;
                        const fieldWeight = tokenMatches.reduce((sum, match) => sum + match.value.field.weight, 0) / tokenMatches.length;
                        const strongest = tokenMatches.slice().sort((a, b) => b.score - a.score)[0];
                        best = {
                            item: record.item,
                            score: (quality * 86) + fieldWeight,
                            quality: quality * 0.86,
                            matchType: 'Multiple fields',
                            matchText: strongest.value.prepared.raw,
                            query: String(query),
                            order: record.order
                        };
                    }
                }

                if (best) results.push(best);
            });

            results.sort((left, right) =>
                right.score - left.score ||
                String(left.item.name || '').localeCompare(String(right.item.name || '')) ||
                left.order - right.order
            );
            return results.slice(0, limit);
        }
    }

    global.AfrinDirectorySearch = Object.freeze({
        SearchIndex,
        canonical,
        fold,
        prepare
    });
})(globalThis);
