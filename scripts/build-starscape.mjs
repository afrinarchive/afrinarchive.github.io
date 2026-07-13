import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SOURCE_PATH = path.join(ROOT, 'village_site_files', 'graph-data.json');
const OUTPUT_PATH = path.join(ROOT, 'landing', 'starscape-data.json');
const HOME_NODE_ID = 'Efr\u00een';
const TWO_PI = Math.PI * 2;

function hashString(value) {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
}

function seededNumber(value, salt) {
    let state = hashString(`${salt}:${value}`);
    state += 0x6D2B79F5;
    let result = state;
    result = Math.imul(result ^ (result >>> 15), result | 1);
    result ^= result + Math.imul(result ^ (result >>> 7), result | 61);
    return ((result ^ (result >>> 14)) >>> 0) / 4294967296;
}

function seededDirection(value, salt) {
    const z = seededNumber(value, `${salt}:z`) * 2 - 1;
    const angle = seededNumber(value, `${salt}:angle`) * TWO_PI;
    const radius = Math.sqrt(Math.max(0, 1 - z * z));
    return {
        x: Math.cos(angle) * radius,
        y: z,
        z: Math.sin(angle) * radius
    };
}

function buildNodePositions(graph) {
    const nodeById = new Map(graph.nodes.map(node => [node.id, node]));
    const fileNodes = graph.nodes.filter(node => node.type === 'file');
    const conceptNodes = graph.nodes.filter(node => node.type !== 'file');
    const fileNeighbours = new Map();

    for (const node of fileNodes) {
        if (node.id === HOME_NODE_ID) {
            node.position = { x: 0, y: 0, z: 0 };
            continue;
        }

        const direction = seededDirection(node.id, 'village');
        const distance = 260 + Math.pow(seededNumber(node.id, 'distance'), 0.62) * 760;
        node.position = {
            x: direction.x * distance,
            y: direction.y * distance * 0.78,
            z: direction.z * distance
        };
    }

    for (const edge of graph.edges) {
        const fromNode = nodeById.get(edge.from);
        const toNode = nodeById.get(edge.to);
        if (!fromNode || !toNode) continue;

        if (fromNode.type === 'file' && toNode.type !== 'file') {
            if (!fileNeighbours.has(toNode.id)) fileNeighbours.set(toNode.id, []);
            fileNeighbours.get(toNode.id).push(fromNode);
        } else if (toNode.type === 'file' && fromNode.type !== 'file') {
            if (!fileNeighbours.has(fromNode.id)) fileNeighbours.set(fromNode.id, []);
            fileNeighbours.get(fromNode.id).push(toNode);
        }
    }

    for (const node of conceptNodes) {
        const neighbours = fileNeighbours.get(node.id) || [];
        const direction = seededDirection(node.id, 'tag');

        if (neighbours.length > 0) {
            const centre = neighbours.reduce((total, neighbour) => {
                total.x += neighbour.position.x;
                total.y += neighbour.position.y;
                total.z += neighbour.position.z;
                return total;
            }, { x: 0, y: 0, z: 0 });
            centre.x /= neighbours.length;
            centre.y /= neighbours.length;
            centre.z /= neighbours.length;

            const spread = 34 + 116 / Math.sqrt(neighbours.length);
            const distance = spread * (0.45 + seededNumber(node.id, 'tag-distance'));
            node.position = {
                x: centre.x + direction.x * distance,
                y: centre.y + direction.y * distance,
                z: centre.z + direction.z * distance
            };
        } else {
            const distance = 860 + seededNumber(node.id, 'outer-distance') * 360;
            node.position = {
                x: direction.x * distance,
                y: direction.y * distance * 0.78,
                z: direction.z * distance
            };
        }
    }
}

const graph = JSON.parse(fs.readFileSync(SOURCE_PATH, 'utf8'));
buildNodePositions(graph);

const indexById = new Map(graph.nodes.map((node, index) => [node.id, index]));
const homeIndex = indexById.get(HOME_NODE_ID);
if (homeIndex === undefined) throw new Error('The home node is missing from graph-data.json.');

const compact = {
    h: homeIndex,
    n: graph.nodes.map(node => [
        node.id,
        node.type === 'file' ? 1 : 0,
        Math.round(node.position.x),
        Math.round(node.position.y),
        Math.round(node.position.z)
    ]),
    e: graph.edges.flatMap(edge => {
        const fromIndex = indexById.get(edge.from);
        const toIndex = indexById.get(edge.to);
        if (fromIndex === undefined || toIndex === undefined) return [];
        return [fromIndex, toIndex];
    })
};

fs.writeFileSync(OUTPUT_PATH, JSON.stringify(compact));
console.log(`Built ${path.relative(ROOT, OUTPUT_PATH)} with ${compact.n.length} nodes and ${compact.e.length / 2} edges.`);
