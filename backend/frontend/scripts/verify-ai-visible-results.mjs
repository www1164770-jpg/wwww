import assert from 'node:assert/strict';
import { compile, createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { parse } from '@vue/compiler-sfc';
import { assistant, read, harness } from './ai-business-contract.mjs';

// Compile the actual template. Only icons and the already separately tested
// favorite component are substituted; all conditionals/text/props are real.
const template=parse(assistant).descriptor.template.content;
const render=compile(template);
const report=JSON.parse(read('../../docs/recommendation/stage3-isolated-verification.json'));
const cases=report.responses.map(row=>row.data);
cases.push({items:[],requirements:{conditions:[]},clarifications:[],notice:'',degraded:false});
cases.push([{id:91,name:'Legacy array',url:'https://fixture.invalid/legacy',reason:'legacy reason'}]);
cases.push({items:[{id:92,name:'Legacy object',url:'https://fixture.invalid/object',reason:'legacy reason'}]});
let rendered=0;
for (const data of cases) {
  const test=harness({recommendSites:async()=>({data:{data}})});
  await test.submitRecommendation();
  const ctx=Object.fromEntries(Object.entries(test.state).map(([k,v])=>[k,v.value]));
  Object.assign(ctx,{isOpen:true,examples:[],canSubmit:true,isComposing:false,
    fillExample(){},closeAssistant(){},handleLauncher(){},handleKeydown(){},submitRecommendation(){},goToLogin(){},emit(){},
    getSiteLogo:()=>'',hasLogoFailed:()=>false,getTextLogo:site=>site.name.slice(0,1),siteDescription:site=>site.summary||''});
  const favorites=[];
  const app=createSSRApp({render,setup:()=>ctx});
  for (const name of new Set([...template.matchAll(/<([A-Z][A-Za-z0-9]+)/g)].map(m=>m[1]))) {
    app.component(name,name==='FavoriteStarButton'?{props:['site'],setup:props=>()=>{favorites.push(props.site.id);return h('button',{'aria-label':`收藏 ${props.site.name}`});}}:{render:()=>h('svg')});
  }
  const html=await renderToString(app);rendered++;
  if (ctx.status==='success') {
    assert.deepEqual(favorites,ctx.results.map(site=>site.id));
    for (const site of ctx.results) {
      assert.ok(html.includes(site.name));assert.ok(html.includes(site.reason));assert.ok(html.includes('访问网站'));
      if(site.match_status) assert.ok(html.includes({full:'完全符合',partial:'部分符合',unverified:'信息待核实'}[site.match_status]));
      for(const label of site.unknown_conditions||[]) assert.ok(html.includes(`待核实：${label}`));
      for(const label of site.unmet_conditions||[]) assert.ok(html.includes(`未满足：${label}`));
    }
  }
  if(ctx.status==='empty') assert.ok(html.includes('暂未找到匹配网站'));
  for(const c of ctx.understanding.conditions) assert.ok(html.includes(c.label) && html.includes(c.evidence));
  for(const c of ctx.understanding.clarifications) assert.ok(html.includes(c));
  if(ctx.understanding.degraded) assert.ok(html.includes('智能理解暂不可用或检索已降级'));
}
console.log(`PASS ${rendered} compiled Vue template renders: conditions, unknown/partial, empty, clarification, degradation, favorite props, legacy success`);
