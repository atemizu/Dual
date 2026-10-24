// The toolbar button opens the report page, or brings it forward if it is
// already open.
chrome.action.onClicked.addListener(async () => {
  const url = chrome.runtime.getURL('report.html');
  const [open] = await chrome.runtime.getContexts({contextTypes: ['TAB'], documentUrls: [url]});
  if (open) {
    await chrome.tabs.update(open.tabId, {active: true});
    await chrome.windows.update(open.windowId, {focused: true});
  } else {
    await chrome.tabs.create({url});
  }
});
