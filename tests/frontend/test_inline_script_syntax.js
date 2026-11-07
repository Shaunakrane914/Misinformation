'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const folder = path.resolve(__dirname, '../../frontend');
for (const file of fs.readdirSync(folder).filter(name => name.endsWith('.html'))) {
  const html = fs.readFileSync(path.join(folder, file), 'utf8');
  for (const [index, match] of [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)].entries()) {
    if (/\bsrc\s*=|application\/ld\+json|application\/json/i.test(match[1])) continue;
    new vm.Script(match[2], {filename: file + ':script' + index});
  }
}
console.log('ALL INLINE PAGE SCRIPTS PARSE');
