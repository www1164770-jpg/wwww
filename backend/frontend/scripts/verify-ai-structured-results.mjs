import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8').replace(/\r\n/g, '\n');
const source = read('../src/components/ai/AiSiteAssistant.vue');
const submit = source.match(/async function submitRecommendation\(\) \{[\s\S]*?\n\}/)?.[0];
const unwrap = read('../src/utils/api.js').match(/export function unwrapResponse\(response\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(submit); assert.ok(unwrap);
const unwrapResponse = new Function(`${unwrap.replace('export ', '')}; return unwrapResponse;`)();
const report = JSON.parse(read('../../../docs/recommendation/stage3-isolated-verification.json'));
assert.equal(report.status, 'passed');
assert.ok(report.responses.some(row => row.data.clarifications.length));
assert.ok(report.responses.some(row => row.data.degraded));
assert.ok(report.responses.some(row => row.data.items.some(item => item.unknown_conditions.length)));
for (const fixture of report.responses) {
  const query = { value: fixture.query }, isLoading = { value: false }, status = { value: 'idle' };
  const errorMessage = { value: '' }, results = { value: [] }, understanding = { value: {} };
  const aiAPI = { recommendSites: async payload => {
    assert.deepEqual(payload, { query: fixture.query, limit: 5 });
    return { data: { success: true, code: 200, data: fixture.data } };
  } };
  const run = new Function('query', 'isLoading', 'status', 'errorMessage', 'results', 'aiAPI', 'unwrapResponse', 'understanding', `const loggedIn = { value: true }, requestGeneration = { value: 0 }; const goToLogin = () => { throw new Error("unexpected login"); }; ${submit}; return submitRecommendation;`)(query, isLoading, status, errorMessage, results, aiAPI, unwrapResponse, understanding);
  await run();
  assert.equal(isLoading.value, false);
  assert.equal(status.value, fixture.data.clarifications.length ? 'clarification' : fixture.data.items.length ? 'success' : 'empty');
  assert.deepEqual(results.value, fixture.data.items);
  assert.deepEqual(understanding.value.conditions, fixture.data.requirements.conditions);
  assert.equal(understanding.value.degraded, fixture.data.degraded);
  assert.equal(understanding.value.notice, fixture.data.notice);
}
assert.ok(source.includes('unknown_conditions'));
assert.ok(source.includes('unmet_conditions'));
assert.ok(!source.includes('v-html'));
console.log(`PASS ${report.responses.length} real isolated API response replays (component submit logic; no browser rendering)`);
