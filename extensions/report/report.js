// Drafts a problem report and hands it to GitHub's "new issue" page. Nothing
// leaves this page until one of the buttons is pressed.

const REPOSITORY = 'https://github.com/atemizu/Dual';
// Longer addresses than this may be cut short on the way to GitHub; the
// report is then copied instead, to be pasted in.
const MAX_ADDRESS_LENGTH = 7000;
const DRAFT_KEY = 'draft';

const STRINGS = {
  ja: {
    title: 'Dual の不具合を報告',
    lead: '項目を埋めると、お使いの環境の情報をつけた報告文ができます。わかる範囲でかまいません。',
    restored: '前回の書きかけを復元しました。',
    required: '必須',
    summaryHeading: '1. どんな不具合ですか',
    subjectLabel: '件名',
    subjectPlaceholder: '例：左のブラウザを閉じると、右のタブバーが出なくなる',
    subjectMissing: '件名を書いてください。',
    kindLabel: '種類',
    kinds: [
      ['look', '表示がおかしい'], ['action', '操作が効かない・違う動きをする'], ['hang', '固まる・落ちる'],
      ['slow', '動きが重い'], ['other', 'その他'],
    ],
    whereLabel: '関係する場所（いくつでも）',
    places: [
      ['tabs', 'タブバー'], ['divider', '左右の境目（分割バー）'], ['window', 'ウィンドウのボタン・移動・サイズ変更'],
      ['fullscreen', '全画面'], ['zen', 'フレームレス モード'], ['private', 'シークレットウィンドウ'], ['page', 'ページの表示'],
      ['menus', '設定・メニュー'], ['autoclose', 'タブの自動削除'], ['timelimit', 'サイト時間制限'],
      ['other', 'その他'],
    ],
    detailHeading: '2. くわしく教えてください',
    whatLabel: '起きたこと',
    whatPlaceholder: '何をしたときに、どうなったか',
    whatMissing: '起きたことを書いてください。',
    stepsLabel: '再現する手順',
    stepsPlaceholder: '1. \n2. \n3. ',
    expectedLabel: '本来こうなるはず、という動作',
    situationHeading: '3. そのときの状況',
    oftenLabel: '起きる頻度',
    often: [['', '選んでください'], ['always', '毎回'], ['sometimes', 'ときどき'], ['once', '1回だけ'], ['unsure', 'わからない']],
    sinceLabel: 'いつから',
    since: [['', '選んでください'], ['this', 'この版にしてから'], ['before', '以前の版から'], ['unsure', 'わからない']],
    panesLabel: '画面の使い方',
    panes: [['one', '1画面'], ['two', '左右2画面'], ['collapsed', '片方を畳んでいた']],
    zenLabel: 'フレームレス モード',
    zen: [['on', 'オン'], ['off', 'オフ'], ['unsure', 'わからない']],
    extraLabel: 'ほかに関係しそうなこと',
    extraPlaceholder: '使っている拡張機能、外部ディスプレイ、直前にした操作など',
    setupHeading: '4. お使いの環境',
    withSetupLabel: '環境の情報を報告に含める',
    previewHeading: '5. 送信される内容',
    send: 'GitHub で報告する',
    search: '似た報告を探す',
    copy: '報告文をコピー',
    clear: '入力を消す',
    clearConfirm: '入力した内容をすべて消しますか？',
    notice:
        '「GitHub で報告する」を押すと、上の内容が入った GitHub の投稿画面が開きます（GitHub のアカウントが必要です）。' +
        'そこで投稿するまで送信されません。投稿は公開されるので、個人情報やパスワードは書かないでください。',
    picture: '画面の写真は、開いた GitHub の画面に貼り付けられます（⌘⇧4 で撮影）。',
    copied: '報告文をコピーしました。',
    opened: 'GitHub の投稿画面を開きました。書きかけは、「入力を消す」を押すまでここに残ります。',
    tooLong: '長い報告なので、本文をコピーしました。開いた GitHub の画面の本文欄に貼り付けてください。',
    headings: {what: '起きたこと', steps: '再現する手順', expected: '期待した動作', situation: '状況', extra: '補足', setup: '環境'},
    situation: {kind: '種類', where: '場所', often: '頻度', since: 'いつから', panes: '画面', zen: 'フレームレス モード'},
    listJoin: '、',
    setup: {
      dual: 'Dual', browser: 'Chromium', system: 'macOS', language: '言語', displays: 'ディスプレイ',
      windows: 'ブラウザ画面（左右それぞれを1つと数えます）', unknown: '不明',
      states: {normal: '通常', minimized: '最小化', maximized: '最大化', fullscreen: '全画面'},
    },
  },
  en: {
    title: 'Report a problem in Dual',
    lead: 'Fill in what you can, and a report with details of your setup is drafted for you.',
    restored: 'Your unfinished report was restored.',
    required: 'required',
    summaryHeading: '1. What kind of problem is it?',
    subjectLabel: 'Summary',
    subjectPlaceholder: 'For example: after closing the left browser, the right tab bar no longer appears',
    subjectMissing: 'Please write a summary.',
    kindLabel: 'Kind',
    kinds: [
      ['look', 'Looks wrong'], ['action', 'Does nothing, or the wrong thing'], ['hang', 'Freezes or quits'],
      ['slow', 'Slow'], ['other', 'Something else'],
    ],
    whereLabel: 'Where (any that apply)',
    places: [
      ['tabs', 'Tab bars'], ['divider', 'Divider between the sides'], ['window', 'Window buttons, moving, resizing'],
      ['fullscreen', 'Full screen'], ['zen', 'Frameless mode'], ['private', 'Incognito windows'], ['page', 'Page display'],
      ['menus', 'Settings and menus'], ['autoclose', 'Closing unused tabs'], ['timelimit', 'Site Time Limit'],
      ['other', 'Somewhere else'],
    ],
    detailHeading: '2. Tell us more',
    whatLabel: 'What happened',
    whatPlaceholder: 'What you did, and what happened',
    whatMissing: 'Please describe what happened.',
    stepsLabel: 'Steps to make it happen again',
    stepsPlaceholder: '1. \n2. \n3. ',
    expectedLabel: 'What you expected instead',
    situationHeading: '3. The situation',
    oftenLabel: 'How often',
    often: [['', 'Choose'], ['always', 'Every time'], ['sometimes', 'Sometimes'], ['once', 'Only once'], ['unsure', 'Not sure']],
    sinceLabel: 'Since when',
    since: [['', 'Choose'], ['this', 'Since this version'], ['before', 'In earlier versions too'], ['unsure', 'Not sure']],
    panesLabel: 'How the window was used',
    panes: [['one', 'One side'], ['two', 'Both sides'], ['collapsed', 'One side hidden']],
    zenLabel: 'Frameless mode',
    zen: [['on', 'On'], ['off', 'Off'], ['unsure', 'Not sure']],
    extraLabel: 'Anything else that may matter',
    extraPlaceholder: 'Extensions you use, external displays, what you did just before',
    setupHeading: '4. Your setup',
    withSetupLabel: 'Include these details in the report',
    previewHeading: '5. What will be sent',
    send: 'Report on GitHub',
    search: 'Look for similar reports',
    copy: 'Copy the report',
    clear: 'Clear the form',
    clearConfirm: 'Clear everything you have entered?',
    notice:
        '"Report on GitHub" opens GitHub\'s new issue page with the text above filled in (a GitHub ' +
        'account is needed). Nothing is sent until you submit it there. Issues are public, so leave ' +
        'out personal details and passwords.',
    picture: 'You can paste a screenshot into the GitHub page that opens (⌘⇧4 takes one).',
    copied: 'Report copied.',
    opened: 'GitHub\'s new issue page was opened. Your draft stays here until you press "Clear the form".',
    tooLong: 'The report is long, so its text was copied. Paste it into the body of the GitHub page that opened.',
    headings: {what: 'What happened', steps: 'Steps to reproduce', expected: 'Expected', situation: 'Situation', extra: 'Notes', setup: 'Setup'},
    situation: {kind: 'Kind', where: 'Where', often: 'How often', since: 'Since', panes: 'Window', zen: 'Frameless mode'},
    listJoin: ', ',
    setup: {
      dual: 'Dual', browser: 'Chromium', system: 'macOS', language: 'Language', displays: 'Displays',
      windows: 'Browser panes (each side counts as one)', unknown: 'unknown',
      states: {normal: 'normal', minimized: 'minimized', maximized: 'maximized', fullscreen: 'full screen'},
    },
  },
};

const strings = chrome.i18n.getUILanguage().startsWith('ja') ? STRINGS.ja : STRINGS.en;
const $ = id => document.getElementById(id);
const TEXT_FIELDS = ['subject', 'what', 'steps', 'expected', 'extra'];
const SELECTS = {often: strings.often, since: strings.since};
// Pill choices: a group's id, its choices, and whether several may be picked.
const CHIPS = [
  ['kind', strings.kinds, false], ['where', strings.places, true], ['panes', strings.panes, false],
  ['zen', strings.zen, false],
];
let setupLines = [];

// Details of the setup that matter for a window and tab bar problem. All of
// it is read on this device and shown on the page before anything is sent.
async function readSetup() {
  const labels = strings.setup;
  const build = await fetch('build.json').then(reply => reply.json()).catch(() => ({}));
  const agent = await navigator.userAgentData?.getHighEntropyValues(
      ['fullVersionList', 'platformVersion', 'architecture']).catch(() => null);
  const chromium = agent?.fullVersionList?.find(brand => brand.brand === 'Chromium')?.version;
  const displays = await chrome.system.display.getInfo();
  const windows = await chrome.windows.getAll({windowTypes: ['normal']});
  return [
    `${labels.dual}: ${build.dual || labels.unknown}`,
    `${labels.browser}: ${chromium ?? labels.unknown}`,
    `${labels.system}: ${agent?.platformVersion ?? labels.unknown}` +
        (agent?.architecture ? ` (${agent.architecture})` : ''),
    `${labels.language}: ${chrome.i18n.getUILanguage()}`,
    `${labels.displays}: ` + displays.map(
        display => `${display.bounds.width}×${display.bounds.height}`).join(', '),
    `${labels.windows}: ` + windows.map(
        window => `${window.width}×${window.height} ${labels.states[window.state] ?? window.state}`).join(', '),
  ];
}

function buildChips() {
  for (const [group, choices, several] of CHIPS) {
    for (const [value, label] of choices) {
      const chip = document.createElement('label');
      chip.className = 'chip';
      const input = document.createElement('input');
      input.type = several ? 'checkbox' : 'radio';
      input.name = group;
      input.value = value;
      // A picked single choice can be unpicked by pressing it again.
      if (!several) {
        input.addEventListener('click', () => {
          if (input.dataset.picked === 'yes') {
            input.checked = false;
          }
          for (const other of document.getElementsByName(group)) {
            other.dataset.picked = other.checked ? 'yes' : '';
          }
          changed();
        });
      }
      const text = document.createElement('span');
      text.textContent = label;
      chip.append(input, text);
      $(group).append(chip);
    }
  }
}

function picked(group) {
  return [...document.getElementsByName(group)].filter(input => input.checked).map(input => input.value);
}

// Everything entered, as plain data: what the draft keeps and the report is
// made from.
function readForm() {
  const form = {withSetup: $('with-setup').checked};
  for (const id of TEXT_FIELDS) {
    form[id] = $(id).value;
  }
  for (const id of Object.keys(SELECTS)) {
    form[id] = $(id).value;
  }
  for (const [group] of CHIPS) {
    form[group] = picked(group);
  }
  return form;
}

function writeForm(form) {
  $('with-setup').checked = form.withSetup !== false;
  for (const id of TEXT_FIELDS) {
    $(id).value = form[id] ?? '';
  }
  for (const id of Object.keys(SELECTS)) {
    $(id).value = form[id] ?? '';
  }
  for (const [group] of CHIPS) {
    for (const input of document.getElementsByName(group)) {
      input.checked = (form[group] ?? []).includes(input.value);
      input.dataset.picked = input.checked ? 'yes' : '';
    }
  }
}

function labelOf(choices, value) {
  return choices.find(([choice]) => choice === value)?.[1];
}

function reportTitle() {
  return $('subject').value.trim();
}

function reportBody() {
  const form = readForm();
  const headings = strings.headings;
  const names = strings.situation;
  const situation = [
    [names.kind, labelOf(strings.kinds, form.kind[0])],
    [names.where, form.where.map(value => labelOf(strings.places, value)).join(strings.listJoin)],
    [names.often, form.often && labelOf(strings.often, form.often)],
    [names.since, form.since && labelOf(strings.since, form.since)],
    [names.panes, labelOf(strings.panes, form.panes[0])],
    [names.zen, labelOf(strings.zen, form.zen[0])],
  ].filter(([, answer]) => answer).map(([name, answer]) => `- ${name}: ${answer}`).join('\n');
  const sections = [
    [headings.what, form.what.trim()],
    [headings.steps, form.steps.trim()],
    [headings.expected, form.expected.trim()],
    [headings.situation, situation],
    [headings.extra, form.extra.trim()],
    [headings.setup, form.withSetup ? setupLines.map(line => `- ${line}`).join('\n') : ''],
  ];
  return sections.filter(([, text]) => text).map(([heading, text]) => `### ${heading}\n${text}`).join('\n\n') + '\n';
}

function showPreview() {
  $('preview-title').textContent = reportTitle();
  $('preview').textContent = reportBody();
  $('setup').classList.toggle('left-out', !$('with-setup').checked);
}

function changed() {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(readForm()));
  showPreview();
}

function showResult(text) {
  $('result').textContent = text;
  $('result').hidden = false;
}

// Points at the first required field left empty; true if none is.
function complete() {
  let first = null;
  for (const id of ['subject', 'what']) {
    const missing = !$(id).value.trim();
    $(`${id}-missing`).hidden = !missing;
    first ??= missing ? $(id) : null;
  }
  first?.focus();
  return !first;
}

document.documentElement.lang = strings === STRINGS.ja ? 'ja' : 'en';
document.title = strings.title;
for (const [id, key] of [
       ['title', 'title'], ['lead', 'lead'], ['restored', 'restored'], ['summary-heading', 'summaryHeading'],
       ['subject-label', 'subjectLabel'], ['subject-required', 'required'], ['subject-missing', 'subjectMissing'],
       ['kind-label', 'kindLabel'], ['where-label', 'whereLabel'], ['detail-heading', 'detailHeading'],
       ['what-label', 'whatLabel'], ['what-required', 'required'], ['what-missing', 'whatMissing'],
       ['steps-label', 'stepsLabel'], ['expected-label', 'expectedLabel'], ['situation-heading', 'situationHeading'],
       ['often-label', 'oftenLabel'], ['since-label', 'sinceLabel'], ['panes-label', 'panesLabel'],
       ['zen-label', 'zenLabel'], ['extra-label', 'extraLabel'], ['setup-heading', 'setupHeading'],
       ['with-setup-label', 'withSetupLabel'], ['preview-heading', 'previewHeading'], ['send', 'send'],
       ['search', 'search'], ['copy', 'copy'], ['clear', 'clear'], ['notice', 'notice'], ['picture', 'picture'],
     ]) {
  $(id).textContent = strings[key];
}
$('subject').placeholder = strings.subjectPlaceholder;
$('what').placeholder = strings.whatPlaceholder;
$('steps').placeholder = strings.stepsPlaceholder;
$('extra').placeholder = strings.extraPlaceholder;
for (const [id, choices] of Object.entries(SELECTS)) {
  for (const [value, label] of choices) {
    $(id).add(new Option(label, value));
  }
}
buildChips();

const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null');
if (draft) {
  writeForm(draft);
  $('restored').hidden = !TEXT_FIELDS.some(id => draft[id]?.trim());
}
document.querySelector('main').addEventListener('input', changed);

$('send').addEventListener('click', async () => {
  if (!complete()) {
    return;
  }
  const head = `${REPOSITORY}/issues/new?labels=bug&title=${encodeURIComponent(reportTitle())}`;
  const withBody = `${head}&body=${encodeURIComponent(reportBody())}`;
  if (withBody.length <= MAX_ADDRESS_LENGTH) {
    chrome.tabs.create({url: withBody});
    showResult(strings.opened);
    return;
  }
  await navigator.clipboard.writeText(reportBody());
  showResult(strings.tooLong);
  chrome.tabs.create({url: head, active: false});
});
$('search').addEventListener('click', () => {
  if (!reportTitle()) {
    $('subject-missing').hidden = false;
    $('subject').focus();
    return;
  }
  chrome.tabs.create({url: `${REPOSITORY}/issues?q=${encodeURIComponent(`is:issue ${reportTitle()}`)}`});
});
$('copy').addEventListener('click', async () => {
  if (!complete()) {
    return;
  }
  await navigator.clipboard.writeText(`${reportTitle()}\n\n${reportBody()}`);
  showResult(strings.copied);
});
$('clear').addEventListener('click', () => {
  if (!confirm(strings.clearConfirm)) {
    return;
  }
  localStorage.removeItem(DRAFT_KEY);
  writeForm({});
  $('restored').hidden = true;
  $('result').hidden = true;
  showPreview();
});

readSetup().then(lines => {
  setupLines = lines;
  for (const line of lines) {
    const item = document.createElement('li');
    item.textContent = line;
    $('setup').append(item);
  }
  showPreview();
});
showPreview();
