/**
 * search-engine.js — deterministic page search for the Command Palette.
 *
 * The index builder is injected so this module can be unit-tested without a
 * DOM. Literal mixed-language matching shares coverage/phrase tiers with
 * English stemming and typo fallback. Page boosts apply inside those tiers.
 */
(function () {
  'use strict';

  var CJK = /[぀-ヿ㐀-䶿一-鿿豈-﫿]/;

  function number(value, fallback) {
    var parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  function lexical(a, b) {
    a = String(a || '');
    b = String(b || '');
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function compare(a, b) {
    return (
      b.score - a.score ||
      lexical(a.doc.title, b.doc.title) ||
      lexical(a.doc.ref, b.doc.ref)
    );
  }

  function group(results) {
    var groups = [];
    var groupByKey = new Map();
    (results || []).forEach(function (result) {
      var rawKey = result.doc.root || result.doc.type || 'pages';
      var key = String(rawKey).trim().toLowerCase() || 'pages';
      var current = groupByKey.get(key);
      if (!current) {
        current = {
          key: key,
          label:
            (result.doc.breadcrumb && result.doc.breadcrumb[0]) ||
            result.doc.root ||
            result.doc.type ||
            'Pages',
          results: [],
        };
        groupByKey.set(key, current);
        groups.push(current);
      }
      current.results.push(result);
    });
    return groups;
  }

  function fold(value) {
    return String(Array.isArray(value) ? value.join(' ') : value || '')
      .normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  // Match normalized text but keep offsets into the original label/snippet.
  // Most text needs no offset map; width/ligature/combining changes do.
  var segmenter;
  function matchRanges(value, needles, firstOnly) {
    var text = String(value || '');
    var lower = text.toLowerCase();
    var normalized = text.normalize('NFKC').toLowerCase();
    var offsets = null;
    if (normalized !== lower || lower.length !== text.length) {
      offsets = [];
      var parts = typeof Intl.Segmenter === 'function'
        ? (segmenter || (segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' }))).segment(text)
        : Array.from(text.matchAll(/\P{M}\p{M}*|\p{M}+/gu), function (part) {
          return { segment: part[0], index: part.index };
        });
      for (var part of parts) {
        var segment = part.segment.normalize('NFKC').toLowerCase();
        for (var n = 0; n < segment.length; n += 1)
          offsets.push([part.index, part.index + part.segment.length]);
      }
    }
    var ranges = [];
    needles.filter(Boolean).forEach(function (needle) {
      var at = normalized.indexOf(needle);
      while (at >= 0) {
        ranges.push(offsets ? [offsets[at][0], offsets[at + needle.length - 1][1]]
          : [at, at + needle.length]);
        if (firstOnly) break;
        at = normalized.indexOf(needle, at + needle.length);
      }
    });
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [];
    ranges.forEach(function (range) {
      var last = merged[merged.length - 1];
      if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
      else merged.push(range.slice());
    });
    return merged;
  }

  // Keep code identifiers intact; split CJK/Latin boundaries even without spaces.
  // No dictionary: a contiguous CJK run remains a literal substring term.
  function terms(value) {
    var atoms = fold(value).match(
      /[-./\\\p{L}\p{N}_]+(?:[=:][-./\\\p{L}\p{N}_]+)*/gu,
    ) || [];
    var split = [];
    atoms.forEach(function (atom) {
      // Paths and code names can themselves contain Chinese or Windows slashes.
      if (/[_./\\:=\-]/.test(atom)) split.push(atom);
      else split = split.concat(atom.replace(
        /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}ー]+/gu,
        ' $& ',
      ).trim().split(/\s+/));
    });
    return Array.from(new Set(split)).filter(function (term) {
      return /[\p{L}\p{N}]/u.test(term);
    }).slice(0, 24);
  }

  var weights = { title: 100, keywords: 80, categories: 60, tags: 60,
    headings: 50, description: 30, body: 10 };

  // A literal term scores by the best field that contains it. Repeated
  // occurrences in that field order pages within its tier: the bonus grows
  // toward 20% and never lets a field outrank the next one up (body stays
  // under 12 while description starts at 30; headings stay under tags' 60).
  // A single occurrence keeps the plain field weight.
  var REPEAT_CAP = 20;
  function occurrences(text, term) {
    var count = 0;
    for (var at = text.indexOf(term); at >= 0 && count < REPEAT_CAP; at = text.indexOf(term, at + term.length))
      count += 1;
    return count;
  }
  function literalScore(fields, term) {
    var best = 0;
    Object.keys(weights).forEach(function (key) {
      var count = occurrences(fields[key], term);
      if (count) best = Math.max(best, weights[key] * (1 + 0.2 * (1 - 1 / count)));
    });
    return best;
  }

  function create(documents, lunrApi, maxResults) {
    var docs = Array.from(new Map((documents || []).map(function (doc) {
      return [doc.ref, doc];
    })).values());
    var limit = number(maxResults, 10);
    var index = null;
    var folded = docs.map(function (doc) {
      var fields = {};
      Object.keys(weights).forEach(function (key) { fields[key] = fold(doc[key]); });
      return fields;
    });
    var sectionCache = new Map();

    function englishMatches(term, eligible) {
      var matches = new Map();
      // Technical punctuation is literal, never Lunr query syntax or a typo.
      if (!lunrApi || !/^[a-z0-9]+$/.test(term)) return matches;
      if (!index) {
        index = lunrApi(function () {
          this.ref('ref');
          Object.keys(weights).forEach(function (key) {
            this.field(key, { boost: weights[key] / 10 });
          }, this);
          docs.forEach(function (doc) { this.add(doc); }, this);
        });
      }
      // Exact/stemmed English matches retain the bundled language pipeline.
      var found = index.query(function (builder) { builder.term(term); })
        .filter(function (hit) { return !eligible || eligible.has(hit.ref); });
      function remember(hit, quality) {
        var score = 0;
        Object.values(hit.matchData.metadata).forEach(function (fields) {
          Object.keys(fields).forEach(function (field) {
            score = Math.max(score, weights[field] || 0);
          });
        });
        matches.set(hit.ref, score * quality);
      }
      found.forEach(function (hit) { remember(hit, 0.9); });
      // Substrings are handled literally below. Typo expansion is a fallback,
      // bounded for short terms to avoid unrelated two-letter matches.
      if (!found.length && term.length >= 5) {
        index.query(function (builder) {
          builder.term(term, { editDistance: term.length >= 8 ? 2 : 1 });
        }).forEach(function (hit) { remember(hit, 0.35); });
      }
      return matches;
    }

    function snippet(text, needles, phrase) {
      text = String(text || '');
      var matches = phrase ? matchRanges(text, [phrase], true) : [];
      if (!matches.length) matches = matchRanges(text, needles, true);
      if (!matches.length) return '';
      var at = matches[0][0];
      var start = Math.max(0, at - 40);
      var end = Math.min(text.length, at + 120);
      // Never cut a supplementary character in half at the excerpt boundary.
      if (start && /[\uDC00-\uDFFF]/.test(text[start])) start -= 1;
      if (end < text.length && /[\uDC00-\uDFFF]/.test(text[end])) end += 1;
      return (start ? '…' : '') + text.slice(start, end).trim() + (end < text.length ? '…' : '');
    }

    function sectionsFor(doc) {
      if (sectionCache.has(doc.ref)) return sectionCache.get(doc.ref);
      var sections = doc.sections || [];
      var bytes = doc.body ? new TextEncoder().encode(doc.body) : null;
      var decoder = new TextDecoder();
      var result = sections.map(function (section, n) {
        var end = n + 1 < sections.length ? sections[n + 1].start : undefined;
        var body = bytes && Number.isInteger(section.start)
          ? decoder.decode(bytes.subarray(section.start, end)) : '';
        return { id: section.id, title: section.title, body: body,
          heading: fold(section.title), text: fold(body) };
      });
      // Introductory text is a real page-level match and must compete with
      // sections, otherwise a strong intro hit can jump to an unrelated heading.
      if (bytes && (!sections.length || sections[0].start > 0)) {
        var intro = decoder.decode(bytes.subarray(0, sections.length ? sections[0].start : undefined));
        result.unshift({ id: '', title: '', body: intro, heading: '', text: fold(intro) });
      }
      sectionCache.set(doc.ref, result);
      return result;
    }

    function context(result, needles, phrase) {
      var doc = result.doc;
      var best = null;
      sectionsFor(doc).forEach(function (section) {
        var matched = 0;
        var score = 0;
        needles.forEach(function (term) {
          var titleMatch = section.heading.indexOf(term) >= 0;
          var bodyMatch = section.text.indexOf(term) >= 0;
          if (titleMatch || bodyMatch) matched += 1;
          score += titleMatch ? 50 : bodyMatch ? 10 : 0;
        });
        var exact = section.heading.indexOf(phrase) >= 0 || section.text.indexOf(phrase) >= 0;
        var rank = matched * 1000 + (exact ? 200 : 0) + score;
        if (matched && (!best || rank > best.rank)) best = { section: section, rank: rank };
      });
      result.ref = doc.ref;
      result.heading = '';
      result.excerpt = snippet(doc.body, needles) || snippet(doc.description, needles) ||
        doc.description || doc.excerpt || '';
      if (best) {
        result.excerpt = snippet(best.section.body, needles, phrase) || best.section.title;
      }
      if (best && best.section.id) {
        result.ref = doc.ref.split('#')[0] + '#' + encodeURIComponent(best.section.id);
        result.heading = best.section.title;
      }
      return result;
    }

    function query(value, options) {
      var needles = terms(value);
      var phrase = needles.join(' ');
      if (!needles.length) return [];
      var root = options && options.root ? fold(options.root) : '';
      var eligible = root ? new Set(docs.filter(function (doc) {
        return fold(doc.root || doc.type) === root;
      }).map(function (doc) { return doc.ref; })) : null;
      var alternatives = needles.map(function (term) { return englishMatches(term, eligible); });
      var hits = [];
      docs.forEach(function (doc, n) {
        if (eligible && !eligible.has(doc.ref)) return;
        var fields = folded[n];
        var matched = 0;
        var textScore = 0;
        var phraseMatch = false;
        needles.forEach(function (term, t) {
          var score = literalScore(fields, term);
          var alternative = alternatives[t].get(doc.ref) || 0;
          if (score || alternative) matched += 1;
          textScore += Math.max(score, alternative);
        });
        Object.keys(weights).forEach(function (key) {
          if (needles.length > 1 && fields[key].indexOf(phrase) >= 0) phraseMatch = true;
        });
        if (matched) hits.push({ doc: doc, textScore: textScore,
          score: textScore * number(doc.boost, 1), matched: matched,
          total: needles.length, phrase: phraseMatch, partial: matched < needles.length });
      });
      var complete = hits.some(function (hit) { return !hit.partial; });
      return hits.filter(function (hit) { return !complete || !hit.partial; })
        .sort(function (a, b) {
          return b.matched - a.matched || Number(b.phrase) - Number(a.phrase) || compare(a, b);
        }).slice(0, limit).map(function (hit) { return context(hit, needles, phrase); });
    }

    return { query: query, queryCjk: query, queryLatin: query };
  }

  window.OinkSearchEngine = {
    CJK: CJK,
    compare: compare,
    group: group,
    lexical: lexical,
    create: create,
    terms: terms,
    matchRanges: matchRanges,
  };
  if (typeof module === 'object' && module.exports)
    module.exports = window.OinkSearchEngine;
})();
