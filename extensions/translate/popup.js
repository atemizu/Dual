// The popup: installs the model the first time, then translates the page in
// the current tab and brings the original back.

import {language, sizeText, text} from './text.js';

const $ = (id) => document.getElementById(id);

let tabId = null;
let pageLanguage = null;   // What the page seems to be written in, or null.
let pageState = {phase: 'original'};
let latest = null;         // The background's last report.

function showText() {
  document.documentElement.lang = language;
  $('title').textContent = text.title;
  $('checking').textContent = text.checking;
  $('intro').textContent = text.intro;
  $('cancel').textContent = text.cancel;
  $('to-ja').textContent = text.into(text.names.ja);
  $('to-en').textContent = text.into(text.names.en);
  $('stop').textContent = text.stop;
  $('resume').textContent = text.resumeTranslation;
  $('restore').textContent = text.restore;
  $('no-page').textContent = text.noPage;
  $('slow').textContent = text.slow;
  $('shortcut').textContent = text.shortcutHint;
}

function render() {
  const {status, hostError, download} = latest || {};
  $('checking').hidden = Boolean(status || hostError);
  $('host-error').hidden = !hostError;
  $('host-error').textContent = hostError === 'missing' ? text.hostMissing : text.hostFailed;
  const model = status?.model;
  const ready = model?.state === 'ready';
  $('setup').hidden = !model || ready;
  $('ready').hidden = !ready;
  if (model && !ready) renderSetup(model, status, download);
  if (ready) renderReady(model, status);
}

function renderSetup(model, status, download) {
  $('need').textContent = text.needModel(model.name, sizeText(model.total));
  $('free').textContent = text.freeSpace(sizeText(status.freeSpace));
  const running = download && ['running', 'verifying'].includes(download.state);
  $('progress').hidden = !running;
  $('download').hidden = running;
  $('partial').hidden = running || model.state !== 'partial';
  $('partial').textContent = text.partial(sizeText(model.bytes));
  $('download').textContent = model.state === 'partial' ? text.resume : text.download;
  if (running) {
    const fraction = download.total ? download.bytes / download.total : 0;
    $('bar-fill').style.width = `${(fraction * 100).toFixed(1)}%`;
    $('progress-text').textContent = download.state === 'verifying'
        ? text.verifying : text.downloading(sizeText(download.bytes), sizeText(download.total));
    $('cancel').hidden = false;
  }
  const failed = download?.state === 'error';
  $('download-error').hidden = !failed;
  if (failed) {
    const describe = text.errors[download.error] || text.errors.other;
    $('download-error').textContent = typeof describe === 'function'
        ? describe(sizeText(download.needed - download.free)) : describe;
    $('download').textContent = text.retry;
  }
}

function renderReady(model, status) {
  $('model').textContent = text.modelReady(model.name);
  $('slow').hidden = status.accelerator !== 'cpu';
  $('no-page').hidden = Boolean(pageLanguage);
  $('page').hidden = !pageLanguage;
  if (!pageLanguage) return;
  $('page-is').textContent = text.pageIs(text.names[pageLanguage]);
  const suggested = pageLanguage === 'ja' ? 'en' : 'ja';
  $('to-ja').classList.toggle('suggested', suggested === 'ja');
  $('to-en').classList.toggle('suggested', suggested === 'en');

  const {phase, target, done, total, loading} = pageState;
  const active = phase !== 'original';
  $('choices').hidden = active;
  $('running').hidden = !active;
  if (!active) return;
  const name = text.names[target];
  $('running-text').textContent =
      phase === 'translating' ? (loading ? text.loading : text.working(name, done, total))
      : phase === 'done' ? (pageState.later ? text.finishedSoFar(name) : text.finished(name))
      : phase === 'stopped' ? text.stopped
      : text.failedPage;
  $('stop').hidden = phase !== 'translating';
  $('resume').hidden = phase !== 'stopped';
}

async function askPage(message) {
  try {
    pageState = await chrome.tabs.sendMessage(tabId, message) || {phase: 'original'};
  } catch {
    pageState = {phase: 'original'};   // Not translated: the page script is not there.
  }
  render();
}

// What the page in the tab is written in, as it is now.
async function detectLanguage() {
  const reply = await chrome.runtime.sendMessage({type: 'pageLanguage', tabId});
  pageLanguage = reply?.language || null;
}

async function translate(target) {
  const reply = await chrome.runtime.sendMessage({type: 'startInTab', tabId, target});
  if (reply?.ok) await askPage({type: 'state'});
}

async function main() {
  showText();
  // The background can be stopped and started again by the browser while the
  // popup is open; the popup then connects again.
  let port = null;
  const connect = () => {
    port = chrome.runtime.connect({name: 'popup'});
    port.onMessage.addListener((message) => {
      latest = message;
      render();
    });
    port.onDisconnect.addListener(() => setTimeout(connect, 300));
    port.postMessage({type: 'hello'});
  };
  connect();

  $('download').addEventListener('click', () => port.postMessage({type: 'download'}));
  $('cancel').addEventListener('click', () => port.postMessage({type: 'cancelDownload'}));
  $('to-ja').addEventListener('click', () => translate('ja'));
  $('to-en').addEventListener('click', () => translate('en'));
  $('stop').addEventListener('click', () => askPage({type: 'stop'}));
  $('resume').addEventListener('click', () => translate(pageState.target));
  $('restore').addEventListener('click', async () => {
    await askPage({type: 'restore'});
    // The page is in its own language again (the popup was opened on the translation).
    await detectLanguage();
    render();
  });

  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  tabId = tab?.id ?? null;
  if (tabId !== null) {
    await detectLanguage();
    await askPage({type: 'state'});
    // Follow the translation while the popup is open.
    setInterval(() => {
      if (pageState.phase === 'translating') askPage({type: 'state'});
    }, 500);
  }
  render();
}

main();
