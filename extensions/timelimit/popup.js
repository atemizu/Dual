// The popup: for the site in front, a limit in one click (or any number of
// minutes), where its sitting stands, and a way to remove the limit; the
// length of a rest; and every site that has a limit.

import {
  MAX_MINUTES, PRESET_MINUTES, REST_CHOICES, breakOf, readAll, siteOf, standing, wholeMinutes,
} from './timelimit.js';
import {clockText, language, sittingMinutes, text} from './text.js';

const $ = (id) => document.getElementById(id);

// The site of the tab the popup was opened on, or null; a break page counts
// as the site it stands in for.
let site = null;
let data = null;

// Asks the worker for a change (or just to look) and shows the result.
async function ask(message) {
  data = (await chrome.runtime.sendMessage(message).catch(() => null)) || (await readAll());
  showAll();
}

// The parts that change as time passes.
function showTime() {
  const now = Date.now();
  const state = site && standing(site, data, now);
  if (site) {
    $('rule').textContent = state ? text.rule(text.minutes(state.limit), text.minutes(data.rest)) : text.noLimit;
    $('now').hidden = !state;
    if (state) {
      const {viewed, left} = sittingMinutes(state);
      $('now').textContent = state.rest > 0 ? text.resting(clockText(state.rest)) : text.counting(viewed, left);
    }
  }
  for (const item of $('list').children) {
    const other = standing(item.dataset.site, data, now);
    if (!other) continue;
    item.querySelector('.length').textContent =
        [text.minutes(other.limit), other.rest > 0 ? text.listResting : ''].filter(Boolean).join(' ・ ');
  }
}

function showAll() {
  $('here').hidden = !site;
  $('nowhere').hidden = Boolean(site);
  if (site) {
    const limit = data.limits[site];
    $('site').textContent = site;
    for (const button of $('presets').children) {
      button.setAttribute('aria-pressed', String(Number(button.value) === limit));
    }
    const own = limit !== undefined && !PRESET_MINUTES.includes(limit);
    $('minutes').classList.toggle('chosen', own);
    if (document.activeElement !== $('minutes')) {
      $('minutes').value = own ? String(limit) : '';
    }
    $('remove').hidden = limit === undefined;
  }
  $('rest').value = String(data.rest);
  if ($('rest').value !== String(data.rest)) {
    // A length that is not among the choices (set some other way) is shown too.
    $('rest').add(new Option(text.minutes(data.rest), String(data.rest)));
    $('rest').value = String(data.rest);
  }

  const sites = Object.keys(data.limits).sort();
  $('list-none').hidden = sites.length > 0;
  $('list-note').hidden = sites.length === 0;
  $('list').replaceChildren(...sites.map((other) => {
    const item = document.createElement('li');
    item.dataset.site = other;
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = other;
    name.title = other;
    const length = document.createElement('span');
    length.className = 'length';
    const remove = document.createElement('button');
    remove.className = 'quiet';
    remove.textContent = '✕';
    remove.title = text.listRemove(other);
    remove.setAttribute('aria-label', text.listRemove(other));
    remove.addEventListener('click', () => ask({remove: other}));
    item.append(name, length, remove);
    return item;
  }));
  showTime();
}

async function start() {
  document.documentElement.lang = language;
  $('title').textContent = text.title;
  $('nowhere').textContent = text.nowhere;
  $('custom-label').textContent = text.custom;
  $('unit').textContent = text.unit;
  $('set').textContent = text.set;
  $('range').textContent = text.customRange(MAX_MINUTES);
  $('remove').textContent = text.remove;
  $('rest-label').textContent = text.restLabel;
  $('rest-hint').textContent = text.restHint;
  $('list-heading').textContent = text.listHeading;
  $('list-none').textContent = text.listNone;
  $('list-note').textContent = text.listNote;
  $('minutes').max = String(MAX_MINUTES);

  for (const minutes of PRESET_MINUTES) {
    const button = document.createElement('button');
    button.type = 'button';
    button.value = String(minutes);
    button.textContent = text.minutes(minutes);
    button.addEventListener('click', () => ask({set: {site, minutes}}));
    $('presets').append(button);
  }
  for (const minutes of REST_CHOICES) {
    $('rest').add(new Option(text.minutes(minutes), String(minutes)));
  }

  $('custom').addEventListener('submit', (event) => {
    event.preventDefault();
    const minutes = wholeMinutes($('minutes').value);
    $('range').hidden = minutes !== null;
    if (minutes !== null) {
      $('minutes').blur();
      ask({set: {site, minutes}});
    }
  });
  $('remove').addEventListener('click', () => ask({remove: site}));
  $('rest').addEventListener('change', () => ask({rest: Number($('rest').value)}));

  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  const address = tab && (tab.url || tab.pendingUrl);
  const resting = breakOf(address);
  site = resting ? resting.site : siteOf(address);

  await ask('look');
  setInterval(showTime, 500);
  // The worker may close a site off, or end a rest, while the popup is open.
  chrome.storage.onChanged.addListener(async () => {
    data = await readAll();
    showAll();
  });
}

start();
