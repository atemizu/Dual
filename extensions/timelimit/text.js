// The words of the popup and the break page, in Japanese or English by the
// browser's language.

import {MINUTE} from './timelimit.js';

const STRINGS = {
  ja: {
    title: 'サイト時間制限',
    minutes: (minutes) => {
      if (minutes < 60) return `${minutes}分`;
      const rest = minutes % 60;
      return rest ? `${Math.floor(minutes / 60)}時間${rest}分` : `${minutes / 60}時間`;
    },
    nowhere: 'このページには時間制限を付けられません。ウェブサイトを開いているタブで使ってください。',
    noLimit: 'このサイトに制限はありません。続けて見られる時間を選ぶと、制限が付きます。',
    rule: (limit, rest) => `続けて見られるのは${limit}まで。達すると、${rest}の休憩になります。`,
    counting: (viewed, left) => `いまの回：${viewed}分見ました（あと${left}分）。`,
    resting: (clock) => `休憩中です。あと ${clock} で、また見られます。`,
    custom: 'ほかの長さ',
    unit: '分',
    set: '設定',
    customRange: (max) => `1〜${max}の整数で入れてください。`,
    remove: 'このサイトの制限をやめる',
    restLabel: '休憩の長さ',
    restHint: '制限に達したサイトは、この長さのあいだ開けません。自分からこの長さ以上離れたときも、数え直します。',
    listHeading: '制限しているサイト',
    listNone: 'まだありません。',
    listNote: '制限は、やめるまでずっと続きます。',
    listResting: '休憩中',
    listRemove: (site) => `${site} の制限をやめる`,
    breakTitle: (site) => `休憩 — ${site}`,
    breakHeading: '休憩の時間です',
    breakMessage: (site, limit) => `${site} を${limit}続けて見ました。`,
    breakNote: 'この時間が過ぎると、また見られます。',
    overHeading: '休憩が終わりました',
    overMessage: (site) => `${site} を、また見られます。`,
    back: (site) => `${site} に戻る`,
    breakUnknown: 'このページは、休憩中のサイトの代わりに表示されるものです。',
  },
  en: {
    title: 'Site Time Limit',
    minutes: (minutes) => {
      if (minutes < 60) return `${minutes} min`;
      const rest = minutes % 60;
      const hours = Math.floor(minutes / 60);
      return rest ? `${hours} h ${rest} min` : `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
    },
    nowhere: 'This page cannot be given a time limit. Use this on a tab showing a website.',
    noLimit: 'No limit on this site. Choose how long you may keep looking at it to set one.',
    rule: (limit, rest) => `You may keep looking for ${limit}. Then the site rests for ${rest}.`,
    counting: (viewed, left) => `This sitting: ${viewed} min so far (${left} min left).`,
    resting: (clock) => `Resting. You can look again in ${clock}.`,
    custom: 'Another length',
    unit: 'min',
    set: 'Set',
    customRange: (max) => `Enter a whole number from 1 to ${max}.`,
    remove: 'Remove the limit on this site',
    restLabel: 'Length of a rest',
    restHint: 'A site that reached its limit stays closed for this long. Staying away this long on your own also starts the count again.',
    listHeading: 'Sites with a limit',
    listNone: 'None yet.',
    listNote: 'A limit stays until you remove it.',
    listResting: 'resting',
    listRemove: (site) => `Remove the limit on ${site}`,
    breakTitle: (site) => `Rest — ${site}`,
    breakHeading: 'Time for a rest',
    breakMessage: (site, limit) => `You have been looking at ${site} for ${limit}.`,
    breakNote: 'You can look again when this runs out.',
    overHeading: 'The rest is over',
    overMessage: (site) => `You can look at ${site} again.`,
    back: (site) => `Back to ${site}`,
    breakUnknown: 'This page is shown in place of a site that is resting.',
  },
};

export const language = chrome.i18n.getUILanguage().startsWith('ja') ? 'ja' : 'en';
export const text = STRINGS[language];

// What is left of a rest, as minutes and seconds (hours too if need be).
export function clockText(milliseconds) {
  const seconds = Math.max(0, Math.ceil(milliseconds / 1000));
  const two = (number) => String(number).padStart(2, '0');
  const minutes = Math.floor(seconds / 60);
  return minutes < 60
      ? `${minutes}:${two(seconds % 60)}`
      : `${Math.floor(minutes / 60)}:${two(minutes % 60)}:${two(seconds % 60)}`;
}

// A sitting's time so far and time left, in whole minutes that add up to the
// limit's own whole minutes.
export function sittingMinutes(state) {
  const left = Math.max(1, Math.ceil(state.left / MINUTE));
  return {viewed: Math.max(0, Math.ceil(state.limit) - left), left};
}
