import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

export const read = path => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8').replace(/\r\n/g, '\n');
export const assistant = read('src/components/ai/AiSiteAssistant.vue');
export function fn(source, name) {
  const body = source.match(new RegExp(`(?:async )?function ${name}\\([^]*?\\n\\}`))?.[0];
  assert.ok(body, `actual function ${name} must exist`);
  return body;
}
export function harness(api = { recommendSites: async () => ({data:{data:{items:[]}}}) }) {
  const state = Object.fromEntries(Object.entries({ loggedIn:true, requestGeneration:0, query:'接口调试', isLoading:false,
    status:'initial', errorMessage:'', results:[], understanding:{conditions:[],clarifications:[],notice:'',degraded:false} }).map(([k,v])=>[k,{value:v}]));
  const calls={login:[],toggle:0,close:0};
  const router={push:value=>calls.login.push(value)};
  const assistantStore={toggleAssistant:()=>calls.toggle++,closeAssistant:()=>calls.close++};
  const unwrapSource=fn(read('src/utils/api.js'),'unwrapResponse');
  const unwrapResponse=new Function(`${unwrapSource};return unwrapResponse;`)();
  const names=['submitRecommendation','handleLauncher','goToLogin','closeAssistant','toggleAssistant','invalidateAssistantSession'];
  const actions=new Function(...Object.keys(state),'aiAPI','router','assistantStore','unwrapResponse',
    `${names.map(n=>fn(assistant,n)).join('\n')};return {${names.join(',')}};`)(...Object.values(state),api,router,assistantStore,unwrapResponse);
  return {state,calls,...actions};
}

export async function verifyEntryBusinessContract() {
  const app=read('src/App.vue'), home=read('src/views/Home.vue'), header=read('src/components/layout/AppHeader.vue');
  assert.equal((`${app}\n${home}\n${header}`.match(/<AiSiteAssistant\b/g)||[]).length,1,'exactly one global instance');
  assert.match(app,/<AiSiteAssistant\s+@visit="visitAiRecommendation"\s*\/>/);
  assert.match(assistant,/watch\(\(\) => \[loggedIn.value, userStore.userInfo\?\.id \|\| userStore.userInfo\?\.username\], invalidateAssistantSession\)/,'global account changes invalidate session');
  assert.ok(!/localStorage|Authorization|Bearer\s/.test(assistant),'component never owns credentials/header construction');
  assert.equal((assistant.match(/getAccessToken\(/g)||[]).length,1,'only shared auth state validation reads token');
  assert.match(assistant,/userStore.isLoggedIn && isValidAuthToken\(getAccessToken\(\)\)/);
  assert.ok(!/getAccessToken|Authorization|Bearer|fetch\(|axios/.test(fn(assistant,'submitRecommendation')),'submit delegates auth to shared API');
  assert.match(home,/class="[^"]*\bai-login-prompt\b[^"]*"/);
  assert.match(home,/@click="handleAiAssistantEntry"/);
  assert.ok(home.includes('登录并使用知航AI助手'));
  assert.match(assistant,/class="ai-site-assistant__launcher"[^]*?aria-label="打开知航AI助手"[^]*?@click="handleLauncher"/);
  let requests=0, resolve;
  const h=harness({recommendSites:()=>{requests++;return new Promise(r=>resolve=r);}});
  h.state.loggedIn.value=false;
  h.handleLauncher(); await h.submitRecommendation();
  assert.deepEqual(h.calls.login,[{path:'/login',query:{redirect:'/'}},{path:'/login',query:{redirect:'/'}}]);
  assert.equal(h.calls.toggle,0);assert.equal(requests,0,'signed-out cannot request or open panel');
  h.state.loggedIn.value=true;h.handleLauncher();assert.equal(h.calls.toggle,1);
  const pending=h.submitRecommendation();assert.equal(requests,1);assert.equal(h.state.isLoading.value,true);
  h.state.loggedIn.value=false;h.invalidateAssistantSession();
  resolve({data:{data:{items:[{id:777,name:'previous account result'}]}}});await pending;
  assert.deepEqual(h.state.results.value,[]);assert.equal(h.state.query.value,'');
  assert.equal(h.state.status.value,'initial');assert.equal(h.state.isLoading.value,false);assert.equal(h.calls.close,1);
  const resolvers=[];
  const switching=harness({recommendSites:()=>new Promise(r=>resolvers.push(r))});
  const old=switching.submitRecommendation();
  switching.invalidateAssistantSession();switching.state.query.value='文献检索';
  const fresh=switching.submitRecommendation();
  resolvers[0]({data:{data:{items:[{id:1}]}}});await old;
  assert.equal(switching.state.isLoading.value,true,'old completion cannot clear new request loading');
  assert.deepEqual(switching.state.results.value,[]);
  resolvers[1]({data:{data:{items:[{id:2}]}}});await fresh;
  assert.deepEqual(switching.state.results.value,[{id:2}]);assert.equal(switching.state.isLoading.value,false);
  const visited=[],routes=[];
  const visit=new Function('normalizeUrl','openVisitedSite','router',`${fn(app,'visitAiRecommendation')};return visitAiRecommendation;`)(url=>url, (...args)=>visited.push(args),{push:path=>routes.push(path)});
  const site={id:7,name:'fixture',url:'https://fixture.invalid/tool'};visit(site);visit({id:8});
  assert.deepEqual(visited[0][0],site);assert.deepEqual(routes,['/site/8']);
  return true;
}
