// Dual Page Translate: connects the pages being translated to the translation
// program that comes with Dual (the native host "dual.translate"), which runs
// the model on this computer.

import {answerTokens, strictPrompt, systemPrompt, userPrompt} from './prompt.js';
import {text} from './text.js';

const HOST = 'dual.translate';

// With nothing to translate for this long, the program is closed, which gives
// back the memory the model takes (about 6 GB).
const IDLE_CLOSE = 10 * 60 * 1000;

// A request with no word from the program for this long is given up, and the
// program closed: something holds it up (loading the model takes seconds).
const SILENCE_LIMIT = 3 * 60 * 1000;

let host = null;            // The port to the program, while it runs.
let status = null;          // Its last "hello": the model's state and so on.
let hostError = null;       // Why the program could not be reached.
let download = null;        // The download's last progress report.
let idleTimer = null;
let silenceTimer = null;
let nextJob = 1;
const jobs = new Map();     // Job id -> {port, requestId, heard}.
const popups = new Set();   // Open popups, told about every change.
const pages = new Set();    // Pages being translated.

function connectHost() {
  if (host) return host;
  hostError = null;
  host = chrome.runtime.connectNative(HOST);
  host.onMessage.addListener(onHostMessage);
  host.onDisconnect.addListener(() => {
    const error = chrome.runtime.lastError?.message || '';
    host = null;
    if (!status) {
      hostError = /not found/i.test(error) ? 'missing' : 'failed';
    }
    status = null;
    if (download && ['running', 'verifying'].includes(download.state)) {
      download = {state: 'error', error: 'stopped'};
    }
    for (const [, job] of jobs) {
      job.port.postMessage({type: 'error', id: job.requestId, error: 'host'});
    }
    jobs.clear();
    tellPopups();
  });
  host.postMessage({type: 'hello'});
  return host;
}

function onHostMessage(message) {
  switch (message.type) {
    case 'hello':
      status = message;
      tellPopups();
      tellPages();
      break;
    case 'download':
      download = message;
      if (message.state === 'done') {
        host?.postMessage({type: 'hello'});
      }
      tellPopups();
      break;
    case 'loading':
      for (const [, job] of jobs) {
        job.heard = Date.now();
        job.port.postMessage({type: 'loading'});
      }
      break;
    case 'delta':
    case 'done':
    case 'error': {
      const job = jobs.get(message.id);
      if (!job) break;
      job.heard = Date.now();
      if (message.type !== 'delta') {
        jobs.delete(message.id);
        armIdleClose();
      }
      try {
        job.port.postMessage({...message, id: job.requestId});
      } catch {
        // The page went away; its jobs are canceled below.
      }
      break;
    }
  }
}

function watchSilence() {
  clearInterval(silenceTimer);
  silenceTimer = setInterval(() => {
    if (!jobs.size) {
      clearInterval(silenceTimer);
      return;
    }
    // Only the oldest request is being worked on; the rest wait their turn.
    const [id, job] = jobs.entries().next().value;
    if (Date.now() - job.heard < SILENCE_LIMIT) return;
    for (const [, waiting] of jobs) {
      waiting.port.postMessage({type: 'error', id: waiting.requestId, error: 'timeout'});
    }
    jobs.clear();
    host?.disconnect();
    host = null;
    status = null;
    tellPopups();
  }, 15 * 1000);
}

// Closes the program once nothing has used it for a while.
function armIdleClose() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    const downloading = download && ['running', 'verifying'].includes(download.state);
    if (host && jobs.size === 0 && !downloading) {
      host.disconnect();
      host = null;
      status = null;
      tellPopups();
    }
  }, IDLE_CLOSE);
}

// How many requests the pages may have on their way at once.
function tellPages() {
  for (const page of pages) {
    page.postMessage({type: 'config', parallel: status?.parallel || 1});
  }
}

function popupState() {
  return {type: 'state', status, hostError, download};
}

function tellPopups() {
  for (const popup of popups) {
    popup.postMessage(popupState());
  }
}

// Puts the page script into the tab and starts it. Clicking the button, the
// menu item or the shortcut gives access to that one tab, nothing more.
async function startInTab(tabId, target) {
  await chrome.scripting.executeScript({target: {tabId}, files: ['content.js']});
  return chrome.tabs.sendMessage(tabId, {type: 'start', target});
}

async function pageLanguage(tabId) {
  const [{result}] = await chrome.scripting.executeScript({
    target: {tabId},
    func: () => {
      const sample = (document.body?.innerText || '').slice(0, 20000);
      const japanese = (sample.match(/[぀-ヿ㐀-鿿]/g) || []).length;
      const latin = (sample.match(/[A-Za-z]/g) || []).length;
      // A Japanese character carries about as much as three Latin letters.
      return japanese * 3 >= latin ? 'ja' : 'en';
    },
  });
  return result;
}

// The menu item and the shortcut translate the page into the other language,
// or, on a page already translated, bring the original back.
async function translateFromShortcut(tab) {
  if (!tab?.id) return;
  try {
    const target = (await pageLanguage(tab.id)) === 'ja' ? 'en' : 'ja';
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
    await chrome.tabs.sendMessage(tab.id, {type: 'toggle', target});
  } catch {
    // Pages that extensions may not touch, such as the settings.
  }
}

chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'popup') {
    popups.add(port);
    port.onDisconnect.addListener(() => popups.delete(port));
    port.onMessage.addListener(async (message) => {
      if (message.type === 'hello') {
        connectHost();
        armIdleClose();
        port.postMessage(popupState());
      } else if (message.type === 'download') {
        download = {state: 'running', bytes: status?.model?.bytes || 0, total: status?.model?.total || 0};
        connectHost().postMessage({type: 'download'});
        tellPopups();
      } else if (message.type === 'cancelDownload') {
        host?.postMessage({type: 'cancelDownload'});
      }
    });
    return;
  }

  if (port.name === 'page') {
    const mine = new Set();
    pages.add(port);
    connectHost();
    if (status) port.postMessage({type: 'config', parallel: status.parallel || 1});
    port.onDisconnect.addListener(() => {
      pages.delete(port);
      for (const id of mine) {
        if (jobs.delete(id)) host?.postMessage({type: 'cancel', id});
      }
      armIdleClose();
    });
    port.onMessage.addListener((message) => {
      if (message.type === 'translate') {
        const id = `job${nextJob++}`;
        mine.add(id);
        jobs.set(id, {port, requestId: message.id, heard: Date.now()});
        clearTimeout(idleTimer);
        watchSilence();
        connectHost().postMessage({
          type: 'generate',
          id,
          system: message.mode === 'strict'
              ? strictPrompt(message.source, message.target)
              : systemPrompt(message.source, message.target, message.title),
          user: userPrompt(message.segments),
          maxTokens: answerTokens(message.segments, message.target),
        });
      } else if (message.type === 'cancel') {
        for (const [id, job] of jobs) {
          if (job.port === port && (message.id === undefined || job.requestId === message.id)) {
            jobs.delete(id);
            host?.postMessage({type: 'cancel', id});
          }
        }
      }
    });
  }
});

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (message.type === 'startInTab') {
    startInTab(message.tabId, message.target).then(
        () => reply({ok: true}), (error) => reply({ok: false, error: String(error?.message || error)}));
    return true;
  }
  if (message.type === 'pageLanguage') {
    pageLanguage(message.tabId).then((language) => reply({language}), () => reply({language: null}));
    return true;
  }
  return false;
});

function addMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({id: 'translate-page', title: text.menuTranslate, contexts: ['page']});
  });
}

chrome.runtime.onInstalled.addListener(addMenu);
chrome.runtime.onStartup.addListener(addMenu);

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'translate-page') translateFromShortcut(tab);
});

chrome.commands.onCommand.addListener((command, tab) => {
  if (command === 'translate-page') translateFromShortcut(tab);
});
