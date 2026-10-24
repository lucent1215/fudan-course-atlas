'use strict';
/* Source URLs stay in the private research log. Only course materials link out. */
window.ReviewSupplement=(()=>{
 let data={records:[],materials:[],historical_syllabi:[]};
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function select(course,teacher='all'){
  const rank=r=>/旁证|相近|非本班|教师风格|项目体验|整体选课/.test(r.scope_label||'')?0:1;
  const year=r=>Math.max(0,...((r.term||r.source_label||'').match(/20\d{2}/g)||[]).map(Number));
  return data.records.filter(r=>r.course_ids.includes(course.id)&&(teacher==='all'||!r.teacher||r.teacher===teacher||(r.teacher_names||[]).includes(teacher))).sort((a,b)=>rank(b)-rank(a)||year(b)-year(a));
 }
 function label(r){return [r.teacher||'教师未注明',r.term||'修读学期未注明',r.scope_label].filter(Boolean).join(' · ')}
 function comments(course,teacher){const rows=select(course,teacher);if(!rows.length)return '';
  return `<section class="detail-resource supplement"><h3>补充课评与公开体验</h3><p class="meta">学生亲历、教师统计、媒体采访分别标注。历史班级数据按原学期保留。</p>${rows.map(r=>`<article class="evidence" data-supplement="${esc(r.id)}"><h4>${esc(label(r))}</h4><p>${esc(r.summary)}</p>${[['workload','投入与作业'],['assessment','考核'],['grading','给分经历']].filter(([k])=>r[k]).map(([k,t])=>`<p><b>${t}：</b>${esc(r[k])}</p>`).join('')}${r.numbers?.length?`<p><b>具体数据：</b>${r.numbers.map(esc).join('；')}</p>`:''}${r.mapping_note?`<p class="meta">归属：${esc(r.mapping_note)}</p>`:''}<p class="citation">来源：${esc(r.source_label)} · ${esc(r.source_type)}</p></article>`).join('')}</section>`;
 }
 function summary(course,teacher){const rows=select(course,teacher).filter(r=>r.judgment);if(!rows.length)return '';
  return `<section class="detail-note supplement"><h3>本轮补充判断</h3>${rows.map(r=>`<div class="evidence"><h4>${esc(label(r))}</h4><p class="verdict">${esc(r.judgment)}</p><p class="citation">依据：${esc(r.source_label)} · ${esc(r.source_type)}</p></div>`).join('')}</section>`;
 }
 function materials(course,teacher){const rows=data.materials.filter(r=>r.course_ids.includes(course.id)&&(teacher==='all'||!r.teacher||r.teacher===teacher));return rows.map(r=>`<section class="detail-resource"><h3>${esc(r.title)}</h3><p>${esc(r.summary)}</p><p class="meta">${esc(r.term)} · ${esc(r.teacher||'教师未注明')} · ${esc(r.note)}</p><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">打开课程资料 ↗</a><p class="citation">来源：${esc(r.source_label)}</p></section>`).join('')}
 function syllabi(course){const r=(data.historical_syllabi||[]).find(r=>r.course_ids.includes(course.id));return `<div class="notice"><strong>历史课程参考 · 本期教学班未确认</strong><p>本课已列入2026公共培养方案课程池。以下是教务处公开通识课程手册中的介绍，未确认与当前学期要求相同。</p></div>${r?`<section class="detail-note"><h3>${esc(course.name)} · ${esc(r.teacher)}</h3><p>${esc(r.summary)}</p><div class="field"><b>手册所列考核</b><p>${esc(r.assessment)}</p></div><p class="citation">来源：${esc(r.source_label)}</p><p class="meta">完整官方手册可在“课程资料”中离线打开。</p></section>`:''}`}
 return {async init(){const r=await fetch('data/review-supplement.json');if(!r.ok)throw Error('补充课评未载入');data=await r.json()},select,comments,summary,materials,syllabi,teachers:course=>[...new Set(select(course).flatMap(r=>r.teacher_names?.length?r.teacher_names:r.teacher?[r.teacher]:[]))]};
})();
