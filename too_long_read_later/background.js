chrome.action.onClicked.addListener((tab) => {
  chrome.identity.getProfileUserInfo({accountStatus: 'ANY'},(userInfo) => {
  var encodedUrl = encodeURIComponent(tab.url);
  // chrome.action.setPopup({popup:'./sending.html', tabId: tab.id}, () => {
  //   chrome.action.openPopup();
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
      // var views = chrome.extension.getViews({
      //     type: "popup"
      // });
      // for (var i = 0; i < views.length; i++) {
      //     views[i].document.getElementById('extension_main').innerHTML =  "<p>Sent!</p>";
      // }
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/images/tlrl.png',
        title: `TLRL`,
        message: "Sent!",
        priority: 1
      });
      // document.getElementById('extension_main').innerHTML = "<p>Sent!</p>"
      // alert("Sent!")
      // chrome.action.setPopup({popup:'./sent.html', tabId: tab.id}, () => chrome.action.openPopup());
      console.log(data);
    })
    .catch(error => {
      // chrome.action.setPopup({popup:'./issue.html', tabId: tab.id}, () => chrome.action.openPopup());
      // for (var i = 0; i < views.length; i++) {
      //     views[i].document.getElementById('extension_main').innerHTML =  "<p>There was an issue. Refresh and try again.</p>";
      // }
      // document.getElementById('extension_main').innerHTML = "<p>There was an issue. Refresh and try again.</p>"
      // alert("There was an issue. Please try again.")
          chrome.notifications.create({
        type: 'basic',
        iconUrl: '/images/tlrl.png',
        title: `TLRL`,
        message: "There was an issue. Refresh and try again.",
        priority: 1
      })
      // window.location.href="issue.html";
      console.error('Error:', error);
    });
  });
});  

