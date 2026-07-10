'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
require('../js/directory-search.js');
const VillageSearch = require('../js/search.js');

const records = [
    {
        name: "Abû Ke'bê Şerqî",
        alt: ["Abu Ka'b Eastern", 'أبو كعب شرقي'],
        nahiya: 'Cindires'
    },
    {
        name: 'Şêx Ebdulqadir',
        alt: ['Sheikh Abdul Qader'],
        villages: ['Kanî Gewrkê']
    }
];

const index = new AfrinDirectorySearch.SearchIndex(records, {
    fields: [
        { key: 'name', label: 'Name', weight: 100 },
        { key: 'alt', label: 'Alias', weight: 94 },
        { key: 'villages', label: 'Village', weight: 66 },
        { key: 'nahiya', label: 'Nahiya', weight: 56 }
    ]
});

function firstName(query) {
    const result = index.search(query, { limit: 1 })[0];
    return result && result.item.name;
}

assert.equal(firstName("Abû Ke'bê Şerqî"), "Abû Ke'bê Şerqî");
assert.equal(firstName('Abu Kebe Serqi'), "Abû Ke'bê Şerqî");
assert.equal(firstName('Abu Kebe Sherqi'), "Abû Ke'bê Şerqî");
assert.equal(firstName('Serqi Kebe Abu'), "Abû Ke'bê Şerqî");
assert.equal(firstName('AbuKebeSerqi'), "Abû Ke'bê Şerqî");
assert.equal(firstName('أبو كعب شرقي'), "Abû Ke'bê Şerqî");
assert.equal(firstName('Shex Ebdulqader'), 'Şêx Ebdulqadir');
assert.equal(firstName('Kani Gewrke'), 'Şêx Ebdulqadir');

const exactKurdish = index.search("Abû Ke'bê Şerqî", { limit: 1 })[0];
const simplifiedLatin = index.search('Abu Kebe Serqi', { limit: 1 })[0];
assert.ok(exactKurdish.score > simplifiedLatin.score);

const workspace = path.resolve(__dirname, '..');
const villageHtml = fs.readFileSync(path.join(workspace, 'village_site_files', '00_village_names.html'), 'utf8');
const inlineScriptPattern = /<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi;
for (const [scriptNumber, match] of Array.from(villageHtml.matchAll(inlineScriptPattern)).entries()) {
    if (match[1].trim()) assert.doesNotThrow(() => new Function(match[1]), `Village inline script ${scriptNumber + 1} does not compile`);
}
const nahiyaMatch = villageHtml.match(/const nahiyas = (\{[\s\S]*?\n\s*\});\s*\n\s*const alphabeticalContainer/);
assert.ok(nahiyaMatch, 'Village directory data could not be read');
const nahiyas = JSON.parse(nahiyaMatch[1]);
const villages = Object.values(nahiyas).flatMap(nahiya => nahiya.all_villages_detailed || []);
const villageIndex = new AfrinDirectorySearch.SearchIndex(villages, {
    fields: [
        { key: 'name', label: 'Village Name', weight: 100 },
        { key: 'alt', label: 'Alternative Name', weight: 94 },
        { key: 'nahiya', label: 'Nahiya', weight: 58 }
    ]
});
assert.equal(villageIndex.search('Abu Kebe Serqi', { limit: 1 })[0].item.name, "Abû Ke'bê Şerqî");
assert.equal(villageIndex.search('Abu Kebe Sherqi', { limit: 1 })[0].item.name, "Abû Ke'bê Şerqî");
VillageSearch.init(villages);
assert.equal(VillageSearch.search('Abu Kebe Serqi')[0].village.name, "Abû Ke'bê Şerqî");

const shrineHtml = fs.readFileSync(path.join(workspace, 'shrines-directory', 'shrines-directory.html'), 'utf8');
for (const [scriptNumber, match] of Array.from(shrineHtml.matchAll(inlineScriptPattern)).entries()) {
    if (match[1].trim()) assert.doesNotThrow(() => new Function(match[1]), `Shrine inline script ${scriptNumber + 1} does not compile`);
}
const shrineMatch = shrineHtml.match(/const shrines = (\[[^\n]+\]);/);
assert.ok(shrineMatch, 'Shrine directory data could not be read');
const shrines = JSON.parse(shrineMatch[1]);
const shrineIndex = new AfrinDirectorySearch.SearchIndex(shrines, {
    fields: [
        { key: 'name', label: 'Shrine Name', weight: 100 },
        { key: 'aliases', label: 'Alternative Name', weight: 94 },
        { key: 'villages', label: 'Village', weight: 66 },
        { key: 'nahiyas', label: 'Nahiya', weight: 56 }
    ]
});
assert.equal(shrineIndex.search('Sheikh Barakat', { limit: 1 })[0].item.name, 'Şêx Berekat');
assert.ok(shrineIndex.search('Kani Gewrke').some(result => result.item.villages.includes('Kanî Gewrkê')));

const benchmarkQueries = ['Abu Kebe Serqi', 'Abu Kebe Sherqi', 'Serqi Kebe Abu', 'Cindires'];
const benchmarkStarted = performance.now();
for (let iteration = 0; iteration < 25; iteration += 1) {
    benchmarkQueries.forEach(query => villageIndex.search(query));
}
const averageSearchMilliseconds = (performance.now() - benchmarkStarted) / (25 * benchmarkQueries.length);
assert.ok(averageSearchMilliseconds < 50, `Average village search took ${averageSearchMilliseconds.toFixed(2)} ms`);

console.log(`Directory search tests passed. Average village search: ${averageSearchMilliseconds.toFixed(2)} ms.`);
