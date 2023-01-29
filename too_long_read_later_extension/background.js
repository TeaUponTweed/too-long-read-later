chrome.tabs.onCreated.addListener((newTab) => {
  chrome.tabs.query({windowType:'normal'}, function(tabs) {
    currentWindowTabCount = 0;
    tabs.map((tab) => {
      if ((tab.windowId == newTab.windowId) && (!tab.pinned)) {
        currentWindowTabCount += 1
      }
    })
    if (currentWindowTabCount > 10) {
      chrome.tabs.remove(newTab.id, () => {
        chrome.notifications.create(
        "test", {
            type: 'basic',
            iconUrl: 'images/10.png',
            title: 'Too Many Tabs!',
            message: 'Close some. For all our sanity.',
            priority: 2,
            requireInteraction: false,
        }, () => console.log("Too many tabs!"))
      });
    }
  });
});
