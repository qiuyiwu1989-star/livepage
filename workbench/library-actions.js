'use strict';
const selection=new Set();
try{for(const id of JSON.parse(sessionStorage.getItem('slide-assembly-draft')||'[]'))if(typeof id==='string')selection.add(id);}catch{}
const assemblyLink=document.createElement('a');const assemblyTarget=sessionStorage.getItem('slide-assembly-target');assemblyLink.href=assemblyTarget&&assemblyTarget!=='new'?'assembly.html?id='+encodeURIComponent(assemblyTarget):'assembly.html';document.querySelector('header').append(assemblyLink);
function updateSelection(){sessionStorage.setItem('slide-assembly-draft',JSON.stringify([...selection]));assemblyLink.textContent=selection.size?'去组课（'+selection.size+' 页）':'我的课件';}
updateSelection();
function addAssemblyAction(page){
 const host=document.getElementById('reader-primary');host.replaceChildren();
 const button=document.createElement('button');const next=document.createElement('a');
 next.href=assemblyLink.href;next.textContent='去组课 →';
 const feedback=document.createElement('span');feedback.className='selection-feedback';feedback.setAttribute('role','status');
 function paint(){const selected=selection.has(page.page_id);button.textContent=selected?'移出备课':'加入备课';button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));next.hidden=!selection.size;}
 button.onclick=()=>{const was=selection.has(page.page_id);if(was)selection.delete(page.page_id);else selection.add(page.page_id);updateSelection();paint();feedback.textContent=was?'已移出，可重新加入':'已加入备课 · 共 '+selection.size+' 页';};
 host.append(feedback,button,next);paint();
}
const relatedBox=document.createElement('section');relatedBox.className='reading-section';relatedBox.innerHTML='<h3>原子页的其他出现位置</h3><p>同一原子页依据原库映射；同标题候选尚未确认，不自动合并。</p><div></div>';document.getElementById('reader-notes').append(relatedBox);
let relatedTicket=0;
async function loadRelated(id){
  const ticket=++relatedTicket;
  const list=relatedBox.querySelector('div');list.textContent='正在读取…';
  try{
    const r=await fetch('/api/library/page/'+encodeURIComponent(id)+'/related');
    if(!r.ok)throw Error('关联信息暂不可用');
    const data=await r.json();if(ticket!==relatedTicket)return;
    list.replaceChildren();
    function group(label,pages){
      const heading=document.createElement('p');heading.textContent=label;list.append(heading);
      for(const p of pages){const b=document.createElement('button');b.textContent=(p.deck_title||p.deck_id)+' · 第 '+p.page_number+' 页';b.onclick=()=>detail(p.page_id);list.append(b);}
    }
    const same=data.same_atom||[],candidates=data.candidates||data.pages||[];
    if(same.length)group('同一原子页 · '+same.length+' 处',same);
    if(candidates.length)group('同标题候选 · 尚未确认',candidates);
    if(!same.length&&!candidates.length)list.textContent='暂无其他出现位置或同标题候选。';
  }catch(e){if(ticket===relatedTicket)list.textContent=e.message;}
}
const quality=document.createElement('p');document.querySelector('main > details').append(quality);
fetch('/api/library/governance').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{const c=d.counts;quality.textContent=(c.confirmed==null?'':('已接回原库 '+c.confirmed+' 个原子身份 · '+c.confirmed_occurrences+' 处记录 · '))+'待接入旧标注 '+c.missing_old_annotations+' 页 · 待登记 HTML '+c.pending_html+' 页 · 同标题待核对 '+c.candidate_groups+' 组。';}).catch(()=>{quality.textContent='处理进度暂不可用，请稍后重试。';});
