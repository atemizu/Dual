// What the background worker, the popup and the break page have to agree on:
// what a site is, what is stored, and how a sitting is counted.
//
// A limit belongs to one site and stays until it is removed. It limits a
// sitting: the time the site is looked at without a rest. A rest is the site
// not being looked at for the rest time; after one, counting starts again
// from nothing. When a sitting reaches the limit, the site is closed off
// until a rest has passed.
//
// Stored (chrome.storage.local):
//   limits    site -> minutes
//   rest      minutes
//   sittings  site -> {viewed, last, blocked}: milliseconds looked at in this
//             sitting, when the site was last looked at, and, once the limit
//             is reached, when that was
//   watch     {site, at}: the site being looked at when the worker last
//             checked, and when that was; absent when none with a limit was

export const PRESET_MINUTES = [15, 30, 60];
export const MAX_MINUTES = 600;
export const REST_CHOICES = [5, 10, 15, 30, 60];
export const DEFAULT_REST = 5;
export const MINUTE = 60 * 1000;
// While a site is being counted the worker checks at least once a minute. A
// longer silence means the Mac slept or the browser was not running, and is
// not counted as looking.
export const LONGEST_STEP = 3 * MINUTE;

const BREAK_PAGE = 'break.html';

// The site a page belongs to: its host name without a leading "www.", or
// null for a page that is not on the web.
export function siteOf(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch (error) {
    return null;
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return null;
  }
  return parsed.hostname.replace(/^www\./, '') || null;
}

// The page shown in place of |url| while its site is closed off.
export function breakUrl(site, url) {
  return `${chrome.runtime.getURL(BREAK_PAGE)}?${new URLSearchParams({site, to: url})}`;
}

// For a break page's address: the site it stands in for and the page to go
// back to, which is always a page of that site. Null for any other address.
export function breakOf(url) {
  if (!url || !url.startsWith(`${chrome.runtime.getURL(BREAK_PAGE)}?`)) {
    return null;
  }
  const params = new URL(url).searchParams;
  const site = params.get('site');
  if (!site) {
    return null;
  }
  const to = params.get('to');
  return {site, to: siteOf(to) === site ? to : `https://${site}/`};
}

// A length of time the worker accepts for a limit or a rest. The popup only
// offers whole minutes; the tests use shorter ones.
export function isLength(minutes) {
  return Number.isFinite(minutes) && minutes > 0 && minutes <= MAX_MINUTES;
}

// What was typed as a number of minutes, or null if it is not a whole number
// in range.
export function wholeMinutes(typed) {
  const minutes = Number(typed);
  return String(typed).trim() !== '' && Number.isInteger(minutes) && minutes >= 1 && minutes <= MAX_MINUTES
      ? minutes : null;
}

export async function readAll() {
  const {limits = {}, rest = DEFAULT_REST, sittings = {}, watch = null} =
      await chrome.storage.local.get(['limits', 'rest', 'sittings', 'watch']);
  return {limits, rest, sittings, watch};
}

// Brings the sittings up to |now|, given the site being looked at then (or
// null). Returns the new sittings and watch; changes nothing passed in.
export function advance(data, now, looking) {
  const restTime = data.rest * MINUTE;
  const sittings = {};
  for (const [site, sitting] of Object.entries(data.sittings)) {
    if (data.limits[site] !== undefined) {
      sittings[site] = {...sitting};
    }
  }

  // The time since the last check goes to the site that was looked at then.
  const watched = data.watch && sittings[data.watch.site];
  if (watched && !watched.blocked) {
    const step = now - data.watch.at;
    if (step > 0 && step <= LONGEST_STEP) {
      watched.viewed += step;
      watched.last = now;
    }
  }

  for (const [site, sitting] of Object.entries(sittings)) {
    if (sitting.blocked) {
      // (A block or a last look in the future means the clock was set back.)
      if (sitting.blocked > now || now >= sitting.blocked + restTime) {
        delete sittings[site];
      }
    } else if (sitting.viewed >= data.limits[site] * MINUTE) {
      sitting.blocked = now;
    } else if (sitting.last > now || now - sitting.last >= restTime) {
      delete sittings[site];
    }
  }

  let watch = null;
  if (looking && data.limits[looking] !== undefined && !(sittings[looking] && sittings[looking].blocked)) {
    sittings[looking] = {viewed: 0, ...sittings[looking], last: now};
    watch = {site: looking, at: now};
  }
  return {sittings, watch};
}

// Where a site stands at |now|, for showing: null without a limit, else
// {limit, viewed, left, rest}: the limit in minutes; how long this sitting
// has lasted and how much of it is left, in milliseconds; and, while the site
// is closed off, how long until it opens again.
export function standing(site, data, now) {
  const limit = data.limits[site];
  if (limit === undefined) {
    return null;
  }
  const whole = limit * MINUTE;
  // As the worker would find it now, if what was being looked at still is.
  const sitting = advance(data, now, data.watch ? data.watch.site : null).sittings[site];
  if (!sitting) {
    return {limit, viewed: 0, left: whole, rest: 0};
  }
  if (sitting.blocked) {
    return {limit, viewed: whole, left: 0, rest: sitting.blocked + data.rest * MINUTE - now};
  }
  return {limit, viewed: sitting.viewed, left: whole - sitting.viewed, rest: 0};
}
