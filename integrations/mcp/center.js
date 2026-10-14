'use strict';
const $=id=>document.getElementById(id);let csrf='',secret='',config='',keyRows=[];
const message=text=>{$('message').textContent=text;};
async function api(path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);try{const r=await fetch('api/'+path,{method:body?'POST':'GET',credentials:'same-origin',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:body?JSON.stringify(body):undefined,signal:controller.signal});const d=await r.json();if(!r.ok)throw Error(d.error||'请求失败');return d;}finally{clearTimeout(timer);}}
async function copy(text){try{await navigator.clipboard.writeText(text);message('已复制');}catch{message('复制失败，请手动选择内容并复制。');}}
function node(tag,text){const e=document.createElement(tag);e.textContent=text;return e;}
const date=value=>value?new Date(value*1000).toLocaleDateString('zh-CN'):'旧记录';
async function load(){
 const [directory,courses,keys]=await Promise.all([api('services'),api('collections'),api('keys')]);
 $('services').replaceChildren();for(const s of directory.services){const block=node('div','');block.className='service';block.append(node('strong',s.name),node('p',s.description||''),node('pre',s.url));const button=node('button','复制地址');button.onclick=()=>copy(s.url);block.append(button,node('p',s.key_management?'已接入密钥管理 · LivePage 只读工具':'已登记 · 尚未接入密钥管理，运行状态未核验'));$('services').append(block);}
 $('overview').textContent=directory.services.length+' 个服务 · '+keys.keys.filter(k=>!k.revoked&&k.expires_at*1000>Date.now()).length+' 把有效密钥';
 const checked=new Set([...$('courses').querySelectorAll('input:checked')].map(x=>x.value));
 $('courses').replaceChildren();for(const c of courses.collections){const label=node('label',''),input=document.createElement('input');input.type='checkbox';input.value=c.id;input.checked=checked.has(c.id);input.onchange=updateScope;label.append(input,document.createTextNode(' '+c.name+' · '+c.pages+' 页'));$('courses').append(label);}
 keyRows=keys.keys;renderKeys();updateScope();filterCourses();
}
function renderKeys(){
 $('keys').replaceChildren();const term=$('key-search').value.trim().toLowerCase(),filter=$('key-filter').value;const visible=keyRows.filter(k=>{const state=k.revoked?'revoked':k.expires_at*1000<Date.now()?'expired':'active';return (filter==='all'||state===filter)&&((k.name||k.client_id)+' '+(k.suffix||'')).toLowerCase().includes(term);});for(const k of visible){const row=node('div','');row.className='key';const expired=k.expires_at*1000<Date.now();const info=node('div','');info.append(node('strong',k.name||k.client_id),node('p',(k.suffix?'末尾 '+k.suffix+' · ':'')+(k.revoked?'已撤销':expired?'已到期':'有效')+' · 到期 '+date(k.expires_at)+' · '+(k.allowed_decks||[]).length+' 份课程 · '+(k.asset_download?'可下载素材':'只读内容')));row.append(info);if(!k.revoked){const button=node('button','撤销');button.onclick=async()=>{if(!confirm('撤销这把密钥？使用它的 Agent 将无法继续调用。'))return;try{await api('keys/'+encodeURIComponent(k.client_id)+'/revoke',{service:'livepage'});await load();message('已撤销');}catch(e){message(e.message);}};row.append(button);}$('keys').append(row);}if(!visible.length)$('keys').textContent=keyRows.length?'没有符合条件的密钥，可切换状态或搜索其他备注。':'还没有密钥，点击“生成密钥”连接你的第一个 Agent。';
}
$('select-all').onclick=()=>{const inputs=[...$('courses').querySelectorAll('input')];inputs.forEach((x,i)=>x.checked=i<20);updateScope();if(inputs.length>20)message('已选择前20份课程，可手动调整。');};
$('key-form').onsubmit=async e=>{e.preventDefault();$('generate').disabled=true;try{const d=await api('keys',{name:$('key-name').value,days:Number($('days').value),allowed_decks:[...$('courses').querySelectorAll('input:checked')].map(x=>x.value),asset_download:$('download').checked});secret=d.key;config=JSON.stringify({mcpServers:{livepage:{type:'http',url:'https://qiuyiwu.com/mcp/livepage',headers:{Authorization:'Bearer '+secret}}}},null,2);$('token').textContent=secret;$('config').textContent=config;$('secret').hidden=false;$('create-panel').open=false;$('secret').scrollIntoView({block:'start',behavior:'smooth'});message('密钥已生成，请现在保存。');try{await load();}catch{message('密钥已生成，请先保存；列表刷新失败可稍后重试。');}}catch(e){message(e.message);}finally{updateScope();}};
$('dismiss').onclick=()=>{secret='';config='';$('token').textContent='';$('config').textContent='';$('secret').hidden=true;};
$('copy-key').onclick=()=>copy(secret);$('copy-config').onclick=()=>copy(config);$('copy-brief').onclick=()=>copy($('brief').textContent);
$('service-form').onsubmit=async e=>{e.preventDefault();try{await api('services',{name:$('service-name').value,url:$('service-url').value,description:$('service-description').value});e.target.reset();await load();message('服务已登记，密钥适配尚未接入。');}catch(e){message(e.message);}};
$('refresh').onclick=()=>load().catch(e=>message(e.message));
(async()=>{try{csrf=(await api('session')).csrf;await load();}catch(e){message('加载失败：'+e.message);$('generate').disabled=true;}})();

function updateScope(){const count=$('courses').querySelectorAll('input:checked').length;$('scope-count').textContent='已选 '+count+' / 20 份';$('generate').disabled=!csrf||count===0||count>20;}
function filterCourses(){const term=$('course-search').value.trim().toLowerCase();for(const label of $('courses').querySelectorAll('label'))label.hidden=!label.textContent.toLowerCase().includes(term);}
function openCreate(){if(secret){message('请先保存当前密钥，再点击“我已保存，隐藏密钥”。');$('secret').scrollIntoView({block:'start'});return;}$('create-panel').open=true;$('create-panel').scrollIntoView({block:'start',behavior:'smooth'});$('key-name').focus({preventScroll:true});}
$('open-create').onclick=openCreate;$('open-create-secondary').onclick=openCreate;$('cancel-create').onclick=()=>{$('create-panel').open=false;};
$('course-search').oninput=filterCourses;$('key-search').oninput=renderKeys;$('key-filter').onchange=renderKeys;
