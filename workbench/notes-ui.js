'use strict';
let notePage=null, noteTicket=0;
const noteLabels={explanation:'页面解读',teaching_note:'讲课记录',example:'案例',question:'课堂问答',source_correction:'原文校正建议'};
const notesSection=document.createElement('section');
notesSection.innerHTML='<h3>解读与讲课记录</h3><div id="note-list"></div><h4>补充解读</h4><form id="note-form"><textarea name="text" aria-label="解读内容" placeholder="这页想表达什么？上课时怎么讲？" required maxlength="20000" rows="4"></textarea><fieldset class="note-context"><legend>记录类型与出处（可选）</legend><select name="kind" aria-label="记录类型"><option value="explanation">页面解读</option><option value="teaching_note">讲课记录</option><option value="example">案例</option><option value="question">课堂问答</option><option value="source_correction">原文校正建议</option></select><input name="course_title" aria-label="课程名称" placeholder="课程名称"><input name="session_title" aria-label="课次" placeholder="课次 / 日期"><input name="source_reference" aria-label="材料出处" placeholder="录音、文稿或资料出处"><input name="timecode" aria-label="时间位置" placeholder="录音时间位置，例如 12:30"></fieldset><button type="submit">保存解读</button><p role="status" id="note-feedback"></p></form>';
document.getElementById('reader-notes').append(notesSection);
function rememberNoteDraft(){if(notePage)sessionStorage.setItem('note-draft:'+notePage,JSON.stringify(Object.fromEntries(new FormData(document.getElementById('note-form')))));}
document.getElementById('note-form').oninput=rememberNoteDraft;
document.getElementById('note-form').onchange=rememberNoteDraft;
const identityLine=document.createElement('p');identityLine.className='muted';notesSection.prepend(identityLine);
async function showNotes(id){
 notePage=id;const ticket=++noteTicket;document.getElementById('note-form').reset();document.getElementById('note-feedback').textContent='';
 try{const draft=JSON.parse(sessionStorage.getItem('note-draft:'+id)||'{}');for(const [key,value] of Object.entries(draft)){const input=document.getElementById('note-form').elements.namedItem(key);if(input&&typeof value==='string')input.value=value;}}catch{}
 identityLine.textContent='';
 fetch('/api/library/page/'+encodeURIComponent(id)+'/identity').then(r=>r.ok?r.json():null).then(data=>{if(data&&ticket===noteTicket)identityLine.textContent='原子页身份：'+(String(data.atom.identity_status||'').startsWith('provisional')?'暂定，跨课件关联待核验':data.atom.atom_id+' · '+data.occurrences.length+' 处使用')+'。解读保留本页出处；讲课记录另外保留课程和课次。';}).catch(()=>{});
 await refreshNotes(id,ticket);
}
async function refreshNotes(id,ticket){
 const list=document.getElementById('note-list');list.textContent='正在读取…';
 try{const r=await fetch('/api/library/page/'+encodeURIComponent(id)+'/notes');if(!r.ok)throw Error('解读记录暂不可用');const data=await r.json();if(ticket!==noteTicket)return;list.replaceChildren();
 const notes=data.notes||[];if(!notes.length)list.textContent='还没有补充解读。每次讲课的案例、问答和讲法都可以保存在这里。';
 for(const n of notes){const box=document.createElement('article');box.className='note';const meta=document.createElement('small');meta.textContent=[noteLabels[n.kind]||n.kind,n.course_title,n.session_title,n.source_reference,n.timecode].filter(Boolean).join(' · ');const text=document.createElement('p');text.textContent=n.text;box.append(meta,text);list.append(box);}
 }catch(e){if(ticket===noteTicket)list.textContent=e.message;}
}
document.getElementById('note-form').onsubmit=async event=>{
 event.preventDefault();const form=event.currentTarget,id=notePage,ticket=noteTicket,button=form.querySelector('button');const feedback=document.getElementById('note-feedback');button.disabled=true;feedback.textContent='正在保存…';
 try{const r=await fetch('/api/library/page/'+encodeURIComponent(id)+'/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(form)))});const data=await r.json();if(!r.ok)throw Error(data.error||'保存失败');sessionStorage.removeItem('note-draft:'+id);if(ticket!==noteTicket)return;form.elements.text.value='';feedback.textContent='已保存，原有标注保留。';await refreshNotes(id,ticket);
 }catch(e){if(ticket===noteTicket)feedback.textContent=e.message;}finally{button.disabled=false;}
};
