// browser.browserAction.onClicked.addListener(async (info, tab) => {

chrome.action.onClicked.addListener((tab) => {
  chrome.identity.getProfileUserInfo({accountStatus: 'ANY'},(userInfo) => {
    var encodedUrl = encodeURIComponent(tab.url);
    fetch('https://news.derivativeworks.co/tlrl', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: encodedUrl,
        email: userInfo.email
      })
    })
    .then(res => res.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
  });
});
