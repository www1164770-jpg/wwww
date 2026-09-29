import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../src/stores/favorites.js',import.meta.url),'utf8');
const segment=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};

export async function verifyFavoriteRaces(){
  for(const operation of ['add','remove']) for(const failed of [false,true]) for(const switched of [false,true]){
    const request=deferred(),calls=[];let current=true;
    const dependencies={
      syncUserScope:()=> 'A',scopeEpoch:1,ownsScope:()=>current,getFavoriteKey:()=> 'id:9',normalizeFavorite:x=>x,
      captureStateSnapshot:()=>({}),beginPending:()=>true,endPending:()=>calls.push('clear'),
      error:{value:null},items:{value:[]},favoriteCount:{value:0},hasSnapshot:{value:false},loadedUserId:{value:''},activeUserId:{value:''},status:{value:''},
      persistCache:()=>calls.push('cache'),favoriteAPI:{addFavorite:()=>request.promise,removeFavorite:()=>request.promise},
      reconcileFavoriteResponse:()=>calls.push('reconcile'),trackFavorite:()=>calls.push('event'),
      isAlreadyDesiredFavoriteState:()=>false,restoreStateSnapshot:()=>calls.push('rollback'),matchesFavorite:()=>false,
    };
    const code=operation==='add'?segment('  async function addFavorite(', '  async function removeFavorite('):segment('  async function removeFavorite(', '  function isFavorite(');
    const fn=new Function(...Object.keys(dependencies),code+`;return ${operation}Favorite;`)(...Object.values(dependencies));
    const pending=fn({id:9});calls.length=0;current=!switched;
    if(failed)request.reject(new Error('controlled failure'));else request.resolve({});
    if(failed&&!switched)await assert.rejects(pending);else await pending;
    if(switched)assert.deepEqual(calls,[],`${operation}: old success/failure must not change B, emit events, rollback or clear B pending`);
    else {assert.equal(calls.filter(x=>x==='clear').length,1,`${operation}: owner pending always cleared`);assert.ok(calls.includes(failed?'rollback':'reconcile'));}
  }
  for(const failed of [false,true]){
    const request=deferred(),calls=[];let current=true;
    const desired=new Map([['id:9',true]]),confirmed=new Map(),promises=new Map();
    const d={scopeEpoch:1,ownsScope:()=>current,desiredStateByKey:desired,confirmedStateByKey:confirmed,syncPromiseByKey:promises,
      favoriteAPI:{addFavorite:()=>request.promise},reconcileFavoriteResponse:()=>calls.push('reconcile'),persistFavoriteCacheSoon:()=>calls.push('cache'),
      isAlreadyDesiredFavoriteState:()=>false,applyFavoriteStateLocally:()=>calls.push('rollback'),endPending:()=>calls.push('clear')};
    const fn=new Function(...Object.keys(d),segment('  function scheduleFavoriteSync(', '  async function toggleFavorite(')+';return scheduleFavoriteSync;')(...Object.values(d));
    const pending=fn({id:9},'id:9','','A');current=false;desired.clear();confirmed.clear();promises.clear();
    const bPromise=Promise.resolve('B');promises.set('id:9',bPromise);desired.set('id:9',false);
    if(failed)request.reject(new Error('controlled failure'));else request.resolve({});
    assert.equal(await pending,false);assert.deepEqual(calls,[]);assert.equal(promises.get('id:9'),bPromise);assert.equal(desired.get('id:9'),false);assert.equal(confirmed.size,0);
  }
  const api=readFileSync(new URL('../src/utils/api.js',import.meta.url),'utf8');let token='B',sent=0;
  const notifyCode=api.slice(api.indexOf('function notifyFavoriteStateChange('),api.indexOf('export const favoriteAPI'));
  const notify=new Function('getAccessToken','getFavoriteTarget','window','CustomEvent',notifyCode+';return notifyFavoriteStateChange;')(()=>token,()=>({siteId:9,url:'https://fixture.test'}),{dispatchEvent:()=>sent++},class{constructor(...args){this.args=args}});
  notify({},true,'A');assert.equal(sent,0,'late A notification must not reach B');notify({},true,'B');assert.equal(sent,1,'current account notification preserved');
  return true;
}
if(process.argv[1]?.endsWith('verify-favorite-account-race.mjs')){await verifyFavoriteRaces();console.log('PASS favorite races: owner success/failure cleanup, stale mutation/rollback/event suppression, B pending preserved, session notification');}

