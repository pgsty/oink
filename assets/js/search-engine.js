/**
 * search-engine.js — deterministic page search for the Command Palette.
 *
 * No index is built. All searchable text is one folded string with a segment
 * table, and each query term is found by scanning it. Sections are scored
 * with BM25 from the counts that scan yields; pages are ranked first by how
 * strong the fields holding the query are. A run of CJK characters matches as
 * overlapping bigrams. Nothing here reads a language tag or a dictionary.
 */
(function () {
  'use strict';

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

  // ---- Characters ---------------------------------------------------------
  // A character's script decides how it is matched; the page language does not.
  var CJK_SOURCE = '\\p{Script=Han}\\p{Script=Hiragana}\\p{Script=Katakana}\\p{Script=Hangul}ー';
  var CJK_CHAR = new RegExp('[' + CJK_SOURCE + ']', 'u');
  var LETTER = /[\p{L}\p{N}]/u;
  var IDENT_PUNCT = /[-./\\_:=]/;
  var ASCII_WORD = /^[a-z]+$/;

  function isCjk(ch) { return CJK_CHAR.test(ch); }

  // True when text[i] is a letter or digit of a script that separates words.
  function wordAt(text, i) {
    if (i < 0 || i >= text.length) return false;
    var code = text.charCodeAt(i);
    if (code < 128) return (code > 96 && code < 123) || (code > 47 && code < 58);
    if (code >= 0xD800 && code <= 0xDFFF) return false;
    var ch = text[i];
    return LETTER.test(ch) && !CJK_CHAR.test(ch);
  }

  // Match normalized text but keep offsets into the original label/snippet.
  // Most text needs no offset map; width/ligature/combining changes do.
  // A needle may be a string or `{ text, word: true }`. A word needle must
  // start a word, unless it is long enough to be found inside a compound.
  var segmenter;
  function matchRanges(value, needles, firstOnly) {
    if (!needles || !needles.length) return [];
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
      if (offsets.length !== normalized.length) offsets = null;
    }
    var ranges = [];
    needles.filter(Boolean).forEach(function (needle) {
      var word = typeof needle === 'object' && needle.word;
      needle = typeof needle === 'object' ? needle.text : needle;
      if (!needle) return;
      var at = normalized.indexOf(needle);
      while (at >= 0) {
        if (!word || needle.length >= INFIX_LENGTH || !wordAt(normalized, at - 1)) {
          ranges.push(offsets ? [offsets[at][0], offsets[at + needle.length - 1][1]]
            : [at, at + needle.length]);
          if (firstOnly) break;
        }
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

  // ---- Query analysis -----------------------------------------------------
  var ATOM = /[-./\\\p{L}\p{N}_]+(?:[=:][-./\\\p{L}\p{N}_]+)*/gu;
  var MAX_ATOMS = 30;
  // Function words still match, at a tenth of the weight, and no page is
  // required to contain them.
  var STOP_WORDS = new Set(('a an and are as at be by for from how in is it of on or ' +
    'that the this to was what when where which who why with').split(' '));
  var STOP_CJK = ['为什么', '如何', '怎么', '怎样', '什么', '请问'];
  var STOP_FACTOR = 0.1;

  // Cut one identifier-shaped atom where a CJK character meets a letter or
  // digit: `pg_upgrade升级` is two pieces, `文档/搜索.md` stays one path.
  function cut(atom) {
    var parts = [];
    var current = '';
    var previous = '';
    Array.from(atom).forEach(function (ch) {
      var kind = isCjk(ch) ? 'c' : IDENT_PUNCT.test(ch) ? 'p' : 'w';
      if (current && ((previous === 'c' && kind === 'w') || (previous === 'w' && kind === 'c'))) {
        parts.push(current);
        current = '';
      }
      current += ch;
      previous = kind;
    });
    if (current) parts.push(current);
    return parts;
  }

  // Pieces in query order: a word, an identifier, a symbol run, or a CJK run.
  function pieces(value) {
    var out = [];
    fold(value).split(' ').forEach(function (chunk) {
      if (!chunk) return;
      if (!LETTER.test(chunk)) {
        var symbol = chunk.replace(/^['"`“‘(\[]+|['"`”’)\],;]+$/g, '');
        if (Array.from(symbol).length >= 2) out.push({ kind: 'sym', text: symbol });
        return;
      }
      (chunk.match(ATOM) || []).forEach(function (atom) {
        if (!LETTER.test(atom)) return;
        cut(atom).forEach(function (part) {
          var text = part.replace(/[.:=-]+$/, '');
          if (!text || !LETTER.test(text)) return;
          var chars = Array.from(text);
          if (chars.every(isCjk)) out.push({ kind: 'cjk', text: text, chars: chars });
          else out.push({ kind: IDENT_PUNCT.test(text) ? 'ident' : 'word', text: text });
        });
      });
    });
    return out;
  }

  // Atoms are what a page must cover: each word, identifier or symbol run,
  // and each character of a CJK run. A term is a string to scan for and the
  // atoms it covers; a CJK run contributes its overlapping bigrams.
  function analyze(value) {
    var terms = [];
    var byText = new Map();
    var atoms = [];
    var spans = [];
    var phrase = [];
    function add(text, kind, covered, weight, stop) {
      var term = byText.get(text);
      if (!term) {
        term = { text: text, kind: kind, atoms: [], weight: weight, stop: stop };
        byText.set(text, term);
        terms.push(term);
      }
      covered.forEach(function (atom) {
        if (term.atoms.indexOf(atom) < 0) term.atoms.push(atom);
      });
      term.stop = term.stop && stop;
    }
    pieces(value).forEach(function (piece) {
      var base = atoms.length;
      if (base >= MAX_ATOMS) return;
      if (piece.kind !== 'cjk') {
        var stopWord = piece.kind === 'word' && STOP_WORDS.has(piece.text);
        atoms.push({ stop: stopWord });
        spans.push([base, 1]);
        phrase.push(piece.text);
        add(piece.text, piece.kind, [base], 1, stopWord);
        return;
      }
      var chars = piece.chars.slice(0, MAX_ATOMS - base);
      var run = chars.join('');
      var stops = chars.map(function () { return false; });
      STOP_CJK.forEach(function (word) {
        var size = Array.from(word).length;
        for (var at = run.indexOf(word); at >= 0; at = run.indexOf(word, at + 1)) {
          var first = Array.from(run.slice(0, at)).length;
          for (var k = 0; k < size; k += 1) stops[first + k] = true;
        }
      });
      chars.forEach(function (ch, i) { atoms.push({ stop: stops[i] }); });
      spans.push([base, chars.length]);
      phrase.push(run);
      if (chars.length === 1) add(chars[0], 'cjk', [base], 1, stops[0]);
      // A run of n characters holds about n/2 words but n-1 bigrams.
      else for (var i = 0; i + 1 < chars.length; i += 1)
        add(chars[i] + chars[i + 1], 'cjk', [base + i, base + i + 1],
          chars.length / (2 * (chars.length - 1)), stops[i] && stops[i + 1]);
    });
    // A query made only of function words is searched as written.
    if (atoms.length && atoms.every(function (atom) { return atom.stop; })) {
      atoms.forEach(function (atom) { atom.stop = false; });
      terms.forEach(function (term) { term.stop = false; });
    }
    return { terms: terms, atoms: atoms, spans: spans, phrase: phrase };
  }

  // Strings to highlight for a query that is not tied to a result.
  function terms(value) {
    return analyze(value).terms.map(function (term) { return term.text; });
  }

  // ---- English suffix stripping (Porter, 1980) for ASCII words ------------
  var STEP2 = ['ational', 'ate', 'tional', 'tion', 'enci', 'ence', 'anci', 'ance',
    'izer', 'ize', 'abli', 'able', 'alli', 'al', 'entli', 'ent', 'eli', 'e',
    'ousli', 'ous', 'ization', 'ize', 'ation', 'ate', 'ator', 'ate', 'alism', 'al',
    'iveness', 'ive', 'fulness', 'ful', 'ousness', 'ous', 'aliti', 'al',
    'iviti', 'ive', 'biliti', 'ble'];
  var STEP3 = ['icate', 'ic', 'ative', '', 'alize', 'al', 'iciti', 'ic', 'ical', 'ic',
    'ful', '', 'ness', ''];
  var STEP4 = ['al', 'ance', 'ence', 'er', 'ic', 'able', 'ible', 'ant', 'ement', 'ment',
    'ent', 'ion', 'ou', 'ism', 'ate', 'iti', 'ous', 'ive', 'ize'];
  var stems = new Map();

  function consonant(word, i) {
    var ch = word[i];
    if ('aeiou'.indexOf(ch) >= 0) return false;
    return ch !== 'y' || i === 0 || !consonant(word, i - 1);
  }
  function measure(word) {
    var count = 0;
    var vowelSeen = false;
    for (var i = 0; i < word.length; i += 1) {
      if (!consonant(word, i)) vowelSeen = true;
      else if (vowelSeen) { count += 1; vowelSeen = false; }
    }
    return count;
  }
  function hasVowel(word) {
    for (var i = 0; i < word.length; i += 1) if (!consonant(word, i)) return true;
    return false;
  }
  function doubled(word) {
    var n = word.length;
    return n > 1 && word[n - 1] === word[n - 2] && consonant(word, n - 1);
  }
  function cvc(word) {
    var n = word.length;
    return n > 2 && consonant(word, n - 3) && !consonant(word, n - 2) &&
      consonant(word, n - 1) && 'wxy'.indexOf(word[n - 1]) < 0;
  }
  function swap(word, table) {
    for (var i = 0; i < table.length; i += 2) {
      if (!word.endsWith(table[i])) continue;
      var base = word.slice(0, word.length - table[i].length);
      return measure(base) > 0 ? base + table[i + 1] : word;
    }
    return word;
  }
  function stem(word) {
    if (word.length < 3 || !ASCII_WORD.test(word)) return word;
    var cached = stems.get(word);
    if (cached !== undefined) return cached;
    var w = word;
    var base;
    if (w.endsWith('sses') || w.endsWith('ies')) w = w.slice(0, -2);
    else if (w.endsWith('s') && !w.endsWith('ss')) w = w.slice(0, -1);
    var stripped = false;
    if (w.endsWith('eed')) {
      if (measure(w.slice(0, -3)) > 0) w = w.slice(0, -1);
    } else if (w.endsWith('ed') && hasVowel(w.slice(0, -2))) {
      w = w.slice(0, -2);
      stripped = true;
    } else if (w.endsWith('ing') && hasVowel(w.slice(0, -3))) {
      w = w.slice(0, -3);
      stripped = true;
    }
    if (stripped) {
      if (/(at|bl|iz)$/.test(w)) w += 'e';
      else if (doubled(w) && !/[lsz]$/.test(w)) w = w.slice(0, -1);
      else if (measure(w) === 1 && cvc(w)) w += 'e';
    }
    if (w.endsWith('y') && hasVowel(w.slice(0, -1))) w = w.slice(0, -1) + 'i';
    w = swap(swap(w, STEP2), STEP3);
    for (var i = 0; i < STEP4.length; i += 1) {
      if (!w.endsWith(STEP4[i])) continue;
      base = w.slice(0, w.length - STEP4[i].length);
      if (measure(base) > 1 && (STEP4[i] !== 'ion' || /[st]$/.test(base))) w = base;
      break;
    }
    if (w.endsWith('e')) {
      base = w.slice(0, -1);
      var m = measure(base);
      if (m > 1 || (m === 1 && !cvc(base))) w = base;
    }
    if (w.endsWith('ll') && measure(w) > 1) w = w.slice(0, -1);
    if (stems.size > 20000) stems.clear();
    stems.set(word, w);
    return w;
  }

  function sharedPrefix(a, b) {
    var n = 0;
    while (n < a.length && n < b.length && a[n] === b[n]) n += 1;
    return n;
  }

  // How a word inflects: by English suffixes when it is a–z only, by a short
  // differing ending in other alphabets, and not at all once it holds a digit.
  function inflection(word) {
    if (ASCII_WORD.test(word)) return 'suffix';
    return /\p{N}/u.test(word) ? '' : 'ending';
  }

  // Whether `found` is another inflection of the query word.
  function sameWord(found, word) {
    var kind = inflection(word);
    if (kind === 'suffix') return ASCII_WORD.test(found) && stem(found) === stem(word);
    if (kind !== 'ending' || inflection(found) !== 'ending') return false;
    var shared = sharedPrefix(found, word);
    return shared >= 4 && found.length - shared <= 3 && word.length - shared <= 3 &&
      shared * 2 >= Math.max(found.length, word.length);
  }

  // The shortest beginning every inflection of `word` shares with it.
  function wordNeedle(word) {
    var kind = inflection(word);
    if (kind === 'suffix') {
      var shared = sharedPrefix(word, stem(word));
      return shared >= 3 ? word.slice(0, shared) : word;
    }
    return kind === 'ending' && word.length > 4
      ? word.slice(0, Math.max(4, word.length - 3)) : word;
  }

  // Optimal string alignment distance, abandoned once it must exceed `max`.
  function distance(a, b, max) {
    if (Math.abs(a.length - b.length) > max) return max + 1;
    var before = null;
    var current = [];
    var i;
    var j;
    for (j = 0; j <= b.length; j += 1) current[j] = j;
    for (i = 1; i <= a.length; i += 1) {
      var next = [i];
      var best = i;
      for (j = 1; j <= b.length; j += 1) {
        var value = Math.min(current[j] + 1, next[j - 1] + 1,
          current[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        if (before && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1])
          value = Math.min(value, before[j - 2] + 1);
        next[j] = value;
        if (value < best) best = value;
      }
      if (best > max) return max + 1;
      before = current;
      current = next;
    }
    return current[b.length];
  }

  // ---- Ranking constants --------------------------------------------------
  // Fields from strongest to weakest, and what a match in each is worth. A
  // match is exact (the term as written) or loose (a longer word, an
  // inflection, part of a name, a correction). Each part of the query takes
  // the strongest match found for it, so a page's strength depends on where
  // the query was found, never on how often.
  var TITLE = 0;
  var KEYWORDS = 1;
  var TAXONOMY = 2;
  var HEADING = 3;
  var DESCRIPTION = 4;
  var BODY = 5;
  var FIELD_WEIGHT = [10, 8, 6, 5, 3, 1];
  var EXACT = 0;
  var LOOSE = 1;
  var LOOSE_FACTOR = 0.7; // a loose match, as a share of its field's worth
  var PHRASE_FACTOR = 1.5; // the query's pieces adjacent and in order
  var STEPS = [];
  FIELD_WEIGHT.forEach(function (weight, field) {
    STEPS.push({ field: field, match: EXACT, worth: weight });
    STEPS.push({ field: field, match: LOOSE, worth: weight * LOOSE_FACTOR });
  });
  STEPS.sort(function (a, b) { return b.worth - a.worth; });
  var K1 = 1.2;
  var B = 0.5;
  var TF_CAP = 24; // occurrences counted per field of one page or section
  var COMPLETE = 0.9; // share of the query's information a full match covers
  var PREFIX_QUALITY = 0.7;
  var STEM_QUALITY = 0.6;
  var PART_QUALITY = 0.6; // a word or identifier found inside a longer name
  var INFIX_QUALITY = 0.25;
  var INFIX_LENGTH = 5; // shorter words never match inside another word
  var TYPO_QUALITY = 0.35;
  var EXCERPT_BEFORE = 40;
  var EXCERPT_LENGTH = 160;

  function create(documents, maxResults) {
    var docs = Array.from(new Map((documents || []).map(function (doc) {
      return [doc.ref, doc];
    })).values());
    var limit = number(maxResults, 10);

    // ---- One haystack, a segment table, and the sections behind it --------
    var parts = [];
    var cursor = 0;
    var segStart = [];
    var segOwner = [];
    var segField = [];
    var unitDoc = [];
    var unitId = [];
    var unitTitle = [];
    var unitFrom = [];
    var unitTo = [];
    var unitLength = [];
    var docFirst = [];
    var docUnits = [];
    var roots = [];
    var encoder = null;
    var decoder = null;

    // A segment belongs to a page (fields TITLE to DESCRIPTION) or to one of
    // its sections, whose heading and body take these two numbers.
    var UNIT_HEADING = 6;
    var UNIT_BODY = 7;
    function push(text, owner, field) {
      if (!text) return 0;
      segStart.push(cursor);
      segOwner.push(owner);
      segField.push(field);
      parts.push(text, '\n');
      cursor += text.length + 1;
      return text.length;
    }
    function unit(doc, id, title, from, to, body) {
      var index = unitDoc.length;
      unitDoc.push(doc);
      unitId.push(id);
      unitTitle.push(title);
      unitFrom.push(from);
      unitTo.push(to);
      push(fold(title), index, UNIT_HEADING);
      unitLength.push(push(fold(body), index, UNIT_BODY));
    }

    docs.forEach(function (doc, d) {
      roots.push(fold(doc.root || doc.type));
      push(fold(doc.title), d, TITLE);
      push(fold(doc.keywords), d, KEYWORDS);
      push(fold([fold(doc.categories), fold(doc.tags)].join(' ')), d, TAXONOMY);
      push(fold(doc.description), d, DESCRIPTION);
      docFirst.push(unitDoc.length);
      var body = typeof doc.body === 'string' ? doc.body : '';
      var sections = Array.isArray(doc.sections) ? doc.sections.filter(Boolean) : [];
      // An index written before sections existed still names its headings.
      if (!sections.length) push(fold(doc.headings), d, HEADING);
      // A split index names each section's start before its text has loaded.
      var offsets = !body ? [] : sections.filter(function (section) {
        return Number.isInteger(section.start);
      });
      if (!offsets.length) {
        if (body) unit(d, '', '', 0, body.length, body);
        sections.forEach(function (section) { unit(d, section.id, section.title, 0, 0, ''); });
      } else {
        // Section starts are UTF-8 byte offsets; excerpts need string offsets.
        encoder = encoder || new TextEncoder();
        decoder = decoder || new TextDecoder();
        var bytes = encoder.encode(body);
        var at = 0;
        var from = 0;
        var text;
        if (offsets[0].start > 0) {
          text = decoder.decode(bytes.subarray(0, offsets[0].start));
          unit(d, '', '', 0, text.length, text);
          at = text.length;
          from = offsets[0].start;
        }
        offsets.forEach(function (section, n) {
          var end = n + 1 < offsets.length ? offsets[n + 1].start : bytes.length;
          text = decoder.decode(bytes.subarray(Math.max(from, section.start), Math.max(from, end)));
          unit(d, section.id, section.title, at, at + text.length, text);
          at += text.length;
          from = Math.max(from, end);
        });
      }
      docUnits.push(unitDoc.length - docFirst[d]);
    });
    var hay = parts.join('');
    parts = null;
    var segments = segStart.length;
    var docCount = docs.length;
    var unitCount = unitDoc.length;

    // Per-query scratch space, cleared at the start of each query.
    var unitScore = new Float64Array(unitCount);
    var masks = function (count) { return [new Uint32Array(count), new Uint32Array(count)]; };
    var unitHead = masks(unitCount);
    var unitBody = masks(unitCount);
    var unitPhrase = new Uint8Array(unitCount);
    var unitTf = new Float32Array(unitCount);
    var docScore = new Float64Array(docCount);
    var docMask = [0, 1, 2, 3, 4].map(function () { return masks(docCount); });
    var docPhrase = new Uint8Array(docCount);
    var docTf = new Float32Array(docCount);
    var docSeen = new Uint8Array(docCount);
    var eligible = new Uint8Array(docCount);
    var scopes = new Map();
    var vocabulary = null;

    function scope(root) {
      var known = scopes.get(root);
      if (known) return known;
      var units = 0;
      var length = 0;
      for (var u = 0; u < unitCount; u += 1) {
        if (root && roots[unitDoc[u]] !== root) continue;
        units += 1;
        length += unitLength[u];
      }
      known = { units: Math.max(units, 1), average: Math.max(length / Math.max(units, 1), 1) };
      scopes.set(root, known);
      return known;
    }

    // Occurrences of `needle` in eligible pages. `judge` returns the quality
    // of the occurrence at an offset, or 0 when it is not a match there.
    // Returns how many were counted; tallies land in unitTf and docTf.
    function scan(needle, judge, bits, touchedUnits, touchedDocs) {
      var found = 0;
      var seg = 0;
      var counted = 0;
      var from = 0;
      var at;
      while ((at = hay.indexOf(needle, from)) >= 0) {
        while (seg + 1 < segments && segStart[seg + 1] <= at) { seg += 1; counted = 0; }
        var quality = judge ? judge(at) : 1;
        from = at + (quality ? needle.length : 1);
        if (!quality) continue;
        var field = segField[seg];
        var owner = segOwner[seg];
        var doc = field < UNIT_HEADING ? owner : unitDoc[owner];
        if (eligible[doc]) {
          found += 1;
          var mask;
          if (field < UNIT_HEADING) {
            if (!docTf[doc]) touchedDocs.push(doc);
            docTf[doc] += FIELD_WEIGHT[field] * quality;
            mask = docMask[field];
          } else {
            if (!unitTf[owner]) touchedUnits.push(owner);
            unitTf[owner] += FIELD_WEIGHT[field === UNIT_HEADING ? HEADING : BODY] * quality;
            mask = field === UNIT_HEADING ? unitHead : unitBody;
          }
          mask[LOOSE][owner] |= bits;
          if (quality === 1) mask[EXACT][owner] |= bits;
        }
        counted += 1;
        // Further repeats in this field cannot change its saturated score.
        if (counted >= TF_CAP) {
          if (seg + 1 >= segments) break;
          from = segStart[seg + 1];
        }
      }
      return found;
    }

    // A word matches itself, a longer word it begins, another inflection of
    // itself, or (when long) the inside of a compound.
    function wordJudge(term, surfaces) {
      var word = term.text;
      var known = new Map();
      return function (at) {
        if (wordAt(hay, at - 1))
          return word.length >= INFIX_LENGTH && hay.startsWith(word, at) ? INFIX_QUALITY : 0;
        var end = at;
        while (end - at < 64 && wordAt(hay, end)) end += 1;
        var found = hay.slice(at, end);
        // A word that is one part of a longer name is a loose match.
        if (found === word) return hay[at - 1] === '_' || hay[end] === '_' ? PART_QUALITY : 1;
        var quality = known.get(found);
        if (quality === undefined) {
          quality = found.startsWith(word) ? PREFIX_QUALITY
            : sameWord(found, word) ? STEM_QUALITY : 0;
          known.set(found, quality);
          if (quality === STEM_QUALITY && surfaces.length < 8) surfaces.push(found);
        }
        return quality;
      };
    }
    function identJudge(term) {
      var length = term.text.length;
      function inside(i) { return wordAt(hay, i) || hay[i] === '_'; }
      return function (at) { return inside(at - 1) || inside(at + length) ? PART_QUALITY : 1; };
    }
    function symbolJudge(term) {
      var length = term.text.length;
      var operator = /[<>=!~@#%^&*|+\-\/?:]/;
      return function (at) {
        return operator.test(hay[at - 1] || ' ') || operator.test(hay[at + length] || ' ')
          ? PART_QUALITY : 1;
      };
    }
    function exactJudge(length) {
      return function (at) { return wordAt(hay, at - 1) || wordAt(hay, at + length) ? 0 : TYPO_QUALITY; };
    }

    // Site words within one edit of a misspelt word (two from eight letters).
    function corrections(word) {
      if (!/^[a-z0-9]+$/.test(word) || word.length < 5) return [];
      if (!vocabulary) {
        vocabulary = new Map();
        var matches = hay.match(/[a-z][a-z0-9]{3,}/g) || [];
        for (var i = 0; i < matches.length; i += 1)
          vocabulary.set(matches[i], (vocabulary.get(matches[i]) || 0) + 1);
      }
      var max = word.length >= 8 ? 2 : 1;
      var found = [];
      vocabulary.forEach(function (count, candidate) {
        if (candidate === word) return;
        var edits = distance(word, candidate, max);
        if (edits <= max) found.push({ word: candidate, edits: edits, count: count });
      });
      return found.sort(function (a, b) {
        return a.edits - b.edits || b.count - a.count || lexical(a.word, b.word);
      }).slice(0, 3).map(function (entry) { return entry.word; });
    }

    // Locate the needles in a section's original text, at bounded cost.
    function locate(text, needles) {
      if (text.length <= 4000) return matchRanges(text, needles);
      var normalized = text.normalize('NFKC').toLowerCase();
      if (normalized.length === text.length && text.normalize('NFKC') === text)
        return matchRanges(text, needles);
      // Offsets drift where normalization changed a length; map one window.
      var first = -1;
      needles.forEach(function (needle) {
        var at = normalized.indexOf(typeof needle === 'object' ? needle.text : needle);
        if (at >= 0 && (first < 0 || at < first)) first = at;
      });
      if (first < 0) return [];
      var drift = Math.abs(normalized.length - text.length) + 8;
      var from = Math.max(0, first - drift - EXCERPT_LENGTH);
      if (from && /[\uDC00-\uDFFF]/.test(text[from])) from -= 1;
      var slice = text.slice(from, first + drift + EXCERPT_LENGTH * 3);
      return matchRanges(slice, needles).map(function (range) {
        return [range[0] + from, range[1] + from];
      });
    }

    // The passage that shows the most different matches, cut near the first.
    function snippet(text, needles) {
      text = String(text || '');
      if (!text || !needles.length) return '';
      var ranges = locate(text, needles).slice(0, 2000);
      if (!ranges.length) return '';
      // A marked stretch may hold several needles: adjacent bigrams merge.
      var held = ranges.map(function (range) {
        var piece = text.slice(range[0], range[1]).normalize('NFKC').toLowerCase();
        return needles.map(function (needle, n) {
          return piece.indexOf(typeof needle === 'object' ? needle.text : needle) >= 0 ? n : -1;
        }).filter(function (n) { return n >= 0; });
      });
      var bestAt = 0;
      var bestKinds = 0;
      for (var i = 0; i < ranges.length && bestKinds < needles.length; i += 1) {
        var kinds = new Set();
        for (var j = i; j < ranges.length &&
            ranges[j][1] - ranges[i][0] <= EXCERPT_LENGTH - EXCERPT_BEFORE; j += 1)
          held[j].forEach(function (n) { kinds.add(n); });
        if (kinds.size > bestKinds) { bestKinds = kinds.size; bestAt = i; }
      }
      var at = ranges[bestAt][0];
      var start = Math.max(0, at - EXCERPT_BEFORE);
      var end = Math.min(text.length, at + EXCERPT_LENGTH - EXCERPT_BEFORE);
      // Never cut a supplementary character in half at the excerpt boundary.
      if (start && /[\uDC00-\uDFFF]/.test(text[start])) start -= 1;
      if (end < text.length && /[\uDC00-\uDFFF]/.test(text[end])) end += 1;
      return (start ? '…' : '') + text.slice(start, end).trim() + (end < text.length ? '…' : '');
    }

    function query(value, options) {
      var analysis = analyze(value);
      var atoms = analysis.atoms;
      if (!atoms.length) return [];
      var root = options && options.root ? fold(options.root) : '';
      var d;
      var u;
      for (d = 0; d < docCount; d += 1) eligible[d] = !root || roots[d] === root ? 1 : 0;
      unitScore.fill(0);
      [unitHead, unitBody].concat(docMask).forEach(function (pair) {
        pair[EXACT].fill(0);
        pair[LOOSE].fill(0);
      });
      unitPhrase.fill(0);
      docScore.fill(0);
      docPhrase.fill(0);
      docSeen.fill(0);
      var statistics = scope(root);
      var hitDocs = [];
      var marks = [];
      var absent = Math.log(1 + (statistics.units + 0.5) / 0.5);

      analysis.terms.forEach(function (term) {
        var bits = 0;
        term.atoms.forEach(function (atom) { bits |= 1 << atom; });
        var touchedUnits = [];
        var touchedDocs = [];
        var surfaces = [];
        var found = 0;
        if (term.kind === 'word') {
          found = scan(wordNeedle(term.text), wordJudge(term, surfaces), bits, touchedUnits, touchedDocs);
          // Spelling help applies only when the scope holds no form of the word.
          if (!found) corrections(term.text).forEach(function (candidate) {
            if (scan(candidate, exactJudge(candidate.length), bits, touchedUnits, touchedDocs))
              surfaces.push(candidate);
          });
        } else {
          found = scan(term.text, term.kind === 'ident' ? identJudge(term)
            : term.kind === 'sym' ? symbolJudge(term) : null, bits, touchedUnits, touchedDocs);
        }
        var df = touchedUnits.length + touchedDocs.length;
        term.idf = df ? Math.log(1 + (Math.max(statistics.units, df) - df + 0.5) / (df + 0.5)) : 0;
        if (!df) return;
        var weight = term.idf * term.weight * (term.stop ? STOP_FACTOR : 1);
        touchedUnits.forEach(function (index) {
          var tf = unitTf[index];
          unitTf[index] = 0;
          unitScore[index] += weight * tf * (K1 + 1) /
            (tf + K1 * (1 - B + B * unitLength[index] / statistics.average));
          var doc = unitDoc[index];
          if (!docSeen[doc]) { docSeen[doc] = 1; hitDocs.push(doc); }
        });
        touchedDocs.forEach(function (doc) {
          var tf = docTf[doc];
          docTf[doc] = 0;
          docScore[doc] += weight * tf * (K1 + 1) / (tf + K1);
          if (!docSeen[doc]) { docSeen[doc] = 1; hitDocs.push(doc); }
        });
        // Highlight what was found: the term, its inflections, or its correction.
        if (found) marks.push(term.kind === 'word' ? { text: term.text, word: true } : term.text);
        surfaces.forEach(function (surface) { marks.push({ text: surface, word: true }); });
      });
      if (!hitDocs.length) return [];

      // The pieces in the order typed, adjacent in the text: nothing, a space
      // or one joining mark between them (`PostgreSQL备份`, `point-in-time`).
      if (analysis.phrase.length > 1 || atoms.length > 2) {
        var phrase = new RegExp(analysis.phrase.map(function (piece) {
          return piece.replace(/[.*+?^${}()|[\]\\\/-]/g, '\\$&');
        }).join('[ \\-_./]?'), 'g');
        var seg = 0;
        var match;
        while ((match = phrase.exec(hay))) {
          while (seg + 1 < segments && segStart[seg + 1] <= match.index) seg += 1;
          if (segField[seg] < UNIT_HEADING) docPhrase[segOwner[seg]] = 1;
          else unitPhrase[segOwner[seg]] = 1;
          if (seg + 1 >= segments) break;
          phrase.lastIndex = segStart[seg + 1];
        }
      }

      // An atom weighs what its commonest covering term is worth. A term the
      // scope lacks cannot be asked of any page; an atom with no term left
      // stays uncovered, so every page is then a partial match.
      var weights = atoms.map(function () { return Infinity; });
      analysis.terms.forEach(function (term) {
        if (!term.idf) return;
        term.atoms.forEach(function (atom) { weights[atom] = Math.min(weights[atom], term.idf); });
      });
      // A function word adds to the score but is never required of a page.
      var total = 0;
      weights = weights.map(function (weight, atom) {
        weight = atoms[atom].stop ? 0 : weight === Infinity ? absent : weight;
        total += weight;
        return weight;
      });
      function weigh(mask) {
        var sum = 0;
        for (var atom = 0; atom < weights.length; atom += 1)
          if (mask & (1 << atom)) sum += weights[atom];
        return sum;
      }
      // Shown as "matched/total terms": a word counts once, a CJK run by pairs.
      function count(mask) {
        var matched = 0;
        var all = 0;
        analysis.spans.forEach(function (span) {
          var asked = 0;
          var covered = 0;
          for (var k = span[0]; k < span[0] + span[1]; k += 1) {
            if (atoms[k].stop) continue;
            asked += 1;
            if (mask & (1 << k)) covered += 1;
          }
          var units = Math.ceil(asked / 2);
          all += units;
          matched += covered === asked ? units : Math.min(units - 1, Math.round(covered / 2));
        });
        return [matched, all];
      }

      var hits = hitDocs.map(function (doc) {
        var union = 0;
        var best = null;
        // One section together with its page's own fields.
        function consider(index, score, phrase) {
          var covered = 0;
          var worth = 0;
          for (var n = 0; n < STEPS.length; n += 1) {
            var step = STEPS[n];
            var mask = step.field === BODY ? 0 : docMask[step.field][step.match][doc];
            if (index >= 0 && step.field === HEADING) mask |= unitHead[step.match][index];
            if (index >= 0 && step.field === BODY) mask |= unitBody[step.match][index];
            mask &= ~covered;
            if (!mask) continue;
            worth += weigh(mask) * step.worth;
            covered |= mask;
          }
          union |= covered;
          var part = weigh(covered) / total;
          var candidate = { unit: index, whole: part >= COMPLETE, share: part, score: score,
            phrase: phrase, strength: worth / total * (phrase ? PHRASE_FACTOR : 1) };
          if (!best || (Number(candidate.whole) - Number(best.whole) ||
              candidate.strength - best.strength || candidate.share - best.share ||
              candidate.score - best.score) > 0)
            best = candidate;
        }
        consider(-1, 0, docPhrase[doc]);
        for (u = docFirst[doc]; u < docFirst[doc] + docUnits[doc]; u += 1)
          if (unitScore[u]) consider(u, unitScore[u], docPhrase[doc] || unitPhrase[u]);
        var covered = weigh(union) / total;
        var counted = count(union);
        var boost = number(docs[doc].boost, 1);
        var textScore = docScore[doc] + best.score;
        return { doc: docs[doc], unit: best.unit, phrase: !!best.phrase,
          partial: covered < COMPLETE, covered: covered, matched: counted[0], total: counted[1],
          // Covered only by combining several sections of the page.
          scattered: covered >= COMPLETE && !best.whole,
          strength: Math.round(best.strength * boost * 1000) / 1000,
          textScore: textScore, score: textScore * boost };
      });

      // A page that holds only the query's function words is not a result.
      hits = hits.filter(function (hit) { return hit.covered > 0; });
      var complete = hits.some(function (hit) { return !hit.partial; });
      return hits.filter(function (hit) { return !complete || !hit.partial; })
        .sort(function (a, b) {
          return (complete ? Number(a.scattered) - Number(b.scattered)
            : Math.round(b.covered * 10) - Math.round(a.covered * 10)) ||
            b.strength - a.strength || compare(a, b);
        }).slice(0, limit).map(function (hit) {
          var doc = hit.doc;
          var index = hit.unit;
          var body = index >= 0 && typeof doc.body === 'string'
            ? doc.body.slice(unitFrom[index], unitTo[index]) : '';
          hit.ref = doc.ref;
          hit.heading = '';
          if (index >= 0 && unitId[index]) {
            hit.ref = doc.ref.split('#')[0] + '#' + encodeURIComponent(unitId[index]);
            hit.heading = unitTitle[index];
          }
          hit.excerpt = snippet(body, marks) || snippet(doc.description, marks) ||
            doc.description || doc.excerpt || '';
          hit.marks = marks;
          delete hit.unit;
          delete hit.covered;
          delete hit.scattered;
          return hit;
        });
    }

    return { query: query };
  }

  window.OinkSearchEngine = {
    compare: compare,
    group: group,
    lexical: lexical,
    create: create,
    terms: terms,
    matchRanges: matchRanges,
    stem: stem,
  };
  if (typeof module === 'object' && module.exports)
    module.exports = window.OinkSearchEngine;
})();
