/* Regression tests: refresh/deep-link must retain selected business sector. No npm dependencies. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const start=html.indexOf('function resetFilters()');
const end=html.indexOf('function toggleSaved(',start);
assert(start>=0&&end>start,'URL navigation code is missing');
const code=html.slice(start,end);
function harness(url){
 const elements={sectorSelect:{value:'all'},searchInput:{value:''},timeSelect:{value:'all'},sortSelect:{value:'newest'},feedHeading:{scrollIntoView(){}}};
 const context={
   URL,URLSearchParams,
   location:new URL(url),state:{sector:'all',region:'all',search:'',hours:'all',sort:'newest',display:25},
   history:{},$:key=>elements[key],SECTORS:['All Sectors','Aviation & Airports','GCCs','Personal Finance'],
   REGION_NAMES:{all:'All Business News',hyderabad:'Hyderabad Business News','telugu-companies':'Telugu Companies','personal-finance':'Personal Finance'},
   render(){},refresh(){}
 };
 function navigate(_state,_title,path){context.location=new URL(path,context.location.href)}
 context.history.pushState=navigate;context.history.replaceState=navigate;
 vm.createContext(context);vm.runInContext(code,context);
 return context;
}
function run(code,ctx){return vm.runInContext(code,ctx)}
let a=harness('https://gmreddy0809-cloud.github.io/MyBusinessNews/#all');
run("setSector('Aviation & Airports')",a);
assert.equal(a.location.searchParams.get('sector'),'Aviation & Airports','Aviation deep-link missing');
let b=harness(a.location.href);run('restoreView()',b);
assert.equal(b.state.sector,'Aviation & Airports','F5 lost Aviation section');
assert.equal(b.state.region,'all');
run("setRegion('hyderabad')",a);
assert.equal(a.location.hash,'#hyderabad');
let c=harness(a.location.href);run('restoreView()',c);
assert.equal(c.state.region,'hyderabad','F5 lost Hyderabad section');
run("setRegion('telugu-companies')",a);
let d=harness(a.location.href);run('restoreView()',d);
assert.equal(d.state.region,'telugu-companies','F5 lost Telugu Companies tab');
run("setRegion('personal-finance')",a);
let e=harness(a.location.href);run('restoreView()',e);
assert.equal(e.state.region,'personal-finance','F5 lost Personal Finance tab');
e.location=new URL('https://gmreddy0809-cloud.github.io/MyBusinessNews/?sector=Aviation%20%26%20Airports&q=IndiGo&hours=24#hyderabad');
run('restoreView()',e);
assert.equal(e.state.sector,'Aviation & Airports');
assert.equal(e.state.search,'IndiGo');
assert.equal(e.state.hours,'24');
assert.equal(e.state.region,'hyderabad');
console.log('PASS: Aviation, Hyderabad, Telugu Companies, Personal Finance, search/time filters survive F5');
