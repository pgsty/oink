/** Typeset copy. A selection copied out of article prose leaves the page as
 *  clean rich text: semantic tags carrying a small inline style sheet drawn
 *  from the print palette. An editor that keeps inline styles (WeChat, Word,
 *  mail) then shows the printed page, and one that keeps only structure
 *  (Notion, Docs outlines) still gets headings, lists, code and tables.
 *
 *  Left to itself a browser serialises a selection with the computed style of
 *  every block, which inlines the page canvas as a background, the reader's
 *  dark palette, rem margins, the whole font stack, and interface controls
 *  such as heading anchors. `text/plain` is written exactly as the browser
 *  would write it; any failure here leaves the native copy untouched. */
(function (global) {
  'use strict';

  var MONO = "'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace";
  var DROP = /^(SCRIPT|STYLE|TEMPLATE|NOSCRIPT|BUTTON|SELECT|TEXTAREA|NAV|FORM|IFRAME|OBJECT|EMBED|SVG|CANVAS|VIDEO|AUDIO|DIALOG|LINK|META|SOURCE)$/;
  var BLOCK = /^(P|DIV|SECTION|ARTICLE|HEADER|FOOTER|MAIN|ASIDE|ADDRESS|H[1-6]|UL|OL|LI|DL|DT|DD|BLOCKQUOTE|PRE|TABLE|THEAD|TBODY|TFOOT|TR|TD|TH|CAPTION|FIGURE|FIGCAPTION|DETAILS|SUMMARY|HR)$/;
  var INLINE = { text: 1, a: 1, strong: 1, em: 1, del: 1, u: 1, mark: 1, sub: 1, sup: 1, kbd: 1, code: 1, br: 1, img: 1, math: 1 };
  var SPACE = /[^ \t\n\r\f]/;
  // Interface that lives inside the prose container. A selection that only
  // crosses one of these drops it; a selection wholly inside one stays native.
  var CHROME = ['td-page-end', 'td-article-meta', 'td-article-info', 'td-byline', 'td-series-strip',
    'td-page-actions', 'td-breadcrumbs', 'td-heading-self-link', 'footnote-backref',
    'td-code__utilities', 'td-code__expand', 'td-map__canvas', 'td-map__load', 'visually-hidden'];
  var LINE_NUMBERS = ['ln', 'lnt', 'lnlinks'];
  var DEFAULTS = {
    ink: '#171717', strong: '#111111', muted: '#70757d', meta: '#4e555c', line: '#c9ced4',
    link: '#174f78', codeBg: '#f5f7f9', tableLine: '#b8bec5', quoteLine: '#8b5a2b',
    quoteBg: '#faf7f3', quoteInk: '#30343a', headerBg: '#edf0f3',
    radius: 6, headingFont: '', headingRule: 'under', rtl: false
  };

  function tagOf(node) { return String(node.nodeName || '').toUpperCase(); }
  function has(el, name) { return !!(el.classList && el.classList.contains(name)); }
  function hasAny(el, names) {
    for (var i = 0; i < names.length; i += 1) if (has(el, names[i])) return true;
    return false;
  }
  function attr(el, name) { return el.getAttribute ? el.getAttribute(name) : null; }
  function esc(text) { return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function escAttr(text) { return esc(text).replace(/"/g, '&quot;'); }

  /** Normalise a stylesheet or computed colour to hex or rgba(), the two
   *  forms every paste target understands. Anything else is refused. */
  function color(value) {
    var v = String(value == null ? '' : value).trim().toLowerCase();
    var m;
    if (/^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/.test(v)) return v;
    function out(r, g, b, a) {
      var parts = [r, g, b].map(function (n) { return Math.max(0, Math.min(255, Math.round(n))); });
      if (parts.some(isNaN)) return '';
      if (a < 0.004) return '';
      if (a < 0.996) return 'rgba(' + parts.join(', ') + ', ' + (Math.round(a * 100) / 100) + ')';
      return '#' + parts.map(function (n) { return (n < 16 ? '0' : '') + n.toString(16); }).join('');
    }
    function alpha(text) {
      if (text === undefined || text === '') return 1;
      return /%$/.test(text) ? parseFloat(text) / 100 : parseFloat(text);
    }
    m = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$/.exec(v);
    if (m) return out(+m[1], +m[2], +m[3], alpha(m[4]));
    m = /^color\(\s*srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+%?))?\s*\)$/.exec(v);
    if (m) return out(m[1] * 255, m[2] * 255, m[3] * 255, alpha(m[4]));
    return '';
  }

  function luminance(hex) {
    var m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/.exec(hex);
    if (!m) return 1;
    var c = [m[1], m[2], m[3]].map(function (x) {
      var n = parseInt(x, 16) / 255;
      return n <= 0.04045 ? n / 12.92 : Math.pow((n + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }

  /** The paper palette: the print tokens, which are the light preset palette
   *  on white whatever mode the screen is in. */
  function readSkin(style, direction) {
    var skin = {};
    var key;
    for (key in DEFAULTS) skin[key] = DEFAULTS[key];
    if (!style || typeof style.getPropertyValue !== 'function') return skin;
    var names = {
      ink: 'ink', strong: 'strong', muted: 'muted', meta: 'meta', line: 'line', link: 'link',
      codeBg: 'code-bg', tableLine: 'table-line', quoteLine: 'quote-line', quoteBg: 'quote-bg',
      quoteInk: 'quote-ink', headerBg: 'header-bg'
    };
    for (key in names) skin[key] = color(style.getPropertyValue('--td-print-' + names[key])) || skin[key];
    var radius = /^\s*([\d.]+)(px|rem)\s*$/.exec(style.getPropertyValue('--td-code-radius'));
    if (radius) skin.radius = Math.min(8, Math.round(radius[1] * (radius[2] === 'rem' ? 16 : 1)));
    var font = style.getPropertyValue('--td-copy-heading-font').trim().replace(/"/g, "'");
    if (font && /^[\w\s,'-]+$/.test(font)) skin.headingFont = font;
    var rule = style.getPropertyValue('--td-copy-heading-rule').trim();
    if (rule === 'over' || rule === 'under' || rule === 'none') skin.headingRule = rule;
    skin.rtl = direction === 'rtl';
    return skin;
  }

  // ---- 1. The selection as a tree --------------------------------------

  function isChrome(el) {
    if (!el.getAttribute) return false;
    return el.hasAttribute('hidden') || attr(el, 'aria-hidden') === 'true' ||
      attr(el, 'role') === 'tablist' || hasAny(el, CHROME);
  }

  function find(node, test) {
    var kids = node.childNodes || [];
    for (var i = 0; i < kids.length; i += 1) {
      if (kids[i].nodeType !== 1) continue;
      if (test(kids[i])) return kids[i];
      var hit = find(kids[i], test);
      if (hit) return hit;
    }
    return null;
  }

  function findAll(node, test, into) {
    into = into || [];
    var kids = node.childNodes || [];
    for (var i = 0; i < kids.length; i += 1) {
      if (kids[i].nodeType !== 1) continue;
      if (test(kids[i])) into.push(kids[i]);
      findAll(kids[i], test, into);
    }
    return into;
  }

  function textOf(node) {
    if (node.nodeType === 3) return node.nodeValue || '';
    var out = '';
    var kids = node.childNodes || [];
    for (var i = 0; i < kids.length; i += 1) out += textOf(kids[i]);
    return out;
  }

  function collector(range, env) {
    var styleOf = env.styleOf || function () { return null; };

    function inRange(node) { return !range || range.intersectsNode(node); }

    function slice(node) {
      var text = node.nodeValue || '';
      var from = 0;
      var to = text.length;
      if (range && node === range.startContainer) from = range.startOffset;
      if (range && node === range.endContainer) to = range.endOffset;
      return text.slice(from, to);
    }

    function unseen(el) {
      var style = styleOf(el);
      if (!style) return false;
      return style.display === 'none' || style.visibility === 'hidden' ||
        style.userSelect === 'none' || style.webkitUserSelect === 'none';
    }

    function kidsOf(node) {
      var out = [];
      var kids = node.childNodes || [];
      for (var i = 0; i < kids.length; i += 1) out.push.apply(out, walk(kids[i]));
      return out;
    }

    function math(node, block) {
      var source = find(node, function (el) { return tagOf(el) === 'ANNOTATION'; });
      var tex = source ? textOf(source).trim() : '';
      return tex ? [{ t: 'math', v: tex, block: block }] : [];
    }

    /** One code block: its text, cut to the selection, with the colour each
     *  token is painted in. Line numbers are interface, not code. */
    function code(pre, title) {
      var tokens = [];
      var cache = typeof Map === 'function' ? new Map() : null;
      function paint(el) {
        if (cache && cache.has(el)) return cache.get(el);
        var style = styleOf(el);
        var ink = style ? {
          c: color(style.color),
          b: parseInt(style.fontWeight, 10) >= 600,
          i: style.fontStyle === 'italic'
        } : { c: '', b: false, i: false };
        if (cache) cache.set(el, ink);
        return ink;
      }
      (function visit(node, parent) {
        if (!inRange(node)) return;
        if (node.nodeType === 3) {
          var text = slice(node);
          if (text) {
            var ink = paint(parent);
            tokens.push({ v: text, c: ink.c, b: ink.b, i: ink.i });
          }
          return;
        }
        if (node.nodeType !== 1 || hasAny(node, LINE_NUMBERS) || isChrome(node) || unseen(node)) return;
        var kids = node.childNodes || [];
        for (var i = 0; i < kids.length; i += 1) visit(kids[i], node);
      })(pre, pre);
      if (!tokens.length) return [];
      var surface = styleOf(pre);
      var bg = '';
      // The shell paints the card; the <pre> inside it is transparent.
      for (var el = pre, depth = 0; el && el.nodeType === 1 && depth < 5 && !bg && !has(el, 'td-content'); el = el.parentNode, depth += 1) {
        var painted = styleOf(el);
        bg = painted ? color(painted.backgroundColor) : '';
      }
      var holder = find(pre, function (kid) { return tagOf(kid) === 'CODE'; });
      var lang = holder ? (attr(holder, 'data-lang') || '') : '';
      return [{
        t: 'pre', title: title || '', lang: /^[\w+#.-]+$/.test(lang) ? lang : '', toks: tokens,
        bg: bg, fg: surface ? color(surface.color) : ''
      }];
    }

    function shell(node) {
      // Chroma's table layout holds one <pre> of line numbers and one of code.
      var pres = findAll(node, function (el) {
        return tagOf(el) === 'PRE' && !find(el, function (kid) { return has(kid, 'lnt'); });
      });
      var pre = pres[pres.length - 1];
      if (!pre) return [{ t: 'group', kids: kidsOf(node) }];
      if (!inRange(pre)) return [];
      var name = find(node, function (el) { return has(el, 'td-code__filename'); });
      var block = code(pre, name && inRange(name) ? textOf(name).trim() : '');
      if (block.length && name) {
        var header = styleOf(name.parentNode);
        var label = styleOf(name);
        block[0].titleBg = header ? color(header.backgroundColor) : '';
        block[0].titleFg = label ? color(label.color) : '';
      }
      return block;
    }

    function callout(node) {
      var title = [];
      var body = [];
      var kids = node.childNodes || [];
      for (var i = 0; i < kids.length; i += 1) {
        var kid = kids[i];
        if (kid.nodeType === 1 && has(kid, 'td-callout__title')) {
          if (inRange(kid) && !unseen(kid)) title = kidsOf(kid);
        } else if (tagOf(node) !== 'DETAILS' || node.hasAttribute('open')) {
          body.push.apply(body, walk(kid));
        }
      }
      var style = styleOf(node);
      var tone = style && style.getPropertyValue ? color(style.getPropertyValue('--td-callout-accent')) : '';
      return [{ t: 'callout', tone: tone, title: title, kids: body }];
    }

    // The date and the tag chips; the `, ` separators between them are plain
    // text for the clipboard's text/plain and are drawn here as spacing.
    function updateMeta(node) {
      var items = [];
      var kids = node.childNodes || [];
      for (var i = 0; i < kids.length; i += 1) {
        var kid = kids[i];
        if (kid.nodeType !== 1 || !inRange(kid) || isChrome(kid) || unseen(kid)) continue;
        var time = tagOf(kid) === 'TIME';
        if (!time && !has(kid, 'td-update-tag')) continue;
        var text = treeText(kidsOf(kid)).trim();
        if (!text) continue;
        items.push({ kind: time ? 'time' : 'tag', v: text });
      }
      return items.length ? [{ t: 'update-meta', items: items }] : [];
    }

    function cell(node, tag) {
      var style = styleOf(node);
      var align = (style && style.textAlign) || attr(node, 'align') || '';
      var span = function (name) {
        var n = parseInt(attr(node, name), 10);
        return n > 1 && n < 1000 ? n : 0;
      };
      return [{
        t: 'cell', head: tag === 'TH', kids: kidsOf(node),
        align: /^(center|right|end)$/.test(align) ? align : '',
        colspan: span('colspan'), rowspan: span('rowspan')
      }];
    }

    function walk(node) {
      if (!inRange(node)) return [];
      if (node.nodeType === 3) {
        var text = slice(node);
        return text ? [{ t: 'text', v: text }] : [];
      }
      if (node.nodeType !== 1) return [];
      var tag = tagOf(node);
      // The Image Zoom runtime wraps a picture in a button; the picture is
      // still the article's. Media print URLs sit hidden beside screen players
      // and carry the recording link into copied rich text, matching print.
      if (tag === 'BUTTON' && has(node, 'td-image-zoom__trigger')) return unseen(node) ? [] : kidsOf(node);
      if (tag === 'P' && has(node, 'td-media__url')) {
        if (node.parentNode && find(node.parentNode, function (el) { return has(el, 'td-media-card'); })) return [];
        return [{ t: 'p', kids: kidsOf(node) }];
      }
      if (DROP.test(tag) || isChrome(node) || unseen(node)) return [];
      if (has(node, 'katex-display')) return math(node, true);
      if (tag === 'MATH' || has(node, 'katex')) return math(node, attr(node, 'display') === 'block');
      if (has(node, 'td-code') || has(node, 'lntable') || (tag === 'DIV' && has(node, 'highlight'))) return shell(node);
      if (has(node, 'td-callout')) return callout(node);
      if (has(node, 'td-update-meta')) return updateMeta(node);
      if (/^H[1-6]$/.test(tag)) return [{ t: 'h', level: +tag.charAt(1), update: has(node, 'update'), kids: kidsOf(node) }];
      switch (tag) {
        case 'P': return [{ t: 'p', lead: has(node, 'lead'), kids: kidsOf(node) }];
        case 'BR': return [{ t: 'br' }];
        case 'HR': return [{ t: 'hr' }];
        case 'PRE': return code(node, '');
        case 'BLOCKQUOTE': return [{ t: 'quote', kids: kidsOf(node) }];
        case 'UL': return [{ t: 'list', kids: kidsOf(node) }];
        case 'OL': return [{ t: 'list', ordered: true, start: parseInt(attr(node, 'start'), 10) || 0, kids: kidsOf(node) }];
        case 'LI': return [{ t: 'li', kids: kidsOf(node) }];
        case 'TABLE': return [{ t: 'table', kids: kidsOf(node) }];
        case 'TR': return [{ t: 'row', kids: kidsOf(node) }];
        case 'TH': case 'TD': return cell(node, tag);
        case 'CAPTION': case 'FIGCAPTION': return [{ t: 'caption', kids: kidsOf(node) }];
        case 'FIGURE': return [{ t: 'figure', kids: kidsOf(node) }];
        case 'DT': return [{ t: 'p', bold: true, kids: kidsOf(node) }];
        case 'SUMMARY': return [{ t: 'p', bold: true, kids: kidsOf(node) }];
        case 'DETAILS': {
          var parts = [];
          var kids = node.childNodes || [];
          for (var i = 0; i < kids.length; i += 1) {
            if (node.hasAttribute('open') || (kids[i].nodeType === 1 && tagOf(kids[i]) === 'SUMMARY'))
              parts.push.apply(parts, walk(kids[i]));
          }
          return [{ t: 'group', kids: parts }];
        }
        case 'A': {
          var inner = kidsOf(node);
          var href = String(node.href || '');
          if (!/^(https?:|mailto:|tel:)/i.test(href) || inner.some(function (n) { return !INLINE[n.t]; }))
            return inner;
          return [{ t: 'a', href: href, kids: inner }];
        }
        case 'IMG': {
          // The authored source, not the rendition this viewport happened to pick.
          var src = String(node.src || node.currentSrc || '');
          if (!/^(https?:|data:image\/)/i.test(src)) return [];
          return [{ t: 'img', src: src, alt: attr(node, 'alt') || '' }];
        }
        case 'INPUT':
          return attr(node, 'type') === 'checkbox' ? [{ t: 'text', v: node.checked ? '☑ ' : '☐ ' }] : [];
        case 'STRONG': case 'B': return [{ t: 'strong', kids: kidsOf(node) }];
        case 'EM': case 'VAR': case 'CITE': case 'DFN': return [{ t: 'em', kids: kidsOf(node) }];
        // An <i> is either emphasis or an icon font glyph with no text of its own.
        case 'I': return /(^|\s)fa-/.test(attr(node, 'class') || '') ? [] : [{ t: 'em', kids: kidsOf(node) }];
        case 'DEL': case 'S': case 'STRIKE': return [{ t: 'del', kids: kidsOf(node) }];
        case 'U': case 'INS': return [{ t: 'u', kids: kidsOf(node) }];
        case 'MARK': return [{ t: 'mark', kids: kidsOf(node) }];
        case 'SUB': return [{ t: 'sub', kids: kidsOf(node) }];
        case 'SUP': return [{ t: 'sup', kids: kidsOf(node) }];
        case 'KBD': return [{ t: 'kbd', kids: kidsOf(node) }];
        case 'CODE': case 'SAMP': case 'TT': return [{ t: 'code', kids: [{ t: 'text', v: treeText(kidsOf(node)) }] }];
      }
      if (BLOCK.test(tag)) return [{ t: 'group', lead: has(node, 'lead'), kids: kidsOf(node) }];
      return kidsOf(node);
    }

    return { walk: walk, code: code };
  }

  function treeText(nodes) {
    return nodes.map(function (n) { return n.t === 'text' ? n.v : treeText(n.kids || []); }).join('');
  }

  function blank(nodes) {
    for (var i = 0; i < nodes.length; i += 1) {
      var n = nodes[i];
      if (n.t === 'text') { if (SPACE.test(n.v)) return false; continue; }
      if (n.t === 'br') continue;
      if (n.t === 'img' || n.t === 'hr' || n.t === 'math' || n.t === 'pre' || n.t === 'cell' || (n.t === 'update-meta' && n.items && n.items.length)) return false;
      if (!blank(n.kids || [])) return false;
    }
    return true;
  }

  /** A range that ends at the top of the next block still touches that
   *  block. Drop whatever the selection left empty. */
  function prune(nodes) {
    var out = [];
    for (var i = 0; i < nodes.length; i += 1) {
      var n = nodes[i];
      if (n.kids) n.kids = prune(n.kids);
      if (n.t === 'callout') n.title = prune(n.title);
      if (INLINE[n.t] || n.t === 'hr' || n.t === 'cell') { out.push(n); continue; }
      if (n.t === 'callout' ? blank(n.kids) && blank(n.title) : blank([n])) continue;
      out.push(n);
    }
    return out;
  }

  // ---- 2. The tree as HTML ----------------------------------------------

  function wide(unit) {
    // Han, kana, CJK punctuation and fullwidth forms. Hangul separates words
    // with spaces and stays out.
    return /[\u2e80-\u312f\u3190-\u9fff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uff60\uffe0-\uffe6\ud840-\ud87f\udc00-\udfff]/.test(unit);
  }

  function firstChar(nodes) {
    for (var i = 0; i < nodes.length; i += 1) {
      var n = nodes[i];
      if (n.t === 'text') {
        var m = SPACE.exec(n.v);
        if (m) return m[0];
      } else if (n.t === 'br' || n.t === 'img' || n.t === 'math') {
        return 'x';
      } else {
        var c = firstChar(n.kids || []);
        if (c) return c;
      }
    }
    return '';
  }

  function renderer(skin, plain) {
    var start = skin.rtl ? 'right' : 'left';
    var end = skin.rtl ? 'left' : 'right';
    var corner = skin.radius + 'px';
    var chip = Math.min(4, skin.radius) + 'px';
    var edge = skin.rtl ? corner + ' 0 0 ' + corner : '0 ' + corner + ' ' + corner + ' 0';
    var first = true;

    function css(style) { return plain || !style ? '' : ' style="' + escAttr(style) + '"'; }

    // The first block of the fragment starts flush; every later one keeps its
    // own space above.
    function top(px) {
      var value = first ? 0 : px;
      first = false;
      return value;
    }

    function below(ctx) { return ctx.tight ? 8 : 16; }

    /** Inline text follows CSS white-space collapsing, plus the one rule
     *  browsers still skip: a source line break between two wide characters
     *  is not a space. */
    function inline(nodes) {
      var out = '';
      var last = '';
      var pending = 0;
      function gap(next) {
        if (pending && last && next && !(pending === 2 && wide(last) && wide(next))) out += ' ';
        pending = 0;
      }
      function wrap(tag, style, node, extra) {
        var lead = firstChar(node.kids || []);
        if (!lead) return;
        gap(lead);
        out += '<' + tag + (extra || '') + css(style) + '>';
        run(node.kids);
        out += '</' + tag + '>';
      }
      function atom(html) { gap('x'); out += html; last = 'x'; }
      function run(list) {
        for (var i = 0; i < list.length; i += 1) {
          var n = list[i];
          switch (n.t) {
            case 'text': {
              var re = /([ \t\n\r\f]+)|([^ \t\n\r\f]+)/g;
              var m;
              while ((m = re.exec(n.v))) {
                if (m[1]) { pending = Math.max(pending, /[\n\r]/.test(m[1]) ? 2 : 1); continue; }
                gap(m[2].charAt(0));
                out += esc(m[2]);
                last = m[2].charAt(m[2].length - 1);
              }
              break;
            }
            case 'br': out += '<br>'; pending = 0; last = ''; break;
            case 'a': wrap('a', 'color:' + skin.link + ';text-decoration:underline;', n, ' href="' + escAttr(n.href) + '"'); break;
            case 'strong': wrap('strong', 'font-weight:700;color:' + skin.strong + ';', n); break;
            case 'em': wrap('em', 'font-style:italic;', n); break;
            case 'del': wrap('del', 'text-decoration:line-through;color:' + skin.muted + ';', n); break;
            case 'u': wrap('u', '', n); break;
            case 'mark': wrap('mark', 'padding:0 2px;background:#fff3bf;color:inherit;', n); break;
            case 'sub': wrap('sub', '', n); break;
            case 'sup': wrap('sup', '', n); break;
            case 'kbd':
              wrap('kbd', 'padding:1px 6px;border:1px solid ' + skin.tableLine + ';border-bottom-width:2px;border-radius:' + chip +
                ';background:#ffffff;color:' + skin.strong + ';font-family:' + MONO + ';font-size:0.85em;', n);
              break;
            case 'code': {
              var text = treeText(n.kids || []);
              if (SPACE.test(text)) atom('<code' + css('padding:2px 5px;border-radius:' + chip + ';background:' + skin.headerBg + ';color:' +
                skin.strong + ';font-family:' + MONO + ';font-size:0.9em;') + '>' + esc(text) + '</code>');
              break;
            }
            case 'img':
              atom('<img src="' + escAttr(n.src) + '" alt="' + escAttr(n.alt) + '"' + css('max-width:100%;height:auto;') + '>');
              break;
            case 'math': atom(esc('$' + n.v + '$')); break;
            default: if (n.kids) run(n.kids);
          }
        }
      }
      run(nodes);
      return out;
    }

    function heading(n, hasUpdateMeta) {
      var i = n.level - 1;
      var above = top([0, 36, 28, 24, 20, 20][i]);
      var style = 'margin:' + above + 'px 0 ' + (hasUpdateMeta ? 6 : [20, 16, 12, 10, 8, 8][i]) + 'px;';
      if (n.update) {
        if (above > 0) style += 'padding:16px 0 0;border-top:1px solid ' + (skin.headingRule === 'over' ? skin.strong : skin.line) + ';';
      } else {
        if (n.level === 2 && skin.headingRule === 'under') style += 'padding:0 0 8px;border-bottom:1px solid ' + skin.line + ';';
        if (n.level === 2 && skin.headingRule === 'over') style += 'padding:12px 0 0;border-top:1px solid ' + skin.strong + ';';
      }
      style += 'font-size:' + [26, 21, 18, 16, 15, 15][i] + 'px;line-height:' + (n.level < 3 ? 1.35 : 1.5) + ';font-weight:700;color:' +
        (n.level > 4 ? skin.meta : skin.strong) + ';';
      if (skin.headingFont) style += 'font-family:' + skin.headingFont + ';';
      var body = inline(n.kids);
      return body ? '<h' + n.level + css(style) + '>' + body + '</h' + n.level + '>' : '';
    }

    function paragraph(kids, ctx, flags) {
      var body = inline(kids);
      if (!body) return '';
      var style = 'margin:' + top(0) + 'px 0 ' + below(ctx) + 'px;';
      if (flags.lead) style += 'font-size:17px;line-height:1.7;color:' + skin.meta + ';';
      else style += 'font-size:' + (ctx.size || 16) + 'px;line-height:1.75;color:' + (ctx.ink || skin.ink) + ';';
      if (flags.bold) style += 'font-weight:700;';
      var solid = kids.filter(function (k) { return !(k.t === 'text' && !SPACE.test(k.v)); });
      if (solid.length === 1 && solid[0].t === 'img') style += 'text-align:center;';
      return '<p' + css(style) + '>' + body + '</p>';
    }

    function codeBlock(n, ctx) {
      // A dark code surface travels as it is; a light one takes the paper tint.
      var dark = !!n.bg && luminance(n.bg) < 0.18;
      var bg = dark ? n.bg : skin.codeBg;
      var fg = dark ? (n.fg || '#e6e6e6') : skin.strong;
      var border = dark ? bg : skin.line;
      var text = '';
      var open = '';
      n.toks.forEach(function (tok, index) {
        var value = index === n.toks.length - 1 ? tok.v.replace(/\n+$/, '') : tok.v;
        if (!value) return;
        var style = (tok.c && tok.c !== fg ? 'color:' + tok.c + ';' : '') + (tok.b ? 'font-weight:700;' : '') + (tok.i ? 'font-style:italic;' : '');
        // Whitespace has no ink: it rides in whichever span is open.
        if (!SPACE.test(value)) style = open;
        if (style !== open) {
          if (open) text += '</span>';
          if (style) text += '<span style="' + escAttr(style) + '">';
          open = style;
        }
        text += esc(value);
      });
      if (open) text += '</span>';
      if (!SPACE.test(text)) return '';
      var out = '';
      var above = top(0);
      if (n.title) {
        out += '<p' + css('margin:' + above + 'px 0 0;padding:6px 16px;border:1px solid ' + border + ';border-bottom:0;border-radius:' +
          corner + ' ' + corner + ' 0 0;background:' + (dark ? (n.titleBg || bg) : skin.headerBg) + ';color:' +
          (dark ? (n.titleFg || fg) : skin.meta) + ';font-family:' + MONO + ';font-size:12.5px;line-height:1.6;') + '>' + esc(n.title) + '</p>';
      }
      return out + '<pre' + css('margin:' + (n.title ? 0 : above) + 'px 0 ' + below(ctx) + 'px;padding:14px 16px;border:1px solid ' + border +
        ';border-radius:' + (n.title ? '0 0 ' + corner + ' ' + corner : corner) + ';background:' + bg + ';color:' + fg + ';font-family:' + MONO +
        ';font-size:13.5px;line-height:1.6;white-space:pre;overflow-x:auto;tab-size:4;text-align:left;') + '><code' +
        (n.lang ? ' class="language-' + n.lang + '"' : '') + css('font-family:inherit;') + '>' + text + '</code></pre>';
    }

    /** Quotes and callouts share one box: a rule on the reading edge and a
     *  quiet ground. Its blocks sit tight, and the bottom padding is short by
     *  the margin the last of them still carries. */
    function aside(n, ctx, tone, title) {
      var above = top(0);
      var body = '';
      if (title) body += '<p' + css('margin:0 0 6px;font-size:15px;line-height:1.6;font-weight:700;color:' + skin.strong + ';') + '>' + title + '</p>';
      body += blocks(n.kids, { ink: skin.quoteInk, tight: true });
      if (!body) return '';
      return '<blockquote' + css('margin:' + above + 'px 0 ' + below(ctx) + 'px;padding:12px 16px 4px;border-' + start + ':3px solid ' + tone +
        ';border-radius:' + edge + ';background:' + skin.quoteBg + ';color:' + skin.quoteInk + ';') + '>' + body + '</blockquote>';
    }

    function list(n, ctx) {
      var tag = n.ordered ? 'ol' : 'ul';
      var above = top(0);
      var items = '';
      var inner = { ink: ctx.ink, size: ctx.size, tight: true, nested: true };
      n.kids.forEach(function (item) {
        if (item.t !== 'li') return;
        var kids = item.kids;
        // A loose item is one paragraph in a wrapper; editors space that badly.
        var solid = kids.filter(function (k) { return !(k.t === 'text' && !SPACE.test(k.v)); });
        if (solid.length === 1 && solid[0].t === 'p') kids = solid[0].kids;
        var body = '';
        var run = [];
        kids.forEach(function (kid) {
          if (INLINE[kid.t]) { run.push(kid); return; }
          body += inline(run) + blocks([kid], inner);
          run = [];
        });
        body += inline(run);
        if (body) items += '<li' + css('margin:0 0 6px;') + '>' + body + '</li>';
      });
      if (!items) return '';
      return '<' + tag + (n.start > 1 ? ' start="' + n.start + '"' : '') + css('margin:' + (ctx.nested ? '6px 0 0' : above + 'px 0 ' + below(ctx) + 'px') +
        ';padding-' + start + ':28px;font-size:' + (ctx.size || 16) + 'px;line-height:1.75;color:' + (ctx.ink || skin.ink) + ';') + '>' + items + '</' + tag + '>';
    }

    function table(n, ctx) {
      var above = top(0);
      var rows = '';
      var caption = '';
      (function each(kids) {
        kids.forEach(function (row) {
          if (row.t === 'group') { each(row.kids); return; }
          if (row.t === 'caption') { caption = inline(row.kids); return; }
          if (row.t !== 'row') return;
          var cells = '';
          row.kids.forEach(function (c) {
            if (c.t !== 'cell') return;
            var tag = c.head ? 'th' : 'td';
            var style = 'padding:8px 12px;border:1px solid ' + skin.tableLine + ';text-align:' + (c.align === 'end' ? end : c.align || start) + ';vertical-align:top;';
            if (c.head) style += 'background:' + skin.headerBg + ';color:' + skin.strong + ';font-weight:700;';
            var body = c.kids.every(function (k) { return INLINE[k.t]; }) ? inline(c.kids) : blocks(c.kids, { tight: true, size: 14.5 });
            cells += '<' + tag + (c.colspan ? ' colspan="' + c.colspan + '"' : '') + (c.rowspan ? ' rowspan="' + c.rowspan + '"' : '') +
              css(style) + '>' + body + '</' + tag + '>';
          });
          if (cells) rows += '<tr>' + cells + '</tr>';
        });
      })(n.kids);
      if (!rows) return '';
      return '<table' + css('margin:' + above + 'px 0 ' + below(ctx) + 'px;border-collapse:collapse;font-size:14.5px;line-height:1.6;color:' + skin.ink + ';') + '>' +
        (caption ? '<caption' + css('padding:0 0 8px;font-size:13.5px;color:' + skin.muted + ';text-align:' + start + ';') + '>' + caption + '</caption>' : '') +
        '<tbody>' + rows + '</tbody></table>';
    }

    function figure(n, ctx) {
      var above = top(0);
      var body = '';
      n.kids.forEach(function (kid) {
        if (kid.t === 'caption') {
          var text = inline(kid.kids);
          if (text) body += '<figcaption' + css('margin:8px 0 0;font-size:13.5px;line-height:1.6;color:' + skin.muted + ';') + '>' + text + '</figcaption>';
        } else if (INLINE[kid.t]) {
          body += inline([kid]);
        } else {
          body += blocks([kid], { tight: true, ink: ctx.ink });
        }
      });
      return body ? '<figure' + css('margin:' + above + 'px 0 ' + below(ctx) + 'px;text-align:center;') + '>' + body + '</figure>' : '';
    }

    function renderUpdateMeta(n) {
      var parts = n.items.map(function (item) {
        if (item.kind === 'time') {
          return '<span' + css('font-weight:600;color:' + skin.strong + ';') + '>' + esc(item.v) + '</span>';
        }
        return '<span' + css('padding:1px 6px;border:1px solid ' + skin.line + ';border-radius:' + chip +
          ';color:' + skin.meta + ';font-size:12px;font-weight:600;') + '>' + esc(item.v) + '</span>';
      });
      return '<p' + css('margin:' + top(0) + 'px 0 12px;font-size:13px;line-height:1.6;color:' + skin.meta + ';') + '>' +
        parts.join(' ') + '</p>';
    }

    function nextBlock(nodes, index) {
      for (var j = index + 1; j < nodes.length; j += 1) {
        if (nodes[j].t === 'text' && !SPACE.test(nodes[j].v)) continue;
        return nodes[j];
      }
      return null;
    }

    function blocks(nodes, ctx) {
      var out = '';
      var run = [];
      function flush() {
        if (run.length) out += paragraph(run, ctx, {});
        run = [];
      }
      nodes.forEach(function (n, index) {
        if (INLINE[n.t] && !(n.t === 'math' && n.block)) { run.push(n); return; }
        flush();
        switch (n.t) {
          case 'h': {
            var next = n.update ? nextBlock(nodes, index) : null;
            out += heading(n, !!(next && next.t === 'update-meta'));
            break;
          }
          case 'p': out += paragraph(n.kids, ctx, n); break;
          case 'math': out += paragraph([{ t: 'text', v: '$$' + n.v + '$$' }], ctx, {}); break;
          case 'hr': out += '<hr' + css('margin:' + top(28) + 'px 0 28px;border:0;border-top:1px solid ' + skin.line + ';height:0;') + '>'; break;
          case 'pre': out += codeBlock(n, ctx); break;
          case 'quote': out += aside(n, ctx, skin.quoteLine, ''); break;
          case 'callout': out += aside(n, ctx, n.tone || skin.quoteLine, inline(n.title)); break;
          case 'update-meta': out += renderUpdateMeta(n); break;
          case 'list': out += list(n, ctx); break;
          case 'li': out += list({ kids: [n] }, ctx); break;
          case 'table': out += table(n, ctx); break;
          case 'row': out += table({ kids: [n] }, ctx); break;
          case 'cell': out += table({ kids: [{ t: 'row', kids: [n] }] }, ctx); break;
          case 'figure': out += figure(n, ctx); break;
          case 'caption': out += paragraph(n.kids, { ink: skin.muted, size: 13.5, tight: ctx.tight }, {}); break;
          case 'group':
            if (n.lead && n.kids.every(function (k) { return INLINE[k.t]; })) out += paragraph(n.kids, ctx, { lead: true });
            else out += blocks(n.kids, ctx);
            break;
        }
      });
      flush();
      return out;
    }

    return { blocks: function (nodes) { return blocks(nodes, {}); }, inline: inline };
  }

  /** A selection inside one line of prose is a phrase, not a document: it
   *  travels as bare semantic markup and takes the destination's style. */
  function phrase(nodes) {
    if (nodes.length !== 1) return null;
    var n = nodes[0];
    var flat = function (kids) { return kids.every(function (k) { return INLINE[k.t] && !(k.t === 'math' && k.block); }); };
    if ((n.t === 'p' || n.t === 'h' || n.t === 'cell' || n.t === 'caption' || n.t === 'group') && flat(n.kids)) return n.kids;
    if (n.t === 'update-meta') return [{ t: 'text', v: n.items.map(function (item) { return item.v; }).join(', ') }];
    if (n.t === 'list' && n.kids.length === 1 && n.kids[0].t === 'li' && flat(n.kids[0].kids)) return n.kids[0].kids;
    if (n.t === 'pre' && !n.title) {
      var text = n.toks.map(function (tok) { return tok.v; }).join('').replace(/\n+$/, '');
      if (!/\n/.test(text)) return [{ t: 'code', kids: [{ t: 'text', v: text }] }];
    }
    return null;
  }

  function render(nodes, skin) {
    var tree = prune(nodes);
    if (!tree.length) return '';
    var bare = phrase(tree);
    return bare ? renderer(skin, true).inline(bare) : renderer(skin, false).blocks(tree);
  }

  // ---- 3. The copy event ------------------------------------------------

  function closestTag(el, pattern, root) {
    for (var n = el; n && n !== root.parentNode; n = n.parentNode) {
      if (n.nodeType === 1 && pattern.test(tagOf(n))) return n;
      if (n === root) break;
    }
    return null;
  }

  /** The block the walk starts from: the smallest one that keeps the
   *  selection's structure (a row needs its table, an item its list). */
  function anchor(el, root) {
    var pre = closestTag(el, /^PRE$/, root);
    if (pre) return pre;
    var n = el;
    while (n !== root && !BLOCK.test(tagOf(n))) n = n.parentNode;
    var tag = tagOf(n);
    if (n === root) return n;
    if (/^(TR|THEAD|TBODY|TFOOT)$/.test(tag)) return closestTag(n, /^TABLE$/, root) || n;
    if (tag === 'LI') return n.parentNode;
    return n;
  }

  function typeset(range, doc, view) {
    var common = range.commonAncestorContainer;
    var el = common.nodeType === 1 ? common : common.parentNode;
    if (!el) return '';
    var roots = [];
    var home = el.closest ? el.closest('.td-content') : null;
    if (home) {
      for (var n = el; n && n !== home; n = n.parentNode) {
        if (n.nodeType === 1 && (DROP.test(tagOf(n)) || isChrome(n))) return '';
      }
      roots = [anchor(el, home)];
    } else {
      // The selection runs past the article (select all): keep the article.
      var all = doc.querySelectorAll('.td-content');
      for (var i = 0; i < all.length; i += 1) {
        if (range.intersectsNode(all[i]) && !(all[i].parentNode.closest && all[i].parentNode.closest('.td-content'))) roots.push(all[i]);
      }
    }
    if (!roots.length) return '';
    var root = doc.documentElement;
    var styleOf = function (node) { return node && node.nodeType === 1 ? view.getComputedStyle(node) : null; };
    var skin = readSkin(view.getComputedStyle(root), view.getComputedStyle(roots[0]).direction);
    var walker = collector(range, { styleOf: styleOf });
    var nodes = [];
    roots.forEach(function (start) { nodes.push.apply(nodes, walker.walk(start)); });
    return render(nodes, skin);
  }

  function onCopy(event) {
    try {
      var doc = global.document;
      if (event.defaultPrevented || !event.clipboardData) return;
      var selection = doc.getSelection();
      if (!selection || selection.isCollapsed || selection.rangeCount !== 1) return;
      var target = event.target && event.target.nodeType === 1 ? event.target : event.target && event.target.parentNode;
      if (target && target.closest && target.closest('input, textarea, [contenteditable]:not([contenteditable="false"])')) return;
      var html = typeset(selection.getRangeAt(0), doc, global);
      if (!html) return;
      var text = selection.toString();
      event.clipboardData.setData('text/html', html);
      event.clipboardData.setData('text/plain', text);
      event.preventDefault();
    } catch (error) {
      // The native copy proceeds.
    }
  }

  var api = { color: color, readSkin: readSkin, collector: collector, render: render, typeset: typeset };
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (global.document && typeof global.document.addEventListener === 'function') {
    global.OinkRichCopy = api;
    global.document.addEventListener('copy', onCopy);
  }
})(typeof window === 'object' ? window : globalThis);
