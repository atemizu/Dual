// What the model is told. A page arrives as numbered segments in page order,
// so that each is translated with the ones around it in view; markers inside
// a segment stand for links and other formatting, and for things embedded in
// the text, so that they can be put back around the translated words.

const NAMES = {en: 'English', ja: 'Japanese'};

// One example in the direction being translated: with only an example in the
// other direction, the model drops markers more often from Japanese.
const EXAMPLES = {
  en: '<s1><g1>Sign in</g1></s1>\n' +
      '<s2>The city will make <g1>bus fares</g1> free from April.<x1/> See the <g2>official site</g2>.</s2>\n' +
      'becomes\n' +
      '<s1><g1>ログイン</g1></s1>\n' +
      '<s2>市は4月から<g1>バス運賃</g1>を無料にする。<x1/>詳しくは<g2>公式サイト</g2>へ。</s2>',
  ja: '<s1><g1>ログイン</g1></s1>\n' +
      '<s2>市は4月から<g1>バス運賃</g1>を無料にする。<x1/>詳しくは<g2>公式サイト</g2>へ。</s2>\n' +
      'becomes\n' +
      '<s1><g1>Sign in</g1></s1>\n' +
      '<s2>The city will make <g1>bus fares</g1> free from April.<x1/> See the <g2>official site</g2> for details.</s2>',
};

export function systemPrompt(source, target, title, withExample = false) {
  const from = NAMES[source];
  const to = NAMES[target];
  const titled = title ? ` The page is titled "${title.slice(0, 200)}".` : '';
  return `You translate a web page from ${from} into ${to}.${titled} ` +
      'The user message holds numbered segments of the page, in page order: <s1>…</s1>, <s2>…</s2> and so on. ' +
      `Translate every segment into natural ${to}, the way a native ${to} writer would put it, keeping the meaning, ` +
      'tone and register (casual stays casual, polite stays polite). Read the segments together, as one text, ' +
      'so that each is translated in context. Keep names, numbers, code, URLs and keyboard shortcuts as they are. ' +
      'Inside a segment, <gN>…</gN> wraps formatted words such as a link, and <xN/> stands for an embedded item ' +
      `such as a picture. Every such marker must appear in the translation: each <gN>…</gN> around the ${to} words ` +
      'that translate the marked words, each <xN/> where the item belongs. Answer with the translated segments ' +
      'only, each inside its own <sN>…</sN> tags, in the same order.' +
      (withExample ? `\n\nExample (${from} to ${to}):\n${EXAMPLES[source]}` : '');
}

// For a paragraph whose markers were lost: plainer words, one paragraph, the
// markers first.
export function strictPrompt(source, target) {
  const from = NAMES[source];
  const to = NAMES[target];
  return `You translate a segment of a web page from ${from} into ${to}. The user message holds it inside <s1>…</s1>. ` +
      'Inside it, <gN>…</gN> wraps formatted words such as a link, and <xN/> stands for an embedded item such as a ' +
      `picture. Translate it into natural ${to}. Every such marker must appear in the translation: each <gN>…</gN> ` +
      `around the ${to} words that translate the marked words, each <xN/> where the item belongs. ` +
      'Answer with the translation only, inside <s1>…</s1>.';
}

export function userPrompt(segments) {
  return segments.map((text, index) => `<s${index + 1}>${text}</s${index + 1}>`).join('\n');
}

// Room for the answer: Japanese takes more tokens per character than English.
export function answerTokens(segments, target) {
  const characters = segments.reduce((sum, text) => sum + text.length, 0);
  return Math.min(6000, Math.ceil(characters * (target === 'ja' ? 1.6 : 1.2)) + 64 * segments.length + 128);
}
