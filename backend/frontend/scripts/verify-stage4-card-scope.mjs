import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parse } from '@vue/compiler-sfc';
import { compile,createSSRApp,h } from 'vue';
import { renderToString } from 'vue/server-renderer';
const template=parse(readFileSync(new URL('../src/components/site/SiteCard.vue',import.meta.url),'utf8')).descriptor.template.content;
const render=compile(template);
async function card(activeRecommendation,blocked) {
  const ctx={site:{id:17,name:'Isolated resource',url:'https://fixture.invalid/item',feedback_enabled:true},activeRecommendation,
    recommendationPreferences:{excluded:()=>blocked},isCareerVariant:true,isCategoryVariant:false,isCompactCategoryVariant:false,
    selectable:false,selected:false,hideActions:false,favorited:true,favoritePending:false,normalizedSiteUrl:'https://fixture.invalid/item',siteDescription:'文献检索',
    handleCardClick(){},openSite(){}};
  const app=createSSRApp({render,setup:()=>ctx});
  app.component('RecommendationFeedback',{render:()=>h('button',{'aria-label':'推荐反馈'})});
  app.component('FavoriteStarButton',{props:['site'],setup:props=>()=>h('button',{'aria-label':`收藏 ${props.site.name}`})});
  app.component('SiteLogo',{render:()=>h('span')});
  app.component('AppTooltip',{props:['content','disabled','showOnOverflow'],setup:(_,context)=>()=>context.slots.default?.()});
  app.component('RouterLink',{render:()=>h('a')});
  return renderToString(app);
}
const active=await card(true,true);assert.ok(!active.includes('Isolated resource'));
const deliberate=await card(false,true);assert.ok(deliberate.includes('Isolated resource'));assert.ok(deliberate.includes('收藏 Isolated resource'));assert.ok(!deliberate.includes('推荐反馈'));
assert.ok((await card(true,false)).includes('推荐反馈'));
console.log('PASS actual SiteCard template: blocked active recommendation hidden; search/favorites/detail retain resource and favorite button even with stale recommendation metadata');
