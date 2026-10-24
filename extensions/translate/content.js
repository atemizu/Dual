// Dual Page Translate, inside the page. Splits the page into paragraphs,
// sends them a few at a time (the ones on screen first) to be translated, and
// puts the translations in their place, keeping links and other formatting.
// Everything it changes is remembered, so that the original comes back as it
// was.
//
// A paragraph ("unit") is an element laid out as a block, with the text of
// its inline descendants. Inside it, inline elements such as links become
// <gN>…</gN> markers around their words, and things that are not words (an
// image, a nested block) become <xN/>. The same elements are put back around
// the translated words, so that links keep working.

(() => {
  'use strict';

  if (window.__dualTranslate) return;
  // Lives in the extension's own view of the page, which the page cannot see;
  // the checks read the paragraphs through it.
  window.__dualTranslate = {
    state: () => state(),
    units: () => [...units.values()].map((unit) => ({
      source: unit.source, state: unit.state, tries: unit.tries, applied: unit.applied,
      tag: unit.element.tagName, inReach: inReach(unit),
    })),
  };

  const JAPANESE_UI = chrome.i18n.getUILanguage().startsWith('ja');
  const T = JAPANESE_UI ? {
    names: {ja: '日本語', en: '英語'},
    loading: '翻訳モデルを読み込んでいます…',
    working: (target, done, total) => `${target}に訳しています… ${done} / ${total}`,
    finished: (target) => `${target}に訳しました`,
    finishedSoFar: (target) => `${target}に訳しました。続きはスクロールに合わせて訳します`,
    stopped: '翻訳を止めました',
    failed: '翻訳できませんでした。もう一度お試しください。',
    noModel: '翻訳モデルがまだありません。ツールバーの「ページ翻訳」から入れてください。',
    noHost: '翻訳に使うプログラムに接続できませんでした。',
    stuck: '翻訳に使うプログラムが応答しなくなりました。もう一度お試しください。',
    stop: '中止',
    restore: '原文に戻す',
    close: '閉じる',
  } : {
    names: {ja: 'Japanese', en: 'English'},
    loading: 'Loading the translation model…',
    working: (target, done, total) => `Translating into ${target}… ${done} / ${total}`,
    finished: (target) => `Translated into ${target}`,
    finishedSoFar: (target) => `Translated into ${target}. The rest follows as you scroll`,
    stopped: 'Translation stopped',
    failed: 'Could not translate. Please try again.',
    noModel: 'The translation model is not installed yet. Install it from Page Translate in the toolbar.',
    noHost: 'Could not reach the translation program.',
    stuck: 'The translation program stopped responding. Please try again.',
    stop: 'Stop',
    restore: 'Show original',
    close: 'Close',
  };

  // Left exactly as they are, words and all.
  const OPAQUE = new Set([
    'SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'TEXTAREA', 'INPUT', 'SELECT', 'OPTION', 'OPTGROUP',
    'CODE', 'PRE', 'KBD', 'SAMP', 'VAR', 'SVG', 'MATH', 'CANVAS', 'IFRAME', 'OBJECT', 'EMBED',
    'VIDEO', 'AUDIO', 'IMG', 'PICTURE', 'HEAD', 'TITLE', 'META', 'LINK', 'BR', 'WBR', 'HR', 'RT', 'RP',
  ]);

  // How many characters go to the model at once: enough for context, few
  // enough that the first words show up soon.
  const BATCH_CHARACTERS = {en: 1200, ja: 600};
  // What is on screen goes in small requests, translated side by side, so
  // that the screen fills quickly.
  const SCREEN_BATCH_CHARACTERS = {en: 600, ja: 300};
  // Requests kept free for paragraphs tried again, so that they do not wait
  // behind the others.
  const KEPT_FOR_RETRIES = 2;
  const BATCH_SEGMENTS = 20;
  // Only what is on screen or near it is translated, in screens: the rest as
  // it comes near, while scrolling.
  const REACH = 3;
  // A paragraph changed by the page itself is translated again, this often.
  const RETRANSLATE_LIMIT = 3;

  const JAPANESE = /[぀-ヿ㐀-鿿ｦ-ﾟ]/g;
  const LATIN = /[A-Za-z]/g;

  let session = null;
  let units = new Map();          // Element -> unit.
  let order = 0;
  let ours = new WeakSet();       // Text nodes this script made.
  let displays = new WeakMap();   // Element -> computed display, per scan.
  let applying = false;
  let port = null;
  const batches = new Map();      // Requests on their way, by id.
  let parallel = 1;               // How many the translator takes at once.
  let nextBatchId = 1;
  let overlay = null;

  // ------------------------------------------------------------------------
  // Reading the page

  function display(element) {
    let value = displays.get(element);
    if (value === undefined) {
      value = getComputedStyle(element).display;
      displays.set(element, value);
    }
    return value;
  }

  function isOpaque(element) {
    return OPAQUE.has(element.tagName) ||
        element.namespaceURI !== 'http://www.w3.org/1999/xhtml' ||
        element.getAttribute('translate') === 'no' ||
        element.classList.contains('notranslate') ||
        element.isContentEditable ||
        element === overlay?.host;
  }

  function isBlock(element) {
    const value = display(element);
    return value !== 'inline' && value !== 'contents' && value !== 'ruby';
  }

  function escapeText(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function unescapeText(text) {
    return text.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
        .replace(/&#39;/g, '\'').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&');
  }

  function plain(marked) {
    return unescapeText(marked.replace(/<\/?[gx]\d+\/?>/g, ''));
  }

  // The paragraph's text with markers, its marked elements and its embedded
  // nodes.
  function serialize(element) {
    const groups = [];
    const embedded = [];
    let text = '';
    const visit = (parent) => {
      for (const child of parent.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) {
          text += escapeText(child.data.replace(/\s+/g, ' '));
        } else if (child.nodeType === Node.ELEMENT_NODE) {
          // Things without letters, such as a note number "[5]", are kept as
          // they are, like pictures.
          if (isOpaque(child) || isBlock(child) || !/\p{L}/u.test(child.textContent)) {
            embedded.push(child);
            text += `<x${embedded.length}/>`;
          } else if (child.tagName === 'RUBY') {
            // Its reading is not part of the sentence; the base text is.
            for (const part of child.childNodes) {
              if (!(part.nodeType === Node.ELEMENT_NODE && (part.tagName === 'RT' || part.tagName === 'RP'))) {
                text += escapeText(part.textContent.replace(/\s+/g, ' '));
              }
            }
          } else {
            groups.push(child);
            const number = groups.length;
            text += `<g${number}>`;
            visit(child);
            text += `</g${number}>`;
          }
        }
      }
    };
    visit(element);
    return {text: text.trim(), groups, embedded};
  }

  function inSourceLanguage(text, source) {
    const japanese = (text.match(JAPANESE) || []).length;
    const latin = (text.match(LATIN) || []).length;
    return source === 'ja' ? japanese > 0 : latin >= 2 && japanese * 3 < latin;
  }

  function makeUnit(element) {
    const {text, groups, embedded} = serialize(element);
    if (!text || text.length > 6000 || !inSourceLanguage(plain(text), session.source)) {
      return null;
    }
    return {
      element, source: text, groups, embedded, state: 'pending', tries: 0, order: order++,
      saved: null, applied: null, retranslated: 0,
    };
  }

  // Finds the paragraphs in and under `root`.
  function scan(root) {
    if (!root || !root.isConnected) return;
    if (root.nodeType !== Node.ELEMENT_NODE) root = root.parentElement;
    while (root && root !== document.body && !isBlock(root)) root = root.parentElement;
    if (!root) return;
    for (let up = root; up; up = up.parentElement) {
      if (isOpaque(up)) return;
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, {
      acceptNode: (element) => isOpaque(element) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    for (let element = root; element; element = walker.nextNode()) {
      if (element !== document.body && !isBlock(element)) continue;
      const known = units.get(element);
      if (known) {
        if (known.state !== 'done') continue;
        // Changed by the page since it was translated: translate it again.
        const now = serialize(element).text;
        if (now === known.applied || known.retranslated >= RETRANSLATE_LIMIT) continue;
        const fresh = makeUnit(element);
        if (!fresh) continue;
        fresh.retranslated = known.retranslated + 1;
        units.set(element, fresh);
        continue;
      }
      const unit = makeUnit(element);
      if (unit) units.set(element, unit);
    }
  }

  // ------------------------------------------------------------------------
  // Putting translations in

  // Builds the translated paragraph. Returns false if the markers do not
  // match up, and the missing marked elements otherwise.
  function build(unit, translated) {
    const pieces = [];
    const stack = [{node: null, number: 0, children: pieces}];
    const usedGroups = new Set();
    const usedEmbedded = new Set();
    const marker = /<(\/?)([gx])(\d+)\s*(\/?)>/g;
    let at = 0;
    const addText = (text) => {
      if (!text) return;
      const node = document.createTextNode(unescapeText(text));
      ours.add(node);
      stack[stack.length - 1].children.push(node);
    };
    for (const match of translated.matchAll(marker)) {
      addText(translated.slice(at, match.index));
      at = match.index + match[0].length;
      const [, closing, kind, digits] = match;
      const number = Number(digits);
      if (kind === 'x') {
        const node = unit.embedded[number - 1];
        if (node && !usedEmbedded.has(number)) {
          usedEmbedded.add(number);
          stack[stack.length - 1].children.push(node);
        }
      } else if (!closing) {
        const node = unit.groups[number - 1];
        if (!node || usedGroups.has(number)) return false;
        usedGroups.add(number);
        stack.push({node, number, children: []});
      } else {
        const top = stack[stack.length - 1];
        if (top.number !== number) return false;
        stack.pop();
        stack[stack.length - 1].children.push(top);
      }
    }
    addText(translated.slice(at));
    if (stack.length !== 1) return false;
    const missing = unit.groups.filter((group, index) => !usedGroups.has(index + 1));
    const missingEmbedded = unit.embedded.filter((node, index) => !usedEmbedded.has(index + 1));
    return {pieces, missing, missingEmbedded};
  }

  function place(container, pieces) {
    const nodes = pieces.map((piece) => {
      if (piece instanceof Node) return piece;
      place(piece.node, piece.children);
      return piece.node;
    });
    container.replaceChildren(...nodes);
  }

  // How a translation went: 'done'; 'retry' (markers lost: try again on its
  // own, with plainer words); 'lookup' (markers lost again: the words of the
  // links are translated by themselves next, to find them in the
  // translation); or 'failed' (left as it was).
  function apply(unit, translated) {
    translated = translated.trim();
    if (!translated) return unit.tries ? 'failed' : 'retry';
    // Given back as it was (the model sometimes copies short headlines):
    // asked for again on its own; a second time it is taken as it comes,
    // being most likely a name.
    if (!unit.tries && stillInSource(unit.source, translated)) return 'retry';
    // A link holding all the words of a paragraph, its markers lost: the
    // translated words go back inside it, innermost link first.
    for (let number = unit.groups.length; number >= 1; number--) {
      if (!translated.includes(`<g${number}>`) && holdsAllWords(unit.source, number)) {
        translated = wrapWords(translated, number);
      }
    }
    let built = build(unit, translated);
    if (!built) {
      if (!unit.tries) return 'retry';
      // Markers in a muddle: keep the words, place the links afresh.
      translated = translated.replace(/<\/?g\d+>/g, '');
      built = build(unit, translated);
      if (!built) return 'failed';
    }
    const missing = unit.groups
        .map((group, index) => built.missing.includes(group) && /\S/.test(group.textContent) ? index + 1 : 0)
        .filter(Boolean);
    if (missing.length) {
      if (!unit.tries) return 'retry';
      unit.lookup = {translated, missing};
      return 'lookup';
    }
    put(unit, built);
    return 'done';
  }

  function words(marked) {
    return plain(marked).match(/\p{L}/gu) || [];
  }

  function stillInSource(source, translated) {
    const japanese = (text) => (plain(text).match(JAPANESE) || []).length;
    if (session.target === 'ja') {
      return japanese(translated) === 0 && (plain(source).match(/[A-Za-z]{3,}/g) || []).length >= 2;
    }
    return japanese(source) >= 2 && japanese(translated) >= japanese(source) / 2;
  }

  // Whether group |number| holds every letter of |source|.
  function holdsAllWords(source, number) {
    const inside = new RegExp(`<g${number}>[\\s\\S]*</g${number}>`);
    return inside.test(source) && words(source.replace(inside, '')).length === 0;
  }

  // Wraps the words of |text| in group |number|: everything but leading and
  // trailing spaces, punctuation and embedded items outside any group.
  function wrapWords(text, number) {
    const edge = /^(?:\s|<x\d+\/>|[^\p{L}\p{N}<])+/u;
    const lead = (text.match(edge) || [''])[0];
    const rest = text.slice(lead.length);
    const reversed = [...rest].reverse().join('');
    const tailEdge = /^(?:\s|>\/\d+x<|[^\p{L}\p{N}>])+/u;
    const tail = [...((reversed.match(tailEdge) || [''])[0])].reverse().join('');
    const middle = rest.slice(0, rest.length - tail.length);
    return middle ? `${lead}<g${number}>${middle}</g${number}>${tail}` : text;
  }

  // Where |phrase| is in |text| (any case), outside the markers, or -1.
  function findPhrase(text, phrase) {
    const lower = text.toLowerCase();
    const wanted = phrase.toLowerCase();
    for (let at = lower.indexOf(wanted); at >= 0; at = lower.indexOf(wanted, at + 1)) {
      const before = text.lastIndexOf('<', at);
      const inMarker = before >= 0 && text.indexOf('>', before) >= at && /^<\/?[gx]\d/.test(text.slice(before));
      const crosses = /<\/?[gx]\d+\/?>/.test(text.slice(at, at + wanted.length));
      if (!inMarker && !crosses) return at;
    }
    return -1;
  }

  // Puts the links whose markers were lost around their words, from the
  // words' own translations: the whole phrase if it is there, else its longest
  // word that is. A link is never dropped: if one cannot be placed, the
  // paragraph stays as it was.
  function placeLinks(unit, phrases) {
    let text = unit.lookup.translated;
    let placed = true;
    const letters = (number) => (unit.groups[number - 1].textContent.match(/[\p{L}\p{N}]/gu) || []).join('');
    // A link whose words are the same in both languages (a site's name, an
    // address) that the model left out goes back as it was, where it was:
    // inside the link around it, at the same end.
    unit.lookup.missing.forEach((number, index) => {
      if (text.includes(`<g${number}>`)) return;
      const original = escapeText(unit.groups[number - 1].textContent.replace(/\s+/g, ' ').trim());
      const phrase = (phrases[index] || '').trim();
      if (phrase.toLowerCase() !== original.toLowerCase() || findPhrase(text, original) >= 0) return;
      const markup = unit.source.match(new RegExp(`<g${number}>[\\s\\S]*?</g${number}>`))[0];
      const parent = unit.groups.findIndex((group, at) => at + 1 < number && group.contains(unit.groups[number - 1]) &&
          text.includes(`</g${at + 1}>`) && !unit.groups.some((other, k) => k > at && k + 1 < number &&
          group.contains(other) && other.contains(unit.groups[number - 1]) && text.includes(`</g${k + 1}>`)));
      const atStart = unit.source.indexOf(markup) <= (parent >= 0 ? unit.source.indexOf(`<g${parent + 1}>`) + `<g${parent + 1}>`.length : 0);
      if (parent < 0) {
        text = atStart ? markup + text : text + markup;
      } else if (atStart) {
        const open = text.indexOf(`<g${parent + 1}>`) + `<g${parent + 1}>`.length;
        text = text.slice(0, open) + markup + text.slice(open);
      } else {
        const close = text.indexOf(`</g${parent + 1}>`);
        text = text.slice(0, close) + markup + text.slice(close);
      }
    });
    // Innermost first, so that a link around the same words as one inside it
    // can go just outside that one.
    const order = unit.lookup.missing.map((number, index) => [number, index]).sort((a, b) => b[0] - a[0]);
    order.forEach(([number, index]) => {
      if (text.includes(`<g${number}>`)) return;
      const inner = unit.groups.findIndex((group, at) => at + 1 > number && unit.groups[number - 1].contains(group) &&
          letters(at + 1) === letters(number) && text.includes(`<g${at + 1}>`));
      if (inner >= 0) {
        const open = text.indexOf(`<g${inner + 1}>`);
        const close = text.indexOf(`</g${inner + 1}>`) + `</g${inner + 1}>`.length;
        text = `${text.slice(0, open)}<g${number}>${text.slice(open, close)}</g${number}>${text.slice(close)}`;
        return;
      }
      const phrase = (phrases[index] || '').trim();
      const shortest = session.target === 'ja' ? 2 : 3;
      const tries = [phrase, ...phrase.split(/[\s\p{P}]+/u).filter((word) => word.length >= shortest)
          .sort((a, b) => b.length - a.length)].filter(Boolean);
      for (const words of tries) {
        const at = findPhrase(text, words);
        if (at >= 0) {
          text = `${text.slice(0, at)}<g${number}>${text.slice(at, at + words.length)}</g${number}>` +
              text.slice(at + words.length);
          return;
        }
      }
      const rest = wrapRest(unit, text, number);
      if (rest) text = rest;
      else placed = false;
    });
    unit.lookup = null;
    if (!placed) return 'failed';
    const built = build(unit, text);
    if (!built || built.missing.some((group) => /\S/.test(group.textContent))) return 'failed';
    put(unit, built);
    return 'done';
  }

  // For a link that, inside the link around it (or the paragraph), holds all
  // the words but those of other links already in place: wraps the words
  // there that are outside those links. Null if that is not the case.
  function wrapRest(unit, text, number) {
    const group = unit.groups[number - 1];
    const present = (k) => text.includes(`<g${k}>`) && text.includes(`</g${k}>`);
    const span = (marked, k) => marked.match(new RegExp(`<g${k}>[\\s\\S]*?</g${k}>`));
    // The nearest link around it that is in place, if any.
    let parent = 0;
    unit.groups.forEach((other, at) => {
      if (at + 1 !== number && other.contains(group) && present(at + 1) &&
          (!parent || unit.groups[parent - 1].contains(other))) parent = at + 1;
    });
    const scope = (marked) => parent ? span(marked, parent)[0].replace(/^<g\d+>|<\/g\d+>$/g, '') : marked;
    // Its neighbours in that scope that are in place.
    const neighbours = unit.groups.map((other, at) => at + 1).filter((k) => k !== number && k !== parent &&
        present(k) && !unit.groups[k - 1].contains(group) && !group.contains(unit.groups[k - 1]) &&
        (!parent || unit.groups[parent - 1].contains(unit.groups[k - 1])));
    const outside = (marked) => neighbours.reduce((rest, k) => rest.replace(span(rest, k)?.[0] || '', ' '), marked);
    let sourceScope = parent ? span(unit.source, parent)?.[0] : unit.source;
    if (!sourceScope) return null;
    sourceScope = outside(sourceScope).replace(new RegExp(`<g${number}>[\\s\\S]*?</g${number}>`), ' ');
    if (words(sourceScope).length) return null;
    // In the translation: the stretch with letters outside the neighbours must be one piece.
    const inner = scope(text);
    const pieces = neighbours.reduce((list, k) => list.flatMap((part) => {
      const found = span(part, k);
      return found ? [part.slice(0, found.index), found[0], part.slice(found.index + found[0].length)] : [part];
    }), [inner]);
    const worded = pieces.filter((part) => !/^<g\d+>/.test(part) && words(part).length);
    if (worded.length !== 1) return null;
    const wrapped = inner.replace(worded[0], wrapWords(worded[0], number));
    return parent ? text.replace(inner, wrapped) : wrapped;
  }

  function put(unit, built) {
    // Embedded things the model left out go where they were: at the start or
    // the end.
    for (const node of built.missingEmbedded) {
      const number = unit.embedded.indexOf(node) + 1;
      if (unit.source.startsWith(`<x${number}/>`)) built.pieces.unshift(node);
      else built.pieces.push(node);
    }

    if (!unit.saved) {
      unit.saved = [unit.element, ...unit.groups].map((container) => [container, [...container.childNodes]]);
    }
    applying = true;
    place(unit.element, built.pieces);
    observer.takeRecords();
    applying = false;
    unit.applied = serialize(unit.element).text;
  }

  function restore(unit) {
    if (!unit.saved) return;
    for (const [container, nodes] of unit.saved) {
      container.replaceChildren(...nodes);
    }
    unit.saved = null;
  }

  // ------------------------------------------------------------------------
  // Talking to the translator

  function connect() {
    if (port) return port;
    port = chrome.runtime.connect({name: 'page'});
    port.onMessage.addListener(onReply);
    port.onDisconnect.addListener(() => {
      port = null;
      if (batches.size) {
        for (const batch of batches.values()) {
          for (const unit of batch.units) if (unit.state === 'sent') unit.state = unit.lookup ? 'lookup' : 'pending';
        }
        batches.clear();
        if (session?.phase === 'translating') setTimeout(pump, 1000);
      }
    });
    return port;
  }

  // How far a paragraph is from what is on screen, in pixels: 0 on screen,
  // Infinity if it is not shown at all.
  function distance(unit) {
    // Menus and the like that are there but not shown wait until they are.
    if (!unit.element.checkVisibility({opacityProperty: true, visibilityProperty: true})) return Infinity;
    const box = unit.element.getBoundingClientRect();
    if (box.width === 0 && box.height === 0) return Infinity;
    if (box.bottom >= 0 && box.top <= innerHeight) return Math.max(0, box.top) / innerHeight;
    if (box.top > innerHeight) return box.top;
    return innerHeight - box.bottom;
  }

  function inReach(unit) {
    return distance(unit) < REACH * innerHeight;
  }

  // The paragraphs for the next request: from the nearest, the ones after it,
  // up to a size. A paragraph tried before goes alone.
  function nextBatch(retriesOnly) {
    const pending = [...units.values()]
        .filter((unit) => (unit.state === 'pending' || unit.state === 'lookup') && unit.element.isConnected &&
                          inReach(unit) && (!retriesOnly || unit.tries > 0))
        .sort((a, b) => a.order - b.order);
    if (!pending.length) return null;
    let first = 0;
    let best = Infinity;
    pending.forEach((unit, index) => {
      const value = distance(unit);
      if (value < best) {
        best = value;
        first = index;
      }
    });
    const chosen = [pending[first]];
    if (pending[first].state === 'pending' && pending[first].tries === 0) {
      let characters = pending[first].source.length;
      const budget = (best < 1 ? SCREEN_BATCH_CHARACTERS : BATCH_CHARACTERS)[session.source];
      for (const unit of pending.slice(first + 1)) {
        if (unit.state !== 'pending' || unit.tries || chosen.length >= BATCH_SEGMENTS) break;
        if (characters + unit.source.length > budget) break;
        characters += unit.source.length;
        chosen.push(unit);
      }
    }
    return chosen;
  }

  // Keeps the translator busy: as many requests on their way as it takes at
  // once, the nearest paragraphs first.
  function pump() {
    if (!session) return;
    const before = session.phase;
    if (before === 'done') session.phase = 'translating';
    if (session.phase !== 'translating') return;
    while (batches.size < parallel) {
      const regular = [...batches.values()].filter((batch) => batch.units.every((unit) => unit.tries === 0)).length;
      const chosen = nextBatch(parallel > KEPT_FOR_RETRIES && regular >= parallel - KEPT_FOR_RETRIES);
      if (!chosen) break;
      send(chosen);
    }
    if (!batches.size) {
      session.phase = 'done';
      if (before !== 'done') show();
      // From now on the note shows only what the user asks for: scrolling
      // further translates quietly.
      session.quiet = true;
    }
  }

  function send(chosen) {
    const lookup = chosen[0].state === 'lookup' ? chosen[0] : null;
    for (const unit of chosen) unit.state = 'sent';
    const batch = {id: nextBatchId++, units: chosen, text: '', handled: new Set(), lookup};
    batches.set(batch.id, batch);
    connect().postMessage({
      type: 'translate',
      id: batch.id,
      // A paragraph tried before is asked for with plainer words; for one
      // tried twice, the words of its links are asked for alone.
      mode: lookup ? 'phrases' : chosen[0].tries ? 'strict' : 'batch',
      source: session.source,
      target: session.target,
      title: document.title,
      segments: lookup
          ? lookup.lookup.missing.map((number) => escapeText(lookup.groups[number - 1].textContent.replace(/\s+/g, ' ').trim()))
          : chosen.map((unit) => unit.source),
    });
  }

  function segmentsOf(text) {
    const found = [];
    for (const match of text.matchAll(/<s(\d+)>([\s\S]*?)<\/s\1>/g)) found[Number(match[1]) - 1] = match[2];
    return found;
  }

  function handleSegments(batch, text, final) {
    if (batch.lookup) {
      if (final) settle(batch.lookup, placeLinks(batch.lookup, segmentsOf(text)));
      return;
    }
    for (const match of text.matchAll(/<s(\d+)>([\s\S]*?)<\/s\1>/g)) {
      const index = Number(match[1]) - 1;
      const unit = batch.units[index];
      if (!unit || batch.handled.has(index)) continue;
      batch.handled.add(index);
      settle(unit, apply(unit, match[2]));
    }
    if (final) {
      // A single segment answered without its <s1> tags.
      if (batch.units.length === 1 && !batch.handled.size && !/<s\d+>/.test(text)) {
        batch.handled.add(0);
        settle(batch.units[0], apply(batch.units[0], text));
      }
      batch.units.forEach((unit, index) => {
        if (!batch.handled.has(index)) settle(unit, unit.tries ? 'failed' : 'retry');
      });
    }
  }

  function settle(unit, result) {
    if (result === 'retry') {
      unit.tries++;
      unit.state = 'pending';
    } else if (result === 'lookup') {
      unit.tries = 2;
      unit.state = 'lookup';
    } else {
      unit.state = result;
    }
    show();
  }

  function onReply(message) {
    if (message.type === 'config') {
      parallel = Math.max(1, message.parallel || 1);
      pump();
      return;
    }
    if (message.type === 'loading') {
      if (session) session.loading = true;
      show();
      return;
    }
    const finished = batches.get(message.id);
    if (!finished) return;
    if (session) session.loading = false;
    if (message.type === 'delta') {
      finished.text += message.text;
      handleSegments(finished, finished.text, false);
      return;
    }
    batches.delete(message.id);
    if (message.type === 'done') {
      handleSegments(finished, message.text, true);
    } else {
      for (const unit of finished.units) if (unit.state === 'sent') unit.state = unit.lookup ? 'lookup' : 'pending';
      if (finished.lookup && !['canceled', 'no_model', 'host', 'timeout'].includes(message.error)) {
        settle(finished.lookup, placeLinks(finished.lookup, []));
      } else if (message.error === 'canceled') {
        // Stopped on purpose.
      } else if (['no_model', 'host', 'timeout'].includes(message.error)) {
        session.phase = 'error';
        session.error = {no_model: T.noModel, host: T.noHost, timeout: T.stuck}[message.error];
      } else if (finished.units.length > 1) {
        for (const unit of finished.units) unit.tries = Math.max(unit.tries, 1);
      } else {
        finished.units[0].state = 'failed';
      }
    }
    show();
    pump();
  }

  // ------------------------------------------------------------------------
  // Watching for new text: pages that load more as you scroll, or change.

  let changed = new Set();
  let rescanTimer = null;
  const observer = new MutationObserver((records) => {
    if (applying || !session || session.phase === 'original') return;
    for (const record of records) {
      if (overlay && overlay.host.contains(record.target)) continue;
      if (record.type === 'attributes') {
        // Something shown or hidden, such as a menu.
        nudge();
      } else if (record.type === 'characterData') {
        if (!ours.has(record.target)) changed.add(record.target);
      } else {
        for (const node of record.addedNodes) {
          if (!ours.has(node)) changed.add(node);
        }
      }
    }
    if (changed.size && !rescanTimer) {
      rescanTimer = setTimeout(rescan, 500);
    }
  });

  let nudgeTimer = null;
  function nudge() {
    if (!session || nudgeTimer) return;
    nudgeTimer = setTimeout(() => {
      nudgeTimer = null;
      pump();
    }, 300);
  }

  function rescan() {
    rescanTimer = null;
    const roots = [...changed];
    changed = new Set();
    if (!session || session.phase === 'original') return;
    displays = new WeakMap();
    for (const root of roots) scan(root);
    if (session.phase === 'done' && [...units.values()].some((unit) => unit.state === 'pending')) {
      session.phase = 'translating';
    }
    show();
    pump();
  }

  // ------------------------------------------------------------------------
  // What the user does

  function start(target) {
    if (session && session.target === target && session.phase !== 'original' && session.phase !== 'error') {
      if (session.phase === 'stopped') {
        session.phase = 'translating';
        show();
        pump();
      }
      return;
    }
    if (session) showOriginal();
    session = {
      target, source: target === 'ja' ? 'en' : 'ja', phase: 'translating', loading: false, error: null,
      lang: document.documentElement.getAttribute('lang'),
    };
    // The right glyphs for the language, Japanese ones for kanji above all.
    document.documentElement.setAttribute('lang', target);
    units = new Map();
    displays = new WeakMap();
    scan(document.body);
    observer.observe(document.body, {
      childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ['class', 'style', 'hidden', 'open', 'aria-hidden', 'aria-expanded'],
    });
    addEventListener('scroll', nudge, {capture: true, passive: true});
    addEventListener('resize', nudge, {passive: true});
    show();
    pump();
  }

  function stop() {
    if (!session || session.phase !== 'translating') return;
    session.phase = 'stopped';
    for (const batch of batches.values()) {
      port?.postMessage({type: 'cancel', id: batch.id});
      for (const unit of batch.units) if (unit.state === 'sent') unit.state = unit.lookup ? 'lookup' : 'pending';
    }
    batches.clear();
    show();
  }

  function showOriginal() {
    if (!session) return;
    stop();
    observer.disconnect();
    removeEventListener('scroll', nudge, {capture: true});
    removeEventListener('resize', nudge);
    clearTimeout(rescanTimer);
    rescanTimer = null;
    changed = new Set();
    applying = true;
    for (const unit of units.values()) restore(unit);
    applying = false;
    if (session.lang === null) document.documentElement.removeAttribute('lang');
    else document.documentElement.setAttribute('lang', session.lang);
    units = new Map();
    session = null;
    hide();
  }

  function state() {
    if (!session) return {phase: 'original'};
    let done = 0;
    let near = 0;
    let later = 0;
    for (const unit of units.values()) {
      if (unit.state === 'done' || unit.state === 'failed') done++;
      else if (unit.state === 'sent' || inReach(unit)) near++;
      else later++;
    }
    return {
      phase: session.phase,
      target: session.target,
      done,
      total: done + near,
      later,
      loading: session.loading,
      error: session.error,
    };
  }

  chrome.runtime.onMessage.addListener((message, sender, reply) => {
    if (message.type === 'start') start(message.target);
    else if (message.type === 'toggle') session ? showOriginal() : start(message.target);
    else if (message.type === 'stop') stop();
    else if (message.type === 'restore') showOriginal();
    reply(state());
  });

  // ------------------------------------------------------------------------
  // The note in the corner of the page

  function makeOverlay() {
    const host = document.createElement('dual-translate-status');
    const root = host.attachShadow({mode: 'closed'});
    root.innerHTML = `
      <style>
        :host { all: initial; position: fixed; right: 16px; bottom: 16px; z-index: 2147483647; }
        .box { display: flex; align-items: center; gap: 10px; max-width: 360px; padding: 8px 8px 8px 14px;
               border-radius: 10px; background: #ffffff; color: #1d1d1f;
               box-shadow: 0 2px 12px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(0, 0, 0, 0.08);
               font: 13px/1.4 system-ui, -apple-system, "Hiragino Sans", sans-serif; }
        @media (prefers-color-scheme: dark) {
          .box { background: #2c2c2f; color: #ececee; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.12); }
          button { color: #3b9bff; }
          button:hover { background: rgba(255, 255, 255, 0.08); }
        }
        .text { flex: 1; }
        button { padding: 4px 8px; border: 0; border-radius: 6px; background: transparent; color: #007aff;
                 font: inherit; font-weight: 600; cursor: pointer; white-space: nowrap; }
        button:hover { background: rgba(0, 0, 0, 0.06); }
        button.close { padding: 4px 6px; color: inherit; opacity: 0.6; font-weight: 400; }
        [hidden] { display: none; }
      </style>
      <div class="box" role="status">
        <span class="text"></span>
        <button class="action"></button>
        <button class="close">✕</button>
      </div>`;
    const parts = {
      host,
      text: root.querySelector('.text'),
      action: root.querySelector('.action'),
      close: root.querySelector('.close'),
      hideTimer: null,
    };
    parts.close.title = T.close;
    parts.close.setAttribute('aria-label', T.close);
    parts.close.addEventListener('click', hide);
    parts.action.addEventListener('click', () => {
      if (session?.phase === 'translating') stop();
      else showOriginal();
    });
    return parts;
  }

  function show() {
    if (!session) return hide();
    if (!overlay) overlay = makeOverlay();
    const {phase, target, done, total, later, loading, error} = state();
    if (!overlay.host.isConnected) {
      if (session.quiet && (phase === 'translating' || phase === 'done')) return;
      document.documentElement.append(overlay.host);
    }
    clearTimeout(overlay.hideTimer);
    const name = T.names[target];
    overlay.action.hidden = false;
    if (phase === 'translating') {
      overlay.text.textContent = loading ? T.loading : T.working(name, done, total);
      overlay.action.textContent = T.stop;
    } else if (phase === 'done') {
      overlay.text.textContent = later ? T.finishedSoFar(name) : T.finished(name);
      overlay.action.textContent = T.restore;
      overlay.hideTimer = setTimeout(hide, 8000);
    } else if (phase === 'stopped') {
      overlay.text.textContent = T.stopped;
      overlay.action.textContent = T.restore;
    } else {
      overlay.text.textContent = error || T.failed;
      overlay.action.textContent = T.restore;
    }
  }

  function hide() {
    if (!overlay) return;
    clearTimeout(overlay.hideTimer);
    overlay.host.remove();
  }
})();
