// The page a tab shows while its site is closed off: how long the rest still
// lasts and, once it is over, the way back to where the tab was. The site and
// the page to go back to are in this page's own address.

import {breakOf, readAll, standing} from './timelimit.js';
import {clockText, language, text} from './text.js';

const $ = (id) => document.getElementById(id);
const here = breakOf(location.href);
let data = null;

function show() {
  // No limit any more counts as a rest that is over.
  const state = standing(here.site, data, Date.now());
  const resting = Boolean(state) && state.rest > 0;
  $('heading').textContent = resting ? text.breakHeading : text.overHeading;
  $('message').textContent = resting ? text.breakMessage(here.site, text.minutes(state.limit)) : text.overMessage(here.site);
  $('clock').hidden = !resting;
  $('note').hidden = !resting;
  $('back').hidden = resting;
  if (resting) {
    $('clock').textContent = clockText(state.rest);
  }
}

// Back to the page the tab was on. Going back in the tab's history can bring
// it back just as it was; a tab with nothing to go back to loads it instead.
function goBack() {
  if (history.length > 1) {
    history.back();
    setTimeout(() => location.replace(here.to), 1000);
  } else {
    location.replace(here.to);
  }
}

async function start() {
  document.documentElement.lang = language;
  if (!here) {
    $('heading').textContent = text.title;
    $('message').textContent = text.breakUnknown;
    return;
  }
  document.title = text.breakTitle(here.site);
  $('note').textContent = text.breakNote;
  $('back').textContent = text.back(here.site);
  $('back').addEventListener('click', goBack);
  data = await readAll();
  show();
  setInterval(show, 250);
  chrome.storage.onChanged.addListener(async () => {
    data = await readAll();
    show();
  });
}

start();
