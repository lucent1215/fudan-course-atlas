const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../public'),data=JSON.parse(fs.readFileSync(root+'/data/review-supplement.json','utf8')),cat=JSON.parse(fs.readFileSync(root+'/data/catalog.json','utf8'));
let passed=0;const ok=(v,m)=>{assert.ok(v,m);passed++};const ids=new Set(cat.scope.map(g=>g.id));
ok(new Set(data.records.map(r=>r.id)).size===data.records.length,'record IDs unique');
const serverIds=JSON.parse(fs.readFileSync(path.join(root,'../lib/course-ids.json'),'utf8'));ok(serverIds.length===ids.size&&serverIds.every(id=>ids.has(id)),'public catalog and upload API share the same course list');
for(const r of data.records){ok(r.course_ids.length>0&&r.course_ids.every(i=>ids.has(i)),'valid course mapping '+r.id);ok(r.source_label&&r.summary&&r.judgment,'provenance and synthesis '+r.id);ok(!/https?:|xsec_token|data:image|<script|@m\.fudan/.test(JSON.stringify(r)),'public records contain no source URL, raw image or login identity '+r.id)}
const box={window:{},fetch:async()=>({ok:true,json:async()=>data})};vm.runInNewContext(fs.readFileSync(root+'/assets/review-supplement.js','utf8'),box);
(async()=>{const t=box.window.ReviewSupplement;await t.init();
for(const g of cat.scope){const rows=t.select(g);ok(rows.every(r=>r.course_ids.includes(g.id)),'scoped records');for(const teacher of t.teachers(g)){const filtered=t.select(g,teacher);ok(filtered.every(r=>!r.teacher||r.teacher===teacher||(r.teacher_names||[]).includes(teacher)),'parallel teachers separated')}
ok(!/<a\b/.test(t.summary(g,'all')+t.comments(g,'all')),'no source anchors outside materials')}
const math=cat.scope.find(g=>g.id==='C0055');ok(!t.select(math).some(r=>r.course_ids.includes('U1694')),'statistics H not merged into mathematics statistics');
ok(t.select(cat.scope.find(g=>g.id==='C0039'),'吴昊').some(r=>r.id==='zhihu_wu'),'Zhihu teacher match');ok(!t.select(cat.scope.find(g=>g.id==='C0039'),'梁振国').some(r=>r.id==='zhihu_wu'),'parallel teacher exclusion');
console.log(JSON.stringify({passed,records:data.records.length,courses:data.stats.courses}));})();
