'use strict';
function bindSlideDrag(row,index){
 row.tabIndex=0;row.setAttribute('aria-label',`第 ${index+1} 页，拖动调整顺序；按住 Alt 和方向键也可排序`);
 row.querySelectorAll('img').forEach(img=>img.draggable=false);
 row.onkeydown=e=>{if(busy||!e.altKey||!['ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const to=index+(e.key==='ArrowUp'?-1:1);if(to<0||to>=entries.length)return;const [item]=entries.splice(index,1);entries.splice(to,0,item);window.prepSelected=to;changed();$('rows').children[to]?.focus();};
 row.onpointerdown=e=>{
  if(busy||e.button!==0||e.target.closest('button,input,textarea,select,a'))return;
  if(e.pointerType==='touch'&&!e.target.closest('.thumb'))return;
  const startX=e.clientX,startY=e.clientY;let ghost=null,line=null,slot=index,lastY=e.clientY,frame=0;
  row.setPointerCapture(e.pointerId);
  function locate(y){const rows=[...$('rows').children];slot=rows.findIndex(r=>y<r.getBoundingClientRect().top+r.getBoundingClientRect().height/2);if(slot<0)slot=rows.length;const target=rows[Math.min(slot,rows.length-1)].getBoundingClientRect();line.style.cssText=`position:fixed;left:${target.left}px;width:${target.width}px;top:${slot===rows.length?target.bottom+6:target.top-6}px`;}
  function scroll(){if(!ghost)return;const delta=lastY<90?-12:lastY>innerHeight-90?12:0;if(delta){const rail=row.closest('.sequence');if(rail)rail.scrollBy(0,delta);else window.scrollBy(0,delta);locate(lastY);}frame=requestAnimationFrame(scroll);}
  function move(ev){lastY=ev.clientY;if(!ghost&&Math.hypot(ev.clientX-startX,ev.clientY-startY)<6)return;
   if(!ghost){ghost=row.cloneNode(true);ghost.className='row drag-ghost';ghost.style.width=row.getBoundingClientRect().width+'px';ghost.setAttribute('aria-hidden','true');document.body.append(ghost);line=document.createElement('div');line.className='drop-line';document.body.append(line);row.classList.add('dragging');frame=requestAnimationFrame(scroll);}
   ghost.style.left=(ev.clientX-40)+'px';ghost.style.top=(ev.clientY-30)+'px';locate(ev.clientY);
  }
  function end(ev){row.removeEventListener('pointermove',move);row.removeEventListener('pointerup',end);row.removeEventListener('pointercancel',cancel);cancelAnimationFrame(frame);row.classList.remove('dragging');if(row.hasPointerCapture(e.pointerId))row.releasePointerCapture(e.pointerId);if(!ghost)return;ghost.remove();line.remove();ghost=null;const to=slot>index?slot-1:slot;if(ev.type==='pointerup'&&to!==index){const [item]=entries.splice(index,1);entries.splice(to,0,item);window.prepSelected=to;changed();$('rows').children[to]?.focus();message(`已移到第 ${to+1} 页，保存后生效`);}}
  function cancel(ev){end(ev);}
  row.addEventListener('pointermove',move);row.addEventListener('pointerup',end);row.addEventListener('pointercancel',cancel);
 };
}
