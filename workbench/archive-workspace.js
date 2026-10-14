function arrowIcon(direction){return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+(direction==='next'?'M9 5l7 7-7 7':'M15 5l-7 7 7 7')+'"/></svg>';}
let readyPlayback;const playbackReady=new Promise(resolve=>{readyPlayback=resolve;});
async function removalState(){const r=await fetch('/api/atom-removals');if(!r.ok)throw Error('删除状态读取失败');return new Set((await r.json()).deleted);}
(async()=>{const id=document.body.dataset.atomId;const host=document.querySelector('.sidecard');if(!host)return;const b=document.createElement('button');b.className='btn block';b.textContent='删除原子页';host.append(b);const msg=document.createElement('p');msg.setAttribute('role','status');host.append(msg);const gone=await removalState();function paint(){const deleted=gone.has(id);b.textContent=deleted?'恢复原子页':'删除原子页';document.body.classList.toggle('atom-deleted',deleted);if(deleted)msg.textContent='已删除：本原子及各课程出现位置已从浏览与检索中移除。可在这里恢复。';}paint();b.onclick=async()=>{const deleted=gone.has(id);if(!deleted&&!confirm('删除这个原子页及它在各课件中的出现位置？已有课件历史保留，删除后可恢复。'))return;b.disabled=true;try{const r=await fetch('/api/atoms/'+encodeURIComponent(id)+'/removal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:deleted?'restore':'delete'})});if(!r.ok)throw Error('操作失败，请重试');location.reload();}catch(e){msg.textContent=e.message;b.disabled=false;}};})();
'use strict';
(async function () {
  const button = document.getElementById('archive-add');
  const feedback = document.getElementById('archive-feedback');
  const atomId = document.body.dataset.atomId;
  if (!button || !atomId) return;
  try {
    const response = await fetch('/api/atoms/' + encodeURIComponent(atomId));
    if (!response.ok) throw Error('备课关联暂不可用，请刷新重试。');
    const data = await response.json();
    const preferred = new URLSearchParams(location.search).get('slide') || data.structured_archive?.rep;
    const page = data.pages.find(p => p.legacy_ids?.includes(preferred)) || data.pages[0];
    if (!page) throw Error('此档案尚未关联课程页面，暂不能加入备课。');
    const tabs=document.querySelector('.tabs');
    const imageTab=tabs.querySelector('button');
    const htmlTab=document.createElement('button');htmlTab.className='tab';htmlTab.textContent='HTML';
    const full=document.createElement('button');full.className='tab';full.textContent='全屏';
    tabs.append(htmlTab,full);
    const host=document.querySelector('.current-slide');
    const imagePane=host.querySelector('.slidebox');
    const frame=document.createElement('iframe');frame.className='html-slide';frame.title='HTML 幻灯片草稿';frame.hidden=true;frame.setAttribute('sandbox','');host.append(frame);
    let conversion;
    try { const response=await fetch('../data/html-conversions.json'); if(response.ok){const manifest=await response.json();conversion=manifest.records[atomId]||manifest.records[page.page_id];} } catch(error) { console.warn('HTML 转换记录暂不可用'); }
    const htmlURL=conversion?.url || (page.html?.status==='local_exists'?page.html.url:null);
    htmlTab.disabled=!htmlURL;
    htmlTab.title=htmlTab.disabled?'这页还没有 HTML 转换记录':'查看 HTML 草稿 · 尚待原图对照验收';
    function switchMode(html){imagePane.hidden=html;frame.hidden=!html;imageTab.classList.toggle('on',!html);htmlTab.classList.toggle('on',html);if(html&&!frame.src)frame.src=htmlURL;}
    imageTab.onclick=()=>switchMode(false);htmlTab.onclick=()=>switchMode(true);
    function exitPresentation(){host.classList.remove('presentation');full.textContent='全屏';document.body.classList.remove('presenting');if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});if(window.presentationTarget&&window.presentationTarget!==location.pathname.split('/').pop()+location.search){const target=window.presentationTarget;window.presentationTarget=null;location.href=target;}}
    const exit=document.createElement('button');exit.className='presentation-exit';exit.textContent='退出全屏';exit.onclick=exitPresentation;host.append(exit);
    const showPages=document.createElement('button');showPages.className='presentation-pages-button';showPages.innerHTML='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="3" width="6" height="6" rx="1"/><rect x="3" y="15" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/></svg>';showPages.setAttribute('aria-label','页面列表');showPages.title='页面列表';showPages.setAttribute('aria-expanded','false');host.append(showPages);readyPlayback();
    showPages.onclick=()=>{const open=host.classList.toggle('show-pages');showPages.setAttribute('aria-expanded',String(open));if(open){const drawer=host.querySelector('.presentation-drawer');const active=drawer?.querySelector('.current');if(active)drawer.scrollTop=active.offsetTop-drawer.clientHeight/2+active.clientHeight/2;}};
    full.onclick=()=>{if(host.classList.contains('presentation')){exitPresentation();return;}host.classList.add('presentation');document.body.classList.add('presenting');full.textContent='退出全屏';host.querySelectorAll('.presentation-dock .slide-arrows a').forEach((a,i)=>{a.setAttribute('aria-label',i?'下一页':'上一页');a.innerHTML=arrowIcon(i?'next':'prev');});if(host.requestFullscreen){host.requestFullscreen().catch(()=>{feedback.textContent='浏览器未允许系统全屏，当前使用窗口内播放。';});}};
    document.addEventListener('keydown',event=>{if(event.key==='Escape')exitPresentation();});
    document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement)exitPresentation();});

    let selected;
    try { selected = new Set(JSON.parse(sessionStorage.getItem('slide-assembly-draft') || '[]')); }
    catch { selected = new Set(); }
    const target = sessionStorage.getItem('slide-assembly-target');
    if (target && target !== 'new') document.getElementById('archive-assembly').href = '../assembly.html?id=' + encodeURIComponent(target);
    function paint() {
      button.textContent = selected.has(page.page_id) ? '移出备课' : '＋ 加入备课';
      button.setAttribute('aria-pressed', String(selected.has(page.page_id)));
    }
    button.disabled = false;
    paint();
    button.onclick = () => {
      if (selected.has(page.page_id)) selected.delete(page.page_id);
      else selected.add(page.page_id);
      sessionStorage.setItem('slide-assembly-draft', JSON.stringify([...selected]));
      paint();
      feedback.textContent = selected.has(page.page_id) ? '已加入备课，可在“我的课件”组装；再次点击可移出。' : '已移出备课。';
    };
    const notes = document.createElement('section');
    notes.id = 'reader-notes';
    notes.className = 'phase';
    document.querySelector('article .main').append(notes);
    const script = document.createElement('script');
    script.src = '../notes-ui.js';
    script.onload = () => {
      const form = document.getElementById('note-form');
      const labels = {kind:'记录类型',course_title:'课程名称',session_title:'课次 / 日期',source_reference:'材料出处',timecode:'时间位置'};
      for (const [name, title] of Object.entries(labels)) {
        const input = form.elements.namedItem(name);
        const label = document.createElement('label');
        const caption = document.createElement('span');
        caption.textContent = title;
        input.before(label); label.append(caption, input);
      }
      const text = form.elements.namedItem('text');
      text.id = 'archive-note-text';
      const textLabel = document.createElement('label');
      textLabel.htmlFor = text.id; textLabel.textContent = '解读内容';
      text.before(textLabel);
      form.elements.namedItem('timecode').placeholder = '例如 12:30';
      showNotes(page.page_id);
    };
    script.onerror = () => { notes.textContent = '解读暂不可用，请刷新重试。'; };
    document.body.append(script);
  } catch (error) {
    button.textContent = '暂不能加入备课';
    feedback.textContent = error.message;
  }
})();

(async function deckContext() {
  try {
    const response = await fetch('deck-context.json');
    if (!response.ok) throw Error('课件顺序暂不可用');
    const removed=await removalState();
    const rows = (await response.json()).filter(r=>!removed.has(r.atom_id));
    const titleResponse=await fetch('../title-governance/knowledge-title-overlay.json');
    const titles=titleResponse.ok?(await titleResponse.json()).titles||{}:{};
    for(const row of rows){const t=titles[row.atom_id];if(t?.knowledge_title){row.original_title=row.title;row.title=t.knowledge_title;row.title_candidate=t.human_review!=='confirmed';}}
    document.querySelectorAll(".reccard,.relcard").forEach(a=>{const id=a.getAttribute("href").split(".")[0];if(removed.has(id))a.remove();});
    const atom = document.body.dataset.atomId;
    const requested = new URLSearchParams(location.search).get('slide');
    const sourceIdentity=document.querySelector('[data-source-representative]');
    const rep = sourceIdentity?.dataset.sourceRepresentative || document.querySelector('#hero-img').dataset.hd.split('/').pop().replace(/\.jpg$/, '');
    const current = rows.find(r => r.id === (requested || rep) && r.atom_id === atom);
    if (!current) return;
    const siblings = rows.filter(r => r.deck === current.deck).sort((a,b)=>a.page-b.page);
    const index = siblings.findIndex(r=>r.id===current.id);
    const href = row => row.atom_id + '.html?slide=' + encodeURIComponent(row.id);
    const hero = document.querySelector('#hero-img');
    if(requested) hero.src = '/uploads/slides-hd/' + current.id + '.jpg';
    hero.dataset.hd = hero.src;
    hero.alt = current.title;
    document.querySelector('.stagetools > div:last-child').textContent = current.id + ' · ' + current.deck_name;
    document.querySelector('.pagenav .mid').textContent = current.deck_name + ' · 第 ' + current.page + ' 页';
    const strip=document.getElementById('deck-filmstrip');strip.replaceChildren();
    const heading=document.createElement('h2');const topicLink=document.createElement('a');topicLink.textContent=current.deck_name+' ↗';topicLink.href='index.html?topic='+encodeURIComponent(current.deck);topicLink.title='查看这个主题的全部活页';heading.append(topicLink);strip.append(heading);
    const list=document.createElement('div');list.className='filmstrip-pages';strip.append(list);
    for(const row of siblings){
      const a=document.createElement('a');a.href=href(row);
      const active=row.id===current.id;
      if(active){a.className='current';a.setAttribute('aria-current','page');}
      const img=document.createElement('img');img.src='../assets/legacy-thumbs/'+row.id+'.jpg';img.decoding='async';img.alt=row.title;img.loading='lazy';
      const label=document.createElement('span');label.textContent='第 '+row.page+' 页'+(active?' · 当前页':'');
      a.title=row.title+(row.title_candidate?' · 标题待确认':'');a.append(img,label);list.append(a);
    }
    requestAnimationFrame(()=>{const active=list.querySelector('.current');if(active&&innerWidth>700)list.scrollTop=active.offsetTop-list.offsetTop-list.clientHeight/2+active.clientHeight/2;});
    const host=document.querySelector('.current-slide');
    const drawer=document.createElement('nav');drawer.className='presentation-drawer';drawer.setAttribute('aria-label','全屏页面列表');host.append(drawer);
    let playing=index;
    const badge=document.createElement('span');badge.className='presentation-position';host.append(badge);
    function updatePlaying(next){
      playing=next;const row=siblings[playing];hero.src='/uploads/slides-hd/'+row.id+'.jpg';hero.dataset.hd=hero.src;hero.alt=row.title;
      const frame=host.querySelector('.html-slide');if(frame)frame.hidden=true;host.querySelector('.slidebox').hidden=false;
      window.presentationTarget=href(row);badge.textContent=(playing+1)+' / '+siblings.length;
      const progress=host.querySelector('.presentation-progress');if(progress)progress.style.setProperty('--progress',((playing+1)/siblings.length*100)+'%');
      drawer.querySelectorAll('button').forEach((b,i)=>{b.classList.toggle('current',i===playing);b.setAttribute('aria-current',i===playing?'page':'false');});
      const arrows=host.querySelectorAll('.presentation-dock .slide-arrows a');if(arrows.length){arrows[0].innerHTML=arrowIcon('prev');arrows[1].innerHTML=arrowIcon('next');arrows[0].setAttribute('aria-disabled',String(playing===0));arrows[1].setAttribute('aria-disabled',String(playing===siblings.length-1));}
    }
    siblings.forEach((row,i)=>{const b=document.createElement('button');const img=document.createElement('img');img.src='../assets/legacy-thumbs/'+row.id+'.jpg';img.decoding='async';img.alt=row.title;img.loading='lazy';const label=document.createElement('span');label.textContent='第 '+row.page+' 页';b.append(img,label);b.onclick=()=>updatePlaying(i);drawer.append(b);});
    document.addEventListener('keydown',event=>{if(!host.classList.contains('presentation')||['INPUT','TEXTAREA'].includes(event.target.tagName))return;if(event.key==='ArrowLeft'&&playing>0){event.preventDefault();updatePlaying(playing-1);}if(event.key==='ArrowRight'&&playing<siblings.length-1){event.preventDefault();updatePlaying(playing+1);}});
    const nav=document.querySelectorAll('.pagenav > a');
    const controls=document.createElement('div');controls.className='slide-navigation';document.querySelector('.current-slide').append(controls);
    const modes=document.querySelector('.tabs');controls.prepend(modes);
    const arrows=document.createElement('div');arrows.className='slide-arrows';controls.append(arrows);
    for(const link of nav)arrows.append(link);
    const pageInfo=document.querySelector('.page-status');if(pageInfo)arrows.append(pageInfo);
    nav.forEach((link,i)=>link.addEventListener('click',event=>{if(!host.classList.contains('presentation'))return;event.preventDefault();const next=playing+(i===0?-1:1);if(next>=0&&next<siblings.length)updatePlaying(next);}));
    badge.textContent=(index+1)+' / '+siblings.length;
    const dock=document.createElement('div');dock.className='presentation-dock';host.append(dock);
    await playbackReady;
    const listButton=host.querySelector('.presentation-pages-button');const exitButton=host.querySelector('.presentation-exit');
    exitButton.textContent='↩';exitButton.setAttribute('aria-label','退出全屏');exitButton.title='退出全屏';
    dock.append(listButton,arrows,badge);
    const progress=document.createElement('span');progress.className='presentation-progress';progress.style.setProperty('--progress',((index+1)/siblings.length*100)+'%');dock.append(progress,exitButton);
    host.querySelector('.slide-navigation').append(arrows.cloneNode(true));
    // Keep normal navigation in place; the dock owns the live playback controls.
    const normalArrows=host.querySelector('.slide-navigation .slide-arrows');normalArrows.querySelectorAll('.page-status').forEach(n=>n.remove());
    const dockInfo=arrows.querySelector('.page-status');if(dockInfo)host.querySelector('.slide-navigation').append(dockInfo);
drawer.querySelectorAll('button')[index]?.classList.add('current');
    document.querySelector('.stagetools').hidden=true;
    const preview=document.querySelector('.current-slide .slidebox');
    function alignFilmstrip(){if(innerWidth<=700){strip.style.height='';return;}const visible=preview.hidden?document.querySelector('.current-slide .html-slide'):preview;const height=visible?.getBoundingClientRect().height;if(height>0)strip.style.height=height+'px';}
    const railObserver=new ResizeObserver(alignFilmstrip);railObserver.observe(preview);const htmlPreview=document.querySelector('.current-slide .html-slide');if(htmlPreview)railObserver.observe(htmlPreview);alignFilmstrip();
    document.querySelector('.pagenav').hidden=true;
    for(const [link,row,label] of [[nav[0],siblings[index-1],'上一页'],[nav[1],siblings[index+1],'下一页']]){if(!link)continue;if(row){link.href=href(row);link.classList.remove('disabled');link.textContent=label+' '+row.page;}else{link.removeAttribute('href');link.classList.add('disabled');link.textContent=label==='上一页'?'课件开头':'课件末尾';}}
    document.querySelectorAll('.relgrid a').forEach(a=>{const parts=a.querySelector('.rd')?.textContent.split(' · p');if(!parts)return;const row=rows.find(r=>r.deck===parts[0]&&String(r.page)===parts[1]);if(row)a.href=href(row);});
  } catch(error) {document.getElementById('deck-filmstrip').textContent='课件缩略图暂不可用，请刷新重试。';}
})();
(async function unifiedKnowledgeTitles(){try{const r=await fetch("../title-governance/knowledge-title-overlay.json");if(!r.ok)return;const d=await r.json();const t=d.titles?.[document.body.dataset.atomId];if(!t?.knowledge_title)return;document.querySelector(".hero h1").textContent=t.knowledge_title;document.title=t.knowledge_title+" · 活页 LivePage";let badge=document.querySelector(".knowledge-title-label");if(!badge){badge=document.createElement("small");badge.className="knowledge-title-label";document.querySelector(".hero h1").after(badge)}badge.textContent=t.source==="image_checked_by_codex"?"知识标题候选 · 待确认":"知识标题 · AI 待确认";}catch{}})();

if(document.body.dataset.atomId==="atom-0410"){const notice=document.createElement("p");notice.className="annotation-warning";notice.textContent="原图已从 Keynote 恢复；旧 AI 白纸解读与原图不符，暂不采用，待重新标注。";document.querySelector(".hero").append(notice);}
