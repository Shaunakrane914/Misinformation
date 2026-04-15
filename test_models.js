
const key = 'AIzaSyA2Xzuss7dr7g040IdUjN_XLcslufUootM';
const versions = ['v1beta', 'v1'];
const models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash-8b'];
async function test() {
  for (let m of models) {
    for (let v of versions) {
      let url = 'https://generativelanguage.googleapis.com/' + v + '/models/' + m + ':generateContent?key=' + key;
      try {
        let r = await fetch(url, {method:'POST', body: JSON.stringify({contents: [{parts: [{text: 'Hi'}]}]}), headers:{'Content-Type': 'application/json'}});
        console.log(m, v, r.status);
      } catch(e) { }
    }
  }
}
test();

