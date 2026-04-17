const DEFAULT_CENTER = [36.65, 36.7];
const DEFAULT_ZOOM = 10;
const MAX_RESULTS_PER_KIND = 300;
const PHRASE_BOOST = 8;
const NAME_PREFIX_BOOST = 12;
const NAME_CONTAINS_BOOST = 7;
const VILLAGE_MATCH_BOOST = 4;
const SOURCE_MATCH_BOOST = 2;
const WILDCARD_MATCH_BOOST = 2.25;
const FUZZY_MATCH_BOOST = 1.75;
const MAP_COLORS = {
  village: "#0074d9",
  transcript: "#ffdc00",
  both: "#e7352b",
  allGreen: "#7fff00",
};

const dom = {
  searchInput: document.querySelector("#search-input"),
  searchButton: document.querySelector("#search-button"),
  syntaxButton: document.querySelector("#syntax-button"),
  closeSyntaxButton: document.querySelector("#close-syntax"),
  syntaxDialog: document.querySelector("#syntax-dialog"),
  themeToggle: document.querySelector("#theme-toggle"),
  themeToggleDarkIcon: document.querySelector("#theme-toggle-dark-icon"),
  themeToggleLightIcon: document.querySelector("#theme-toggle-light-icon"),
  themeColorMeta: document.querySelector('meta[name="theme-color"]'),
  statusLine: document.querySelector("#status-line"),
  villageCount: document.querySelector("#village-count"),
  transcriptCount: document.querySelector("#transcript-count"),
  villageResults: document.querySelector("#village-results"),
  transcriptResults: document.querySelector("#transcript-results"),
  previewContent: document.querySelector("#preview-content"),
};

const state = {
  rawData: null,
  searchEngine: null,
  villageResults: [],
  transcriptResults: [],
  selectedResultId: "",
  selectedVillage: "",
  map: null,
  legendControl: null,
  layerGroups: null,
  legendCheckboxes: {
    village: null,
    transcript: null,
    both: null,
    allGreen: null,
  },
  layerVisibility: {
    village: true,
    transcript: true,
    both: true,
  },
  allGreen: false,
};

function setupTheme() {
  const isDark =
    localStorage.getItem("color-theme") === "dark" ||
    (!("color-theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches);

  document.documentElement.classList.toggle("dark", isDark);
  dom.themeToggleLightIcon.classList.toggle("hidden", !isDark);
  dom.themeToggleDarkIcon.classList.toggle("hidden", isDark);
  dom.themeColorMeta?.setAttribute("content", isDark ? "#2d2d2d" : "#f7f5f3");
}

class SearchEngine {
  constructor(payload) {
    this.documents = payload.documents.map((doc) => this.#prepareDocument(doc));
    this.documentById = new Map(this.documents.map((doc) => [doc.id, doc]));
    this.docCount = this.documents.length;
    this.docFreqs = new Map();
    this.avgDocLength = 1;

    let totalLength = 0;
    for (const doc of this.documents) {
      totalLength += doc.docLength;
      for (const term of doc.termFreq.keys()) {
        this.docFreqs.set(term, (this.docFreqs.get(term) ?? 0) + 1);
      }
    }
    this.avgDocLength = totalLength / Math.max(this.documents.length, 1);
  }

  #prepareDocument(doc) {
    const searchableText = doc.searchText ?? doc.text;
    const boostedSearchText = [
      doc.name,
      doc.name,
      doc.name,
      doc.village,
      doc.village,
      doc.kind === "transcript" ? doc.village : "",
      doc.source ?? "",
      searchableText,
    ]
      .filter(Boolean)
      .join("\n");

    const normalizedSearchText = normalizeText(boostedSearchText);
    const rawTokens = tokenize(normalizedSearchText);
    const stemmedTokens = rawTokens.map(stemToken);
    const termFreq = new Map();
    for (const token of stemmedTokens) {
      termFreq.set(token, (termFreq.get(token) ?? 0) + 1);
    }

    return {
      ...doc,
      normalizedName: normalizeText(doc.name),
      normalizedVillage: normalizeText(doc.village),
      normalizedLinkedVillages: (doc.linkedVillages ?? [doc.village]).map((name) => normalizeText(name)),
      normalizedSource: normalizeText(doc.source ?? ""),
      normalizedText: normalizeText(doc.text),
      rawTokens,
      rawTokenSet: new Set(rawTokens),
      stemmedTokens,
      stemmedTokenSet: new Set(stemmedTokens),
      termFreq,
      docLength: stemmedTokens.length || 1,
      fragments: null,
    };
  }

  getDocument(id) {
    return this.documentById.get(id);
  }

  search(rawQuery) {
    const parsed = parseQuery(rawQuery);
    if (!parsed || !parsed.clauses.length || !parsed.positiveClauses.length) {
      return {
        parsed,
        villageResults: [],
        transcriptResults: [],
      };
    }

    const results = [];
    for (const doc of this.documents) {
      const evaluation = evaluateQueryForDocument(doc, parsed);
      if (!evaluation.matches) {
        continue;
      }

      let score = this.#scoreDocument(doc, parsed);
      score += evaluation.boost;
      score += this.#fieldBoost(doc, parsed);

      results.push({
        id: doc.id,
        kind: doc.kind,
        name: doc.name,
        village: doc.village,
        linkedVillages: doc.linkedVillages ?? [doc.village],
        url: doc.url,
        source: doc.source,
        lat: doc.lat,
        lon: doc.lon,
        score,
        clauseMatches: evaluation.clauseMatches,
        positiveTerms: parsed.highlightTerms,
      });
    }

    results.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));
    return {
      parsed,
      villageResults: results
        .filter((result) => result.kind === "village")
        .slice(0, MAX_RESULTS_PER_KIND),
      transcriptResults: results
        .filter((result) => result.kind === "transcript")
        .slice(0, MAX_RESULTS_PER_KIND),
    };
  }

  #scoreDocument(doc, parsed) {
    let score = 0;
    const uniqueTerms = new Set(parsed.positiveStemTerms);
    const k1 = 1.5;
    const b = 0.75;

    for (const term of uniqueTerms) {
      const tf = doc.termFreq.get(term) ?? 0;
      if (!tf) {
        continue;
      }

      const df = this.docFreqs.get(term) ?? 0;
      const idf = Math.log(1 + (this.docCount - df + 0.5) / (df + 0.5));
      const numerator = tf * (k1 + 1);
      const denominator = tf + k1 * (1 - b + b * (doc.docLength / this.avgDocLength));
      score += idf * (numerator / denominator);
    }

    return score;
  }

  #fieldBoost(doc, parsed) {
    let boost = 0;
    const normalizedFullQuery = parsed.normalizedFullQuery;

    if (normalizedFullQuery) {
      if (doc.normalizedName.startsWith(normalizedFullQuery)) {
        boost += NAME_PREFIX_BOOST;
      } else if (doc.normalizedName.includes(normalizedFullQuery)) {
        boost += NAME_CONTAINS_BOOST;
      }

      if (doc.normalizedLinkedVillages.includes(normalizedFullQuery) || doc.normalizedVillage === normalizedFullQuery) {
        boost += VILLAGE_MATCH_BOOST;
      } else if (
        doc.normalizedVillage.includes(normalizedFullQuery) ||
        doc.normalizedLinkedVillages.some((name) => name.includes(normalizedFullQuery))
      ) {
        boost += 2;
      }

      if (doc.normalizedSource && doc.normalizedSource.includes(normalizedFullQuery)) {
        boost += SOURCE_MATCH_BOOST;
      }
    }

    for (const token of parsed.highlightTerms) {
      if (!token) {
        continue;
      }
      if (doc.normalizedName.includes(token)) {
        boost += 1.4;
      }
      if (
        doc.normalizedVillage.includes(token) ||
        doc.normalizedLinkedVillages.some((name) => name.includes(token))
      ) {
        boost += 0.8;
      }
    }

    return boost;
  }
}

function normalizeText(text) {
  return text
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[â€™'`Â´]/g, "")
    .toLowerCase();
}

function tokenize(text) {
  return normalizeText(text).match(/[\p{L}\p{N}]+/gu) ?? [];
}

function stemToken(token) {
  if (!/^[a-z]+$/.test(token) || token.length < 3) {
    return token;
  }

  let stem = token;

  if (stem.endsWith("sses")) {
    stem = stem.slice(0, -2);
  } else if (stem.endsWith("ies") && stem.length > 4) {
    stem = `${stem.slice(0, -3)}y`;
  } else if (stem.endsWith("es") && /(ches|shes|sses|xes|zes|oes)$/.test(stem)) {
    stem = stem.slice(0, -2);
  } else if (stem.endsWith("s") && !stem.endsWith("ss") && !stem.endsWith("us") && !stem.endsWith("is")) {
    stem = stem.slice(0, -1);
  }

  if (stem.endsWith("ingly") && hasVowel(stem.slice(0, -5))) {
    stem = stem.slice(0, -5);
  } else if (stem.endsWith("edly") && hasVowel(stem.slice(0, -4))) {
    stem = stem.slice(0, -4);
  } else if (stem.endsWith("ing") && stem.length > 5 && hasVowel(stem.slice(0, -3))) {
    stem = stem.slice(0, -3);
  } else if (stem.endsWith("ed") && stem.length > 4 && hasVowel(stem.slice(0, -2))) {
    stem = stem.slice(0, -2);
  }

  if (stem.endsWith("ational")) {
    stem = `${stem.slice(0, -7)}ate`;
  } else if (stem.endsWith("tional")) {
    stem = `${stem.slice(0, -2)}`;
  } else if (stem.endsWith("ization")) {
    stem = `${stem.slice(0, -5)}e`;
  } else if (stem.endsWith("ation")) {
    stem = `${stem.slice(0, -5)}e`;
  } else if (stem.endsWith("ment") && stem.length > 6) {
    stem = stem.slice(0, -4);
  } else if (stem.endsWith("ness") && stem.length > 6) {
    stem = stem.slice(0, -4);
  } else if (stem.endsWith("less") && stem.length > 6) {
    stem = stem.slice(0, -4);
  } else if (stem.endsWith("ful") && stem.length > 5) {
    stem = stem.slice(0, -3);
  } else if (stem.endsWith("ly") && stem.length > 4) {
    stem = stem.slice(0, -2);
  } else if (stem.endsWith("er") && stem.length > 5) {
    stem = stem.slice(0, -2);
  }

  return stem || token;
}

function hasVowel(text) {
  return /[aeiouy]/.test(text);
}

function parseQuery(rawQuery) {
  const normalizedFullQuery = normalizeText(rawQuery).trim();
  const lexemes = [];
  const re = /"([^"]+)"(?:~(\d+))?|(\S+)/g;

  for (const match of rawQuery.matchAll(re)) {
    if (match[1]) {
      const phraseText = match[1].trim();
      const phraseTokens = tokenize(phraseText);
      if (!phraseTokens.length) {
        continue;
      }
      lexemes.push({
        type: "clause",
        clause: {
          kind: "phrase",
          text: phraseText,
          tokens: phraseTokens,
          stems: phraseTokens.map(stemToken),
          slop: Number.parseInt(match[2] ?? "0", 10),
        },
      });
      continue;
    }

    const token = match[3];
    const upper = token.toUpperCase();
    if (upper === "AND" || upper === "OR" || upper === "NOT") {
      lexemes.push({ type: "operator", value: upper });
      continue;
    }

    const normalized = normalizeText(token).trim();
    if (!normalized) {
      continue;
    }

    if (normalized.endsWith("*")) {
      const prefix = normalized.slice(0, -1);
      if (prefix) {
        lexemes.push({
          type: "clause",
          clause: {
            kind: "wildcard",
            text: token,
            prefix,
          },
        });
      }
      continue;
    }

    if (normalized.endsWith("~")) {
      const base = normalized.slice(0, -1);
      if (base) {
        lexemes.push({
          type: "clause",
          clause: {
            kind: "fuzzy",
            text: token,
            value: base,
            maxDistance: base.length > 4 ? 2 : 1,
          },
        });
      }
      continue;
    }

    lexemes.push({
      type: "clause",
      clause: {
        kind: "term",
        text: token,
        value: normalized,
        stem: stemToken(normalized),
      },
    });
  }

  const infix = [];
  let previousType = null;
  let previousOperator = null;
  for (const lexeme of lexemes) {
    if (
      (lexeme.type === "clause" || lexeme.value === "NOT") &&
      previousType === "clause"
    ) {
      infix.push({ type: "operator", value: "AND" });
    }

    infix.push(lexeme);
    previousType = lexeme.type;
    previousOperator = lexeme.type === "operator" ? lexeme.value : previousOperator;
  }

  const rpn = toRpn(infix);
  const clauses = infix
    .filter((item) => item.type === "clause")
    .map((item) => item.clause);
  const positiveClauses = [];
  const highlightTerms = [];
  const positiveStemTerms = [];

  for (let index = 0; index < infix.length; index += 1) {
    const item = infix[index];
    if (item.type !== "clause") {
      continue;
    }

    const negated = infix[index - 1]?.type === "operator" && infix[index - 1].value === "NOT";
    if (!negated) {
      positiveClauses.push(item.clause);
      if (item.clause.kind === "term") {
        highlightTerms.push(item.clause.value);
        positiveStemTerms.push(item.clause.stem);
      } else if (item.clause.kind === "phrase") {
        highlightTerms.push(...item.clause.tokens);
        positiveStemTerms.push(...item.clause.stems);
      } else if (item.clause.kind === "wildcard") {
        highlightTerms.push(item.clause.prefix);
      } else if (item.clause.kind === "fuzzy") {
        highlightTerms.push(item.clause.value);
      }
    }
  }

  return {
    rawQuery,
    normalizedFullQuery,
    clauses,
    positiveClauses,
    positiveStemTerms,
    highlightTerms: [...new Set(highlightTerms.filter(Boolean))],
    rpn,
  };
}

function toRpn(infix) {
  const output = [];
  const operators = [];
  const precedence = { OR: 1, AND: 2, NOT: 3 };
  const rightAssociative = new Set(["NOT"]);

  for (const item of infix) {
    if (item.type === "clause") {
      output.push(item);
      continue;
    }

    while (operators.length) {
      const last = operators[operators.length - 1];
      if (
        precedence[last.value] > precedence[item.value] ||
        (precedence[last.value] === precedence[item.value] && !rightAssociative.has(item.value))
      ) {
        output.push(operators.pop());
      } else {
        break;
      }
    }
    operators.push(item);
  }

  while (operators.length) {
    output.push(operators.pop());
  }

  return output;
}

function evaluateQueryForDocument(doc, parsed) {
  const clauseMatches = new Map();
  for (const clause of parsed.clauses) {
    if (!clauseMatches.has(clause)) {
      clauseMatches.set(clause, evaluateClause(doc, clause));
    }
  }

  const stack = [];
  for (const item of parsed.rpn) {
    if (item.type === "clause") {
      stack.push(clauseMatches.get(item.clause).matches);
      continue;
    }

    if (item.value === "NOT") {
      stack.push(!stack.pop());
      continue;
    }

    const right = stack.pop();
    const left = stack.pop();
    stack.push(item.value === "AND" ? left && right : left || right);
  }

  let boost = 0;
  for (const clause of parsed.positiveClauses) {
    boost += clauseMatches.get(clause)?.boost ?? 0;
  }

  return {
    matches: Boolean(stack.pop()),
    boost,
    clauseMatches,
  };
}

function evaluateClause(doc, clause) {
  if (clause.kind === "term") {
    return {
      matches: doc.stemmedTokenSet.has(clause.stem),
      boost: 0,
    };
  }

  if (clause.kind === "phrase") {
    const gap = findPhraseGap(doc.rawTokens, clause.tokens);
    const matches = gap !== Number.POSITIVE_INFINITY && gap <= clause.slop;
    return {
      matches,
      boost: matches
        ? clause.slop === 0
          ? PHRASE_BOOST
          : Math.max(2, PHRASE_BOOST - gap * 0.75)
        : 0,
    };
  }

  if (clause.kind === "wildcard") {
    for (const token of doc.rawTokenSet) {
      if (token.startsWith(clause.prefix)) {
        return { matches: true, boost: WILDCARD_MATCH_BOOST };
      }
    }
    return { matches: false, boost: 0 };
  }

  if (clause.kind === "fuzzy") {
    for (const token of doc.rawTokenSet) {
      if (Math.abs(token.length - clause.value.length) > clause.maxDistance) {
        continue;
      }
      if (levenshtein(token, clause.value) <= clause.maxDistance) {
        return { matches: true, boost: FUZZY_MATCH_BOOST };
      }
    }
    return { matches: false, boost: 0 };
  }

  return { matches: false, boost: 0 };
}

function findPhraseGap(tokens, phraseTokens) {
  if (!phraseTokens.length || phraseTokens.length > tokens.length) {
    return Number.POSITIVE_INFINITY;
  }

  let bestGap = Number.POSITIVE_INFINITY;
  for (let index = 0; index < tokens.length; index += 1) {
    if (tokens[index] !== phraseTokens[0]) {
      continue;
    }

    let previousIndex = index;
    let gap = 0;
    let matched = true;

    for (let phraseIndex = 1; phraseIndex < phraseTokens.length; phraseIndex += 1) {
      let foundIndex = -1;
      for (let tokenIndex = previousIndex + 1; tokenIndex < tokens.length; tokenIndex += 1) {
        if (tokens[tokenIndex] === phraseTokens[phraseIndex]) {
          foundIndex = tokenIndex;
          break;
        }
      }

      if (foundIndex === -1) {
        matched = false;
        break;
      }

      gap += foundIndex - previousIndex - 1;
      previousIndex = foundIndex;
    }

    if (matched && gap < bestGap) {
      bestGap = gap;
      if (bestGap === 0) {
        return 0;
      }
    }
  }

  return bestGap;
}

function levenshtein(left, right) {
  if (left === right) {
    return 0;
  }
  if (!left.length) {
    return right.length;
  }
  if (!right.length) {
    return left.length;
  }

  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let i = 0; i < left.length; i += 1) {
    const current = [i + 1];
    for (let j = 0; j < right.length; j += 1) {
      const insertions = previous[j + 1] + 1;
      const deletions = current[j] + 1;
      const substitutions = previous[j] + Number(left[i] !== right[j]);
      current.push(Math.min(insertions, deletions, substitutions));
    }
    for (let j = 0; j < current.length; j += 1) {
      previous[j] = current[j];
    }
  }
  return previous[right.length];
}

function buildSnippet(doc, parsed) {
  if (!doc.fragments) {
    doc.fragments = splitIntoFragments(doc.text);
  }

  if (!doc.fragments.length) {
    return "";
  }

  let bestFragment = doc.fragments[0];
  let bestScore = -1;

  for (const fragment of doc.fragments) {
    const normalized = normalizeText(fragment);
    let score = 0;
    for (const term of parsed.highlightTerms) {
      if (normalized.includes(term)) {
        score += term.length > 4 ? 3 : 2;
      }
    }
    for (const clause of parsed.positiveClauses) {
      if (clause.kind === "phrase" && normalized.includes(normalizeText(clause.text))) {
        score += 5;
      }
    }
    if (score > bestScore) {
      bestScore = score;
      bestFragment = fragment;
    }
  }

  const trimmed = bestFragment.length > 440 ? `${bestFragment.slice(0, 437)}...` : bestFragment;
  return highlightSnippet(trimmed, parsed);
}

function splitIntoFragments(text) {
  const normalized = text.replace(/\[[0-9:.]+\]\s*/g, "").trim();
  const paragraphs = normalized
    .split(/\n{2,}/)
    .map((fragment) => fragment.trim())
    .filter(Boolean);

  const fragments = [];
  for (const paragraph of paragraphs) {
    const sentences = paragraph.match(/[^.!?\n]+(?:[.!?]+|$)/g) ?? [paragraph];
    let buffer = "";
    for (const sentence of sentences.map((part) => part.trim()).filter(Boolean)) {
      const next = buffer ? `${buffer} ${sentence}` : sentence;
      if (next.length > 300 && buffer) {
        fragments.push(buffer);
        buffer = sentence;
      } else {
        buffer = next;
      }
    }
    if (buffer) {
      fragments.push(buffer);
    }
  }

  return fragments.length ? fragments : [normalized];
}

function highlightSnippet(snippet, parsed) {
  const escaped = escapeHtml(snippet);
  const phrases = parsed.positiveClauses
    .filter((clause) => clause.kind === "phrase")
    .map((clause) => clause.text)
    .sort((left, right) => right.length - left.length);
  const terms = parsed.highlightTerms
    .filter((term) => term.length > 1)
    .sort((left, right) => right.length - left.length);

  let output = escaped;
  for (const phrase of phrases) {
    output = wrapMatches(output, phrase);
  }
  for (const term of terms) {
    output = wrapMatches(output, term);
  }
  return output;
}

function wrapMatches(html, text) {
  const re = new RegExp(`(${escapeRegex(text)})`, "giu");
  return html.replace(re, "<mark>$1</mark>");
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildPreviewHtml(result, parsed) {
  const doc = state.searchEngine.getDocument(result.id);
  const snippet = buildSnippet(doc, parsed);

  return `
    <div class="preview-header">
      <h3>${escapeHtml(result.name)}</h3>
    </div>
    <div class="preview-snippet">${snippet || '<p class="preview-empty">No snippet available for this result.</p>'}</div>
  `;
}

function renderHelpPreview() {
  dom.previewContent.innerHTML = `
    <p class="preview-empty">
      Search the archive the same way as the desktop tool: type a query, inspect the ranked village and transcript lists, and see every matching village on the map.
    </p>
    <p class="preview-empty">
      Use <code>"quoted phrases"</code> for exact matches, <code>"phrase"~5</code> for proximity, <code>OR</code>, <code>NOT</code>, wildcard suffixes like <code>well*</code>, and fuzzy suffixes like <code>roman~</code>.
    </p>
  `;
}

function updateStatus(text) {
  dom.statusLine.textContent = text;
}

function renderResults(villageResults, transcriptResults, parsed) {
  dom.villageCount.textContent = String(villageResults.length);
  dom.transcriptCount.textContent = String(transcriptResults.length);

  renderResultList(dom.villageResults, villageResults, parsed);
  renderResultList(dom.transcriptResults, transcriptResults, parsed);
}

function renderResultList(container, results, parsed) {
  container.innerHTML = "";

  if (!results.length) {
    const item = document.createElement("li");
    item.className = "result-item";
    item.innerHTML = `<div class="result-card"><p class="result-title">No matches.</p></div>`;
    container.appendChild(item);
    return;
  }

  for (const result of results) {
    const item = document.createElement("li");
    item.className = "result-item";

    const selected = state.selectedResultId === result.id;
    item.innerHTML = `
      <div class="result-card${selected ? " is-selected" : ""}">
        <div class="result-main">
          <p class="result-title">${escapeHtml(result.name)}</p>
          <a class="result-open" href="${result.url}" target="_blank" rel="noopener noreferrer">Open</a>
        </div>
      </div>
    `;

    item.querySelector(".result-card").addEventListener("click", () => {
      selectResult(result.id, parsed);
    });
    item.querySelector(".result-open").addEventListener("click", (event) => {
      event.stopPropagation();
    });

    container.appendChild(item);
  }
}

function selectResult(resultId, parsed) {
  const allResults = [...state.villageResults, ...state.transcriptResults];
  const result = allResults.find((item) => item.id === resultId);
  if (!result) {
    return;
  }

  state.selectedResultId = result.id;
  state.selectedVillage = result.linkedVillages?.[0] ?? result.village;
  dom.previewContent.innerHTML = buildPreviewHtml(result, parsed);
  renderResults(state.villageResults, state.transcriptResults, parsed);
  renderMap(state.villageResults, state.transcriptResults);
}

function currentResultById(resultId) {
  return [...state.villageResults, ...state.transcriptResults].find((result) => result.id === resultId);
}

function runSearch() {
  if (!state.searchEngine) {
    return;
  }

  const query = dom.searchInput.value.trim();
  setQuerystring(query);

  if (!query) {
    state.villageResults = [];
    state.transcriptResults = [];
    state.selectedResultId = "";
    state.selectedVillage = "";
    renderResults([], [], null);
    renderHelpPreview();
    updateStatus(
      `Ready. ${state.rawData.stats.villageCount} village files (${state.rawData.stats.villagesWithCoords} with coordinates), ${state.rawData.stats.transcriptCount} transcripts.`
    );
    renderMap([], []);
    return;
  }

  const { parsed, villageResults, transcriptResults } = state.searchEngine.search(query);
  state.villageResults = villageResults;
  state.transcriptResults = transcriptResults;

  const allResults = [...villageResults, ...transcriptResults];
  const uniqueVillages = new Set(allResults.map((result) => result.village));
  updateStatus(`Query: "${query}" -> ${villageResults.length} village file hits, ${transcriptResults.length} transcript hits (across ${uniqueVillages.size} unique villages).`);

  if (!currentResultById(state.selectedResultId) && allResults.length) {
    state.selectedResultId = allResults[0].id;
    state.selectedVillage = allResults[0].linkedVillages?.[0] ?? allResults[0].village;
  } else if (!allResults.length) {
    state.selectedResultId = "";
    state.selectedVillage = "";
  }

  renderResults(villageResults, transcriptResults, parsed);

  if (state.selectedResultId) {
    selectResult(state.selectedResultId, parsed);
  } else {
    dom.previewContent.innerHTML = `<p class="preview-empty">No results matched this query.</p>`;
    renderMap(villageResults, transcriptResults);
  }
}

function initMap() {
  state.map = L.map("map", { attributionControl: false });
  L.control.attribution({ prefix: false })
    .addAttribution("&copy; OpenStreetMap &copy; CARTO")
    .addTo(state.map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png", {
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(state.map);

  state.layerGroups = {
    village: L.layerGroup().addTo(state.map),
    transcript: L.layerGroup().addTo(state.map),
    both: L.layerGroup().addTo(state.map),
  };

  state.legendControl = L.control({ position: "topright" });
  state.legendControl.onAdd = () => {
    const wrapper = L.DomUtil.create("div", "map-legend");
    wrapper.innerHTML = `
      <h3>Match Type</h3>
      <label class="legend-row"><input type="checkbox" data-group="village" checked> <span class="legend-dot blue"></span>Village only</label>
      <label class="legend-row"><input type="checkbox" data-group="transcript" checked> <span class="legend-dot yellow"></span>Transcript only</label>
      <label class="legend-row"><input type="checkbox" data-group="both" checked> <span class="legend-dot red"></span>Both</label>
      <hr>
      <label class="legend-row"><input type="checkbox" data-group="all-green"> <span class="legend-dot green"></span>Make all green</label>
    `;

    L.DomEvent.disableClickPropagation(wrapper);
    L.DomEvent.disableScrollPropagation(wrapper);

    state.legendCheckboxes.village = wrapper.querySelector('input[data-group="village"]');
    state.legendCheckboxes.transcript = wrapper.querySelector('input[data-group="transcript"]');
    state.legendCheckboxes.both = wrapper.querySelector('input[data-group="both"]');
    state.legendCheckboxes.allGreen = wrapper.querySelector('input[data-group="all-green"]');

    for (const group of ["village", "transcript", "both"]) {
      state.legendCheckboxes[group].addEventListener("change", (event) => {
        state.layerVisibility[group] = event.target.checked;
        const layerGroup = state.layerGroups[group];
        if (event.target.checked) {
          state.map.addLayer(layerGroup);
        } else {
          state.map.removeLayer(layerGroup);
        }
      });
    }

    state.legendCheckboxes.allGreen.addEventListener("change", (event) => {
      state.allGreen = event.target.checked;
      renderMap(state.villageResults, state.transcriptResults);
    });

    return wrapper;
  };
  state.legendControl.addTo(state.map);

  state.map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  requestAnimationFrame(() => state.map.invalidateSize());
}

function renderMap(villageResults, transcriptResults) {
  for (const group of Object.values(state.layerGroups)) {
    group.clearLayers();
  }

  const counts = new Map();
  for (const result of villageResults) {
    for (const linkedVillage of result.linkedVillages ?? [result.village]) {
      const current = counts.get(linkedVillage) ?? { village: 0, transcript: 0 };
      current.village += 1;
      counts.set(linkedVillage, current);
    }
  }
  for (const result of transcriptResults) {
    for (const linkedVillage of result.linkedVillages ?? [result.village]) {
      const current = counts.get(linkedVillage) ?? { village: 0, transcript: 0 };
      current.transcript += 1;
      counts.set(linkedVillage, current);
    }
  }

  const villageLookup = new Map(
    state.rawData.documents
      .filter((doc) => doc.kind === "village")
      .map((doc) => [doc.village, doc])
  );

  const bounds = [];
  for (const [village, count] of counts.entries()) {
    const doc = villageLookup.get(village);
    if (!doc || typeof doc.lat !== "number" || typeof doc.lon !== "number") {
      continue;
    }

    const groupKey =
      count.village && count.transcript
        ? "both"
        : count.village
          ? "village"
          : "transcript";
    const color = state.allGreen ? MAP_COLORS.allGreen : MAP_COLORS[groupKey];
    const selected = state.selectedVillage === village;
    const icon = L.divIcon({
      className: "smart-search-marker",
      html: `<div class="marker-dot${selected ? " is-selected" : ""}" style="background:${color}"></div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
    const marker = L.marker([doc.lat, doc.lon], { icon });
    marker.bindPopup(`<strong>${escapeHtml(village)}</strong><br>Villages: ${count.village} | Transcripts: ${count.transcript}`);
    marker.addTo(state.layerGroups[groupKey]);
    bounds.push([doc.lat, doc.lon]);

    if (selected) {
      marker.openPopup();
    }
  }

  if (!bounds.length) {
    state.map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  } else if (bounds.length === 1) {
    state.map.setView(bounds[0], 12);
  } else {
    state.map.fitBounds(bounds, { padding: [30, 30] });
  }
}

function setQuerystring(query) {
  const url = new URL(window.location.href);
  if (query) {
    url.searchParams.set("q", query);
  } else {
    url.searchParams.delete("q");
  }
  window.history.replaceState({}, "", url);
}

async function init() {
  setupTheme();
  renderHelpPreview();
  initMap();

  dom.themeToggle.addEventListener("click", () => {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("color-theme", isDark ? "dark" : "light");
    setupTheme();
  });
  dom.searchButton.addEventListener("click", runSearch);
  dom.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runSearch();
    }
  });
  dom.syntaxButton.addEventListener("click", () => dom.syntaxDialog.showModal());
  dom.closeSyntaxButton.addEventListener("click", () => dom.syntaxDialog.close());
  dom.syntaxDialog.addEventListener("click", (event) => {
    const rect = dom.syntaxDialog.getBoundingClientRect();
    const clickedInside =
      rect.top <= event.clientY &&
      event.clientY <= rect.top + rect.height &&
      rect.left <= event.clientX &&
      event.clientX <= rect.left + rect.width;
    if (!clickedInside) {
      dom.syntaxDialog.close();
    }
  });

  const response = await fetch("./data/search-documents.json", { cache: "no-cache" });
  state.rawData = await response.json();
  state.searchEngine = new SearchEngine(state.rawData);

  updateStatus(
    `Ready. ${state.rawData.stats.villageCount} village files (${state.rawData.stats.villagesWithCoords} with coordinates), ${state.rawData.stats.transcriptCount} transcripts.`
  );

  const query = new URLSearchParams(window.location.search).get("q");
  if (query) {
    dom.searchInput.value = query;
    runSearch();
  } else {
    renderMap([], []);
  }
}

init().catch((error) => {
  console.error(error);
  dom.previewContent.innerHTML = `<p class="preview-empty">Smart-search failed to load.</p>`;
  updateStatus("Smart-search failed to load.");
});
