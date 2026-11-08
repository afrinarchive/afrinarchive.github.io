'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const homepage = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const directory = fs.readFileSync(path.join(root, 'village_site_files/00_village_names.html'), 'utf8');
const nahiyas = JSON.parse(directory.match(/const nahiyas = (\{[\s\S]*?\n\s*\});\s*\n\s*const alphabeticalContainer/)[1]);
const villages = Object.values(nahiyas).flatMap(nahiya => nahiya.all_villages_detailed || []);

function environment(html, marker) {
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, { style: {}, value: 'village', innerHTML: '' });
        return elements.get(id);
    };
    const context = vm.createContext({
        document: {
            addEventListener() {},
            getElementById: element,
            querySelector: element,
            createElement() {
                return {
                    textContent: '',
                    get innerHTML() {
                        return String(this.textContent).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    }
                };
            }
        },
        window: { addEventListener() {} }
    });
    const script = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
        .map(match => match[1]).find(source => source.includes(marker));
    assert.ok(script);
    vm.runInContext(script, context);
    return { context, element };
}

function links(markup, className) {
    return [...markup.matchAll(new RegExp(`<a class="${className}"[^>]*>`, 'g'))].map(match => {
        const tag = match[0];
        assert.match(tag, /target="_blank"/);
        assert.match(tag, /rel="noopener"/);
        assert.doesNotMatch(tag, /onclick=/);
        return tag.match(/href="([^"]*)"/)[1]
            .replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
    });
}

for (const hydrated of [true, false]) {
    test(`homepage dropdown and full results preserve page addresses (${hydrated ? 'filtered' : 'all'} search)`, async () => {
        const { context, element } = environment(homepage, 'function setupGraph()');
        const fixtures = [
            ...villages.filter(village => village.filename.includes("'")).slice(0, 2)
                .map(village => ({ url: `/village_sites/${village.filename}`, meta: { title: village.name } })),
            { url: '/shrine_sites/Şêx Berekat.html', meta: { title: 'Şêx Berekat' } },
            { url: '/village_sites/أبو كعب.html', meta: { title: 'أبو كعب' } },
            { url: '/village_sites/test.html?name="quoted"&other=1', meta: { title: 'Test' } }
        ];
        context.fixtureResults = fixtures.map(data => ({ data: async () => data }));
        context.fixtureData = fixtures;
        context.hydrated = hydrated;
        vm.runInContext(`
            pagefind = {};
            getScopedSearch = async () => ({
                results: fixtureResults, resultCount: fixtureResults.length,
                scope: null, scopeLabel: '',
                hydratedResults: hydrated ? fixtureData.map(data => ({ data })) : null
            });
        `, context);

        await context.performDropdownSearch();
        await context.showSearchResultsPage();
        const expected = fixtures.map(data => data.url);
        assert.deepEqual(links(element('search-results').innerHTML, 'search-result-item'), expected);
        assert.deepEqual(links(element('search-results-page-list').innerHTML, 'search-result-card'), expected);
        assert.throws(() => new Function(`window.open('${fixtures[0].url}', '_blank')`), SyntaxError,
            'The apostrophe fixture must reproduce the original broken click handler.');
    });
}

test('village directory dropdown and full results link to every existing village page', () => {
    const { context, element } = environment(directory, 'function performSearch()');
    const orderedVillages = [...villages].sort((left, right) =>
        Number(right.filename.includes("'")) - Number(left.filename.includes("'")));
    context.AfrinArchiveSearch = {
        search: () => orderedVillages.map(village => ({ village, matchType: 'Village Name', matchText: village.name, query: village.name }))
    };
    context.performSearch();
    context.showSearchResultsPage();

    const expected = orderedVillages.map(village => `../village_sites/${encodeURIComponent(village.filename)}`);
    assert.deepEqual(links(element('search-results').innerHTML, 'search-result-item'), expected.slice(0, 8));
    assert.deepEqual(links(element('search-results-page-list').innerHTML, 'search-result-card'), expected);
    for (const href of expected) {
        assert.ok(fs.existsSync(path.resolve(root, 'village_site_files', decodeURIComponent(href))), href);
    }
});
