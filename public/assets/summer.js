(function(){
  'use strict';let rows=new Map();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function render(g,teacher='all'){
    const row=rows.get(g.id);if(!row)return '';
    const offers=row.offerings.filter(o=>teacher==='all'||o.teachers.includes(teacher));if(!offers.length)return '';
    const rec=row.recognition;
    let out='<section class="detail-note summer-info"><h3>2026暑期 · 认定与安排</h3>';
    if(rec?.kind==='core')out+='<p><b>通识核心认定：</b>'+esc(rec.recognition)+'。</p>';
    if(rec?.kind==='english_2023_and_before')out+='<p><b>英语认定仅适用于2023级及以前：</b>'+esc(rec.recognition)+'，只能认定一项。2024级及以后不据此自动计作进阶或高阶英语。</p>';
    if(g.is_pe)out+='<p><b>暑期体育为通识选修或任意选修，不能替代春秋学期GEPE体育必修学分。</b></p>';
    out+='<p>本次教学活动安排在7月5日起至8月1日左右，密集授课；成绩和PNP选择原则与春秋课程一致。选课结束后无试听，通知只受理附医院诊断证明的伤病退课。</p>';
    out+=offers.map(o=>'<div class="summer-offer"><b>'+esc(o.code)+' · '+esc(o.teachers.join('、'))+'</b><p class="meta">'+esc(o.source_status)+(o.pdf_pages?.length?' · 课程表PDF第'+o.pdf_pages.join('、')+'页':'')+'</p>'+(o.cancelled?'<p class="course-cancelled">停开：'+esc(o.remark)+'</p>':'')+(o.assessment_deadline?'<p>通知所列考核时间：'+esc(o.assessment_deadline)+'</p>':'')+'</div>').join('');
    out+='<p class="citation">来源：教务处2026-06-16暑期教学活动通知、课程表与英文课程认定附件；2026-10-26读取的教务班次。上述选课时间为2026暑期历史安排。</p></section>';
    return out;
  }
  window.SummerInfo={async init(){const r=await fetch('data/summer.json');if(!r.ok)throw Error('暑期课程资料未载入');rows=new Map((await r.json()).records.map(x=>[x.id,x]))},render};
})();
