// chrome.action.onClicked.addListener((tab) => {
  console.log("Here")
  chrome.identity.getProfileUserInfo({accountStatus: 'ANY'},(userInfo) => {
    var encodedUrl = encodeURIComponent(tab.url);
    console.log(encodedUrl);
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
    .then(data => {
      // window.location.href="sent.html";
      document.getElementById('extension_main').innerHTML = "<p>Sent!</p>"
      // chrome.action.setPopup({popup:'./sent.html', tabId: tab.id}, () => chrome.action.openPopup());
      console.log(data);
    })
    .catch(error => {
      // chrome.action.setPopup({popup:'./issue.html', tabId: tab.id}, () => chrome.action.openPopup());
      document.getElementById('extension_main').innerHTML = "<p>There was an issue. Refresh and try again.</p>"
      // window.location.href="issue.html";
      console.error('Error:', error);
    });
  });
// })