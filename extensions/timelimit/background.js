// Counts how long each site with a limit is looked at in one sitting, and
// closes the site off for a rest when the limit is reached (see timelimit.js
// for the rule).
//
// A site is being looked at while one of its pages is the tab in front in
// the browser window in use, and someone is there: the Mac is not locked, and
// either it has been used in the last two minutes or the page is playing
// sound. With two Dual panes, that is the pane last clicked.
//
// A site that is closed off is not blocked on the network: a tab in front
// that shows it is sent to this extension's break page instead, which leads
// back to where the tab was. Tabs in the background are left as they are
// until they come to the front. The extension never reads or changes a page.
//
// A page can ask whether it should really be left (it holds something
// unsaved) and be told no. Its tab then stays on the site; the rest does not
// begin while it does, and the tab is sent again later.

import {MINUTE, advance, breakUrl, isLength, readAll, siteOf, standing} from './timelimit.js';

const ALARM = 'next';
// No keyboard or pointer for this long, and no sound: nobody is looking.
const IDLE_SECONDS = 120;
// A tab that was sent to the break page and is still where it was is not
// sent again for this long.
const RETRY_SECONDS = 30;
const BADGE_COLOUR = '#5F6368';
const BADGE_LAST_MINUTE_COLOUR = '#D93025';

// When each tab was sent to the break page, until its address changes: kept
// for the browser session as {tab id: time}, since the worker itself is
// stopped whenever it has nothing to do.
async function readSent() {
  const {sent = {}} = await chrome.storage.session.get('sent');
  return sent;
}

async function forgetSent(tabId) {
  const sent = await readSent();
  if (sent[tabId] !== undefined) {
    delete sent[tabId];
    await chrome.storage.session.set({sent});
  }
}

// Everything that reads and then writes what is stored runs one at a time.
let queue = Promise.resolve();
function inTurn(task) {
  const result = queue.then(task);
  queue = result.catch(() => {});
  return result;
}

// The site being looked at now, or null.
async function lookingAt() {
  let window;
  try {
    window = await chrome.windows.getLastFocused({windowTypes: ['normal']});
  } catch (error) {
    return null;  // No browser window at all.
  }
  if (!window.focused || window.state === 'minimized') {
    return null;
  }
  const [tab] = await chrome.tabs.query({active: true, windowId: window.id});
  const site = tab && siteOf(tab.url);
  if (!site) {
    return null;
  }
  const state = await chrome.idle.queryState(IDLE_SECONDS);
  return state === 'active' || (state === 'idle' && tab.audible) ? site : null;
}

// The sites whose rest cannot begin yet: a tab that was sent to the break
// page is still showing the site in front.
function sitesNotLeft(stored, tabs, sent) {
  return tabs
      .filter((tab) => sent[tab.id] !== undefined)
      .map((tab) => siteOf(tab.url))
      .filter((site) => site && stored.sittings[site] && stored.sittings[site].blocked);
}

// Sends each tab in front that shows a closed-off site to the break page.
async function closeOff(data, tabs, sent, now) {
  let changed = false;
  for (const tab of tabs) {
    const site = siteOf(tab.url);
    if (!site || !data.sittings[site] || !data.sittings[site].blocked) {
      continue;
    }
    if (now - (sent[tab.id] || 0) < RETRY_SECONDS * 1000) {
      continue;
    }
    sent[tab.id] = now;
    changed = true;
    try {
      await chrome.tabs.update(tab.id, {url: breakUrl(site, tab.url)});
    } catch (error) {
      // The tab is gone, or cannot be changed just now (it is being dragged).
    }
  }
  if (changed) {
    await chrome.storage.session.set({sent});
  }
}

// On the button, for each tab in front on a site with a limit: the minutes
// left of the sitting.
async function showLeft(data, tabs, now) {
  for (const tab of tabs) {
    const site = siteOf(tab.url);
    const state = site && standing(site, data, now);
    if (!state || state.rest > 0) {
      continue;
    }
    const minutes = Math.max(1, Math.ceil(state.left / MINUTE));
    try {
      await chrome.action.setBadgeBackgroundColor(
          {tabId: tab.id, color: minutes <= 1 ? BADGE_LAST_MINUTE_COLOUR : BADGE_COLOUR});
      await chrome.action.setBadgeText({tabId: tab.id, text: String(minutes)});
    } catch (error) {
      // The tab is gone.
    }
  }
}

async function clearLeft(site) {
  for (const tab of await chrome.tabs.query({windowType: 'normal'})) {
    if (siteOf(tab.url) === site) {
      await chrome.action.setBadgeText({tabId: tab.id, text: ''}).catch(() => {});
    }
  }
}

// The next time something changes without anything happening in the browser:
// the minutes left of the sitting being counted go down by one (the last of
// these is the limit itself), or a rest ends.
async function setAlarm(data, now) {
  const times = [];
  if (data.watch) {
    const {left} = standing(data.watch.site, data, now);
    times.push(now + (left % MINUTE || MINUTE));
  }
  for (const sitting of Object.values(data.sittings)) {
    if (sitting.blocked) {
      times.push(sitting.blocked + data.rest * MINUTE);
    }
  }
  if (times.length) {
    await chrome.alarms.create(ALARM, {when: Math.min(...times)});
  } else {
    await chrome.alarms.clear(ALARM);
  }
}

// Brings everything up to now. Returns what is stored afterwards.
async function check() {
  const stored = await readAll();
  if (!Object.keys(stored.limits).length && !Object.keys(stored.sittings).length && !stored.watch) {
    // No site has a limit: nothing to count, show or wait for.
    return stored;
  }
  const looking = await lookingAt();
  const tabs = await chrome.tabs.query({active: true, windowType: 'normal'});
  const sent = await readSent();
  const now = Date.now();
  for (const site of sitesNotLeft(stored, tabs, sent)) {
    stored.sittings[site].blocked = now;
  }
  const data = {...stored, ...advance(stored, now, looking)};
  await chrome.storage.local.set({sittings: data.sittings, watch: data.watch});
  await closeOff(data, tabs, sent, now);
  await showLeft(data, tabs, now);
  await setAlarm(data, now);
  return data;
}

// What the popup asks for. A limit that is set, changed or removed starts
// its site's sitting afresh, which also opens the site if it was closed off.
async function change(message) {
  const {limits, sittings, watch} = await readAll();
  const forget = async (site) => {
    delete sittings[site];
    await chrome.storage.local.set({limits, sittings, watch: watch && watch.site === site ? null : watch});
  };
  if (message.set && typeof message.set.site === 'string' && message.set.site &&
      isLength(message.set.minutes) && limits[message.set.site] !== message.set.minutes) {
    limits[message.set.site] = message.set.minutes;
    await forget(message.set.site);
  } else if (typeof message.remove === 'string' && limits[message.remove] !== undefined) {
    delete limits[message.remove];
    await forget(message.remove);
    await clearLeft(message.remove);
  } else if (isLength(message.rest)) {
    await chrome.storage.local.set({rest: message.rest});
  }
}

chrome.idle.setDetectionInterval(IDLE_SECONDS);

const look = () => inTurn(check).catch(() => {});
// For a tab that has gone elsewhere or is gone: it is no longer one that would not leave.
const lookAfterMove = (tabId) => inTurn(async () => {
  await forgetSent(tabId);
  return check();
}).catch(() => {});
chrome.runtime.onInstalled.addListener(look);
chrome.runtime.onStartup.addListener(look);
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM) {
    look();
  }
});
chrome.idle.onStateChanged.addListener(look);
chrome.windows.onFocusChanged.addListener(look);
chrome.tabs.onActivated.addListener(look);
chrome.tabs.onAttached.addListener(look);
chrome.tabs.onUpdated.addListener((tabId, changes) => {
  // The address, for which site is in front; the sound, for whether someone
  // is there; and the end of loading, because loading a page takes the
  // minutes off the button.
  if (changes.url) {
    lookAfterMove(tabId);
  } else if (changes.audible !== undefined || changes.status === 'complete') {
    look();
  }
});
chrome.tabs.onRemoved.addListener(lookAfterMove);

// From the popup and the break page: {set: {site, minutes}}, {remove: site},
// {rest: minutes}, or anything else just to look. The answer is what is
// stored afterwards.
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.id !== chrome.runtime.id) {
    return false;
  }
  inTurn(async () => {
    if (message && typeof message === 'object') {
      await change(message);
    }
    return check();
  }).then(respond, () => respond(null));
  return true;
});
