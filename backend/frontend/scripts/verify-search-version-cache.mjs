import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(root, 'src/stores/search.js'), 'utf8')
  .replace(/^import .*;\r?\n/gm, '').replaceAll('export ', '');
let generation = 'search-v2:1:1', cacheable = true, available = true, calls = 0;
let items = [{ id: 1, name: 'Fixture' }];
const api = {
  async version() {
    if (!available) throw new Error('unavailable');
    return { dataVersion: generation, cacheable };
  },
  async search() { calls++; return { query: 'fixture', items, dataVersion: generation, pagination: { total: items.length } }; },
};
const store = new Function('defineStore','reactive','ref','normalizeWebsite','searchAPI','unwrapResponse','getAccessToken','getStoredUserInfo',
  source + '\nreturn useSearchStore();')(
    (_name, factory) => factory, x => x, value => ({ value }), x => x, api, x => x, () => null, () => ({}),
  );
assert.equal((await store.search({q:'fixture'})).fromCache, false);
assert.equal((await store.search({q:'fixture'})).fromCache, true);
assert.equal(calls, 1);
generation = 'search-v2:2:1'; cacheable = false; items = [];
assert.deepEqual((await store.search({q:'fixture'})).payload.items, []);
assert.equal((await store.search({q:'fixture'})).fromCache, false);
generation = 'search-v2:2:2'; cacheable = true;
assert.equal((await store.search({q:'fixture'})).fromCache, false);
assert.equal((await store.search({q:'fixture'})).fromCache, true);
available = false;
await assert.rejects(store.search({q:'fixture'}), /unavailable/);
console.log('PASS actual search store: shared version, cache hit, immediate unpublish, pending bypass, indexed generation, unavailable validation');
