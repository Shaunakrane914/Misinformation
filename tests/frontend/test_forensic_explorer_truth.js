'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const context = vm.createContext({ window: {} });
const source = fs.readFileSync(
  path.resolve(__dirname, '../../frontend/forensic-explorer.js'), 'utf8'
);
vm.runInContext(source, context);

const explorer = new context.window.ForensicExplorer(null);
const empty = explorer.renderFindingsTab([]);
assert(empty.includes('No grounded findings were returned'));
assert(empty.includes('does not establish that the claim is true'));
assert(!empty.includes('standard consistency'));
console.log('FORENSIC EXPLORER TRUTH CONTRACTS PASSED');
