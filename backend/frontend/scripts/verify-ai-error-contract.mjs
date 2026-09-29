import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import axios from "axios";

const source = readFileSync(new URL("../src/components/ai/AiSiteAssistant.vue", import.meta.url), "utf8").replace(/\r\n/g, "\n");
const api = readFileSync(new URL("../src/utils/api.js", import.meta.url), "utf8").replace(/\r\n/g, "\n");
const submit = source.match(/async function submitRecommendation\(\) \{[\s\S]*?\n\}/)?.[0];
const unwrap = api.match(/export function unwrapResponse\(response\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(submit, "Exercise the current component's complete submit function");
assert.ok(unwrap, "Use the actual shared response unwrapping function");
const unwrapResponse = new Function(`${unwrap.replace("export ", "")}; return unwrapResponse;`)();
const fixtures = JSON.parse(readFileSync(new URL("../../../docs/data/stage1-ai-response-contract.json", import.meta.url), "utf8")).cases;
assert.equal(fixtures.filter((item) => item.status === 400).length, 6);
for (const fixture of fixtures) {
  const query = { value: "接口调试" }, isLoading = { value: false }, status = { value: "idle" };
  const errorMessage = { value: "" }, results = { value: [] };
  const aiAPI = { recommendSites: async (payload) => {
    assert.deepEqual(payload, { query: query.value, limit: 5 });
    const response = { status: fixture.status, data: fixture.body };
    if (!axios.defaults.validateStatus(response.status)) throw { response };
    return response;
  } };
  const understanding = { value: {} };
  const run = new Function("query", "isLoading", "status", "errorMessage", "results", "aiAPI", "unwrapResponse", "understanding", `const loggedIn = { value: true }, requestGeneration = { value: 0 }; const goToLogin = () => { throw new Error("unexpected login"); }; ${submit}; return submitRecommendation;`)(query, isLoading, status, errorMessage, results, aiAPI, unwrapResponse, understanding);
  await run();
  assert.equal(status.value, fixture.expected_state, fixture.case);
  assert.equal(isLoading.value, false, fixture.case);
  if (fixture.expected_state === "error") {
    assert.equal(errorMessage.value, fixture.body.message, fixture.case);
    assert.deepEqual(results.value, [], fixture.case);
    assert.equal(fixture.body.success, false);
  } else if (fixture.expected_state === "success") {
    assert.deepEqual(results.value, fixture.body.data.items);
    assert.ok(results.value.length);
  } else {
    assert.deepEqual(results.value, []);
  }
  console.log(`PASS ${fixture.case}: HTTP ${fixture.status} -> ${status.value}`);
}
