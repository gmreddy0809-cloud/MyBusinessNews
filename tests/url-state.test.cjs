/* Regression tests: refresh/deep-link must retain selected business sector. No npm dependencies. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
// Guard the compact news-first experience from future header/content bloat.
assert(html.indexOf('id="newsList"')<html.indexOf('id="metricStories"'),'Metrics must appear below news');
assert(html.indexOf('id="newsList"')<html.indexOf('id="pulseTelugu"'),'Newsroom shortcuts must appear below news');
assert(html.includes('<details class="source-disclosure">'),'Official sources should be collapsed above news');
assert(html.includes('id="advancedFilters"'),'Advanced filters must be user-expandable');
assert(html.includes('.region-tabs{position:relative;display:flex!important;align-items:center;justify-content:flex-start;flex-wrap:wrap!important;overflow:visible!important'),
       'Region tabs must wrap without sideways scrolling');
assert(html.includes('.region-tab[data-mobile-extra="true"]{display:none!important}'),
       'Secondary mobile regions should move into More rather than require scrolling');
assert(html.includes('id="moreRegionTabs"'),'Mobile More menu must provide access to secondary tabs');
assert(html.includes('.sector-quickbar{display:none!important}'),'Sector quickbar should not introduce sideways scrolling');
for(const [region,label] of [['andhra-pradesh','AP'],['telangana','TG'],['personal-finance','PF']]){
 const expression=new RegExp('data-region="'+region+'"[^>]*>'+label+'<\\/button>');
 assert(expression.test(html),'Missing abbreviated nav label for '+region);
}
const start=html.indexOf('function resetFilters()');
const end=html.indexOf('function toggleSaved(',start);
assert(start>=0&&end>start,'URL navigation code is missing');
const code=html.slice(start,end);
function harness(url){
 const elements={sectorSelect:{value:'all'},searchInput:{value:''},timeSelect:{value:'all'},sortSelect:{value:'newest'},originSelect:{value:'all'},feedHeading:{scrollIntoView(){}}};
 const context={
   URL,URLSearchParams,
   location:new URL(url),state:{sector:'all',region:'all',search:'',hours:'all',sort:'newest',origin:'all',miscTopic:'all',miscArea:'all',regionalState:'all',realtyType:'all',display:25},
   history:{},$:key=>elements[key],SECTORS:['All Sectors','Aviation & Airports','GCCs','Personal Finance'],
   REGION_NAMES:{all:'All Business News',hyderabad:'Hyderabad Business News','telugu-companies':'Telugu Companies','personal-finance':'Personal Finance','hyderabad-realty':'Hyderabad Real Estate','x-watch':'X Business Watch','avi-ivi':'అవీ ఇవీ','telugu-states':'AP + TG General News','telugu-patrikalu':'తెలుగు పత్రికలు','english-magazines':'English Magazines'},
   MISC_TOPICS:[['all','Everything'],['Health & Wellbeing','Health'],['Science & Space','Science']],MISC_AREAS:[['all','Everywhere'],['telugu','Telugu'],['world','World']],PUBLISHER_TOPIC_OPTIONS:[['all','Everything'],['Health & Wellbeing','Health'],['Lifestyle & Living','Lifestyle']],
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
run("setRegion('hyderabad-realty')",a);
a.state.realtyType='Retail';run('saveView(true)',a);
assert.equal(a.location.searchParams.get('realty'),'Retail','Hyderabad Realty filter URL missing');
let realtyReload=harness(a.location.href);run('restoreView()',realtyReload);
assert.equal(realtyReload.state.region,'hyderabad-realty','F5 lost Hyderabad Realty tab');
assert.equal(realtyReload.state.realtyType,'Retail','F5 lost retail-property category');
run("setRegion('personal-finance')",a);
let e=harness(a.location.href);run('restoreView()',e);
assert.equal(e.state.region,'personal-finance','F5 lost Personal Finance tab');
run("setRegion('x-watch')",a);
let x=harness(a.location.href);run('restoreView()',x);
assert.equal(x.state.region,'x-watch','F5 lost X Business Watch tab');
run("setRegion('avi-ivi')",a);
assert.equal(a.location.hash,'#avi-ivi','Avii Ivii deep link missing');
a.state.miscTopic='Health & Wellbeing';
a.state.miscArea='telugu';
run('saveView(true)',a);
assert.equal(a.location.searchParams.get('topic'),'Health & Wellbeing');
assert.equal(a.location.searchParams.get('area'),'telugu');
let magazine=harness(a.location.href);run('restoreView()',magazine);
assert.equal(magazine.state.region,'avi-ivi','F5 lost Avii Ivii tab');
assert.equal(magazine.state.miscTopic,'Health & Wellbeing','F5 lost magazine topic');
assert.equal(magazine.state.miscArea,'telugu','F5 lost magazine area');
assert(html.includes('id="miscHub"'),'Avii Ivii panel missing');
assert(html.includes('data-region="telugu-patrikalu"'),'Telugu Patrikalu tab missing');
assert(html.includes('data-region="english-magazines"'),'English Magazines tab missing');
run("setRegion('telugu-states')",a);
a.state.regionalState='andhra-pradesh';run('saveView(true)',a);
assert.equal(a.location.searchParams.get('state'),'andhra-pradesh','AP reader filter URL missing');
let apReload=harness(a.location.href);run('restoreView()',apReload);
assert.equal(apReload.state.region,'telugu-states','F5 lost AP + TG general news desk');
assert.equal(apReload.state.regionalState,'andhra-pradesh','F5 lost Andhra Pradesh subfilter');
a.state.regionalState='telangana';run('saveView(true)',a);
let tgReload=harness(a.location.href);run('restoreView()',tgReload);
assert.equal(tgReload.state.regionalState,'telangana','F5 lost Telangana subfilter');
run("setRegion('telugu-patrikalu')",a);
let telugu=harness(a.location.href);run('restoreView()',telugu);
assert.equal(telugu.state.region,'telugu-patrikalu','F5 lost Telugu paper reader');
run("setRegion('english-magazines')",a);
a.state.publicationTopic='Health & Wellbeing';run('saveView(true)',a);
assert.equal(a.location.searchParams.get('pubtopic'),'Health & Wellbeing');
let mag=harness(a.location.href);run('restoreView()',mag);
assert.equal(mag.state.region,'english-magazines','F5 lost English magazine reader');
assert.equal(mag.state.publicationTopic,'Health & Wellbeing','F5 lost lifestyle category');
assert(html.includes('https://www.eenadu.net/'),'Direct Eenadu homepage link missing');
assert(html.includes('https://www.indiatoday.in/'),'Direct India Today homepage link missing');
assert(html.includes('<nav id="publisherCards" class="publisher-cards"'),'Compact publisher name tabs must be direct link navigation');
assert(html.includes('link.textContent=name;'),'Publisher chips should display just the publication name');
assert(html.includes('.publisher-cards{display:flex!important;flex-wrap:wrap!important'),
       'Publisher tabs must wrap without requiring horizontal scrolling');
assert(!html.includes('class="publisher-rights"'),'Unnecessary publisher badge boxes must be removed');


assert(html.includes("'telugu-states':'AP + TG General News'"),'AP+TG should be general news rather than duplicate regional business');
const regionalBranch=html.split("else if(['telugu-states','andhra-pradesh','telangana'].includes(selectedDesk))",2)[1]?.split("else if(selectedDesk==='india-general')",1)[0];
assert(regionalBranch && regionalBranch.includes("['andhra-pradesh','telangana','hyderabad','ap-tg'].includes(area)"),
       'AP+TG must accept every captured regional headline without limiting news desks');
assert(!regionalBranch.includes('item.desk') && !regionalBranch.includes('item.sector'),
       'AP/TG general news must not exclude property, business, health, sports or crime');
assert(html.includes("if(!isListedCompanyStory(item))return false"),
       'Telugu Companies must still show corporate-only headlines');
assert(html.includes('id="regionalGeneralBar"'),'Missing English/Telugu live regional updates');
assert(html.includes('id="regionalCountAP"')&&html.includes('id="regionalCountTG"'),
       'AP/TG region counts must be separately displayed');
assert(html.includes('data-regional-state="andhra-pradesh"')&&html.includes('data-regional-state="telangana"'),
       'AP/TG state-specific buttons are required');
assert(html.includes('region-label${regionBadgeClass}'),'Every regional headline should visibly identify the state');
assert(html.includes('region-label.regional-ap')&&html.includes('region-label.regional-tg'),
       'Distinct state badges must be styled');
assert(html.includes('https://www.andhrajyothy.com/andhra-pradesh')&&html.includes('https://www.andhrajyothy.com/telangana'),
       'Direct Andhra Jyothy state section links missing');
assert(html.includes('https://www.sakshi.com/andhra-pradesh')&&html.includes('https://www.sakshi.com/telangana'),
       'Direct Sakshi state section links missing');
assert(html.includes('RSS పునఃప్రచురణ లేదు'),'Publisher RSS must not be presented as syndicated');

assert(html.includes('class="moneycontrol-direct"'),'Missing direct original Moneycontrol News link');
assert(html.includes("state.region!=='telugu-states'"),'Only show AP+TG regional news filter in that desk');
assert(html.includes('id="pfSourceDiscovery"')&&html.includes('id="regionBusinessDiscovery"'),
       'Dedicated PF and regional business original-source directories are missing');
assert(html.includes('reader_finance:Boolean(data.reader_finance)'),
       'Permitted Telugu source links should flow into reader finance without duplicate URLs');
assert(html.includes('regional_business:Boolean(data.regional_business)'),
       'Telugu business links must be shared with regional business view');
assert(html.includes("item.desk==='personal-finance'"),
       'Standalone PF sources must render in the PF view');
assert(html.includes("item.desk==='regional-business'"),
       'Standalone AP/TG company sources must render in Telugu Companies');
assert(html.includes('amfiindia.com/rss-feeds')&&html.includes('rbi.org.in/Scripts/rss.aspx'),
       'Official first-party mutual fund and bank RSS directories must be reachable');
assert(html.includes('after:2026-11-13'),
       'PF and regional original-source searches should support the 14-Nov-2026 backfill');
assert(html.includes('id="xWatchPanel"'),'X Business Watch panel missing');
assert(html.includes('https://platform.twitter.com/widgets.js'),'Official X embed loader missing');
assert(html.includes('InvTGOfficial')&&html.includes('THubHyd')&&html.includes('AP_EDB'),'Regional source profiles missing');
e.state.origin='exchange';run('saveView(true)',e);
assert.equal(e.location.searchParams.get('origin'),'exchange','Official source filter not in URL');
const sourceReload=harness(e.location.href);run('restoreView()',sourceReload);
assert.equal(sourceReload.state.origin,'exchange','F5 lost official source filter');
e.location=new URL('https://gmreddy0809-cloud.github.io/MyBusinessNews/?sector=Aviation%20%26%20Airports&q=IndiGo&hours=24#hyderabad');
run('restoreView()',e);
assert.equal(e.state.sector,'Aviation & Airports');
assert.equal(e.state.search,'IndiGo');
assert.equal(e.state.hours,'24');
assert.equal(e.state.region,'hyderabad');
console.log('PASS: compact AP/TG/PF nav wraps without sideways scrolling; More menu works; all deep-link F5 tests pass');
