(function(){
  'use strict';
  let data={records:[]};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const select=(g,teacher='all')=>data.records.filter(r=>r.course_ids.includes(g.id)&&(teacher==='all'||!r.teacher_names.length||r.teacher_names.includes(teacher)));
  const issueText=v=>typeof v==='string'?v:v.description||v.issue||v.note||v.reason||v.type||'';
  function syllabi(g,teacher){const rs=select(g,teacher);if(!rs.length)return '';
    let out='<section class="detail-resource handbook-info"><h3>手册中的课程设计</h3><p class="meta">手册保留版本、教师和页码；当前教学班的内容与考核以本班大纲为准。</p>';
    for(const r of rs){out+='<details class="handbook-entry"><summary>'+esc(r.title)+' · '+esc(r.teacher_names.join('、')||'项目通用说明')+' · '+esc(r.version)+'</summary><p>'+esc(r.summary)+'</p>';
      if(r.historical_credits?.length)out+='<p class="meta">手册旧课号 '+esc(r.historical_codes.join('、'))+' · 当时 '+esc(r.historical_credits.join(' / '))+' 学分 · '+esc(r.module)+'</p>';
      if(r.training&&r.training!==r.summary)out+='<p><b>训练内容：</b>'+esc(r.training)+'</p>';
      if(r.conditioning)out+='<p><b>专项体能：</b>'+esc(r.conditioning)+'</p>';
      if(r.assessment)out+='<p><b>手册所列考核：</b>'+esc(r.assessment)+'</p>';
      if(r.test_items?.length)out+='<p><b>明确测试项目：</b>'+r.test_items.map(issueText).map(esc).join('；')+'</p>';
      if(r.readings?.length)out+='<p><b>教学涉及的阅读文本：</b>'+r.readings.map(esc).join('、')+'<span class="meta">（课程提及文本，不一概视为必读书目）</span></p>';
      const issues=(r.issues||[]).map(issueText).filter(Boolean);if(issues.length)out+='<p class="meta">原资料校核：'+issues.map(esc).join('；')+'</p>';
      out+='<p class="meta">'+esc(r.note)+'</p><p class="source-label">来源：'+esc(r.source_label)+'</p></details>';
    }
    if(rs.some(r=>r.kind==='pe'))out+='<div class="handbook-evaluation"><p><b>体育课评价构成（2024手册）：</b>'+esc(data.pe_evaluation.assessment)+'</p><p class="meta">'+esc(data.pe_evaluation.note)+'</p><p class="source-label">来源：'+esc(data.pe_evaluation.source_label)+'</p></div>';
    return out+'</section>';
  }
  function materials(g,teacher){const rs=select(g,teacher);return rs.map(r=>'<section class="detail-resource"><h3>'+esc(r.title)+' · '+esc(r.teacher_names.join('、')||'项目说明')+'</h3><p>'+esc(r.version)+' · PDF第'+r.pages.map(esc).join('、')+'页</p><a href="'+esc(r.url)+'" target="_blank" rel="noopener noreferrer">打开手册对应页 ↗</a><p class="source-label">来源：'+esc(r.source_label)+'</p></section>').join('')}
  function summary(g,teacher){const rs=select(g,teacher);if(!rs.length)return '';return '<details class="detail-resource"><summary>手册课程设计参考 · '+rs.length+'份</summary><p class="meta">以下是手册课程设计，不是修读者对当前教学班的评价。</p>'+rs.map(r=>'<p><b>'+esc(r.teacher_names.join('、')||r.title)+' · '+esc(r.version)+'</b><br>'+esc(r.summary)+'</p><p class="source-label">来源：'+esc(r.source_label)+'</p>').join('')+'<p class="meta">考核、阅读文本和训练内容详见“课程大纲”；原件在“课程资料”。</p></details>'}
  window.HandbookInfo={async init(){try{const r=await fetch('data/handbooks.json');if(r.ok)data=await r.json()}catch{}},syllabi,materials,summary,teachers:g=>[...new Set(select(g).flatMap(r=>r.teacher_names))]};
})();
