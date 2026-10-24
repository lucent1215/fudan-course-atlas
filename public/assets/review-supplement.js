'use strict';
/* Canonical public source links and brief excerpts accompany course reviews. */
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
  const cards=rows.map(r=>`<article class="evidence" data-supplement="${esc(r.id)}"><div class="review-source-type">${esc(r.source_type)}</div><h4>${esc(label(r))}</h4><p>${esc(r.summary)}</p>${[['workload','投入与作业'],['assessment','考核'],['grading','给分经历']].filter(([k])=>r[k]).map(([k,t])=>`<p><b>${t}：</b>${esc(r[k])}</p>`).join('')}${r.numbers?.length?`<p><b>具体数据：</b>${r.numbers.map(esc).join('；')}</p>`:''}${r.short_excerpt?`<blockquote class="review-excerpt">${esc(r.short_excerpt)}<small>原回答短摘</small></blockquote>`:''}${r.source_excerpts?.length?`<details class="review-original"><summary>查看对应树洞原评节选</summary>${r.source_excerpts.map(x=>`<blockquote class="review-excerpt"><b>${esc(x.label)}</b><p>${esc(x.text)}</p></blockquote>`).join('')}</details>`:''}${r.mapping_note?`<p class="meta">归属：${esc(r.mapping_note)}</p>`:''}<p class="citation">来源：${esc(r.source_label)} · 引用编号 ${esc(r.source_id||r.id)}${r.source_url?` · <a data-review-source="public" href="${esc(r.source_url)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>`:''}</p></article>`);
  return `<section class="detail-resource supplement"><h3>课程体验与原帖节选</h3><p class="meta">公开课评、树洞经历与助教说明合并查阅，各自保留来源。跨平台转载和同一作者的多课回顾不算多个独立样本；原文可能需要登录。</p>${cards.join('')}</section>`;
 }
 function summary(course,teacher){const rows=select(course,teacher).filter(r=>r.judgment);if(!rows.length)return '';
  return `<section class="detail-note supplement"><h3>本轮补充判断</h3>${rows.map(r=>`<div class="evidence"><h4>${esc(label(r))}</h4><p class="verdict">${esc(r.judgment)}</p><p class="citation">依据：${esc(r.source_label)} · ${esc(r.source_type)}</p></div>`).join('')}</section>`;
 }
 function materials(course,teacher){const rows=data.materials.filter(r=>r.course_ids.includes(course.id)&&(teacher==='all'||!r.teacher||r.teacher===teacher));return rows.map(r=>`<section class="detail-resource"><h3>${esc(r.title)}</h3><p>${esc(r.summary)}</p><p class="meta">${esc(r.term)} · ${esc(r.teacher||'教师未注明')} · ${esc(r.note)}</p><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">打开课程资料 ↗</a><p class="citation">来源：${esc(r.source_label)}</p></section>`).join('')}
 function syllabi(course){const r=(data.historical_syllabi||[]).find(r=>r.course_ids.includes(course.id));return `<div class="notice"><strong>历史课程参考 · 本期教学班未确认</strong><p>本课已列入2026公共培养方案课程池。以下是教务处公开通识课程手册中的介绍，未确认与当前学期要求相同。</p></div>${r?`<section class="detail-note"><h3>${esc(course.name)} · ${esc(r.teacher)}</h3><p>${esc(r.summary)}</p><div class="field"><b>手册所列考核</b><p>${esc(r.assessment)}</p></div><p class="citation">来源：${esc(r.source_label)}</p><p class="meta">完整官方手册可在“课程资料”中离线打开。</p></section>`:''}`}
 return {async init(){const r=await fetch('data/review-supplement.json');if(!r.ok)throw Error('补充课评未载入');data=await r.json()},select,comments,summary,materials,syllabi,teachers:course=>[...new Set(select(course).flatMap(r=>r.teacher_names?.length?r.teacher_names:r.teacher?[r.teacher]:[]))]};
})();
