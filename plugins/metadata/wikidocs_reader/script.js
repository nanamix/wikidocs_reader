(async function(pluginId,container){
'use strict';
const $=s=>container.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DEBUG_LOG_KEY='wikidocs_reader_browser_logs'; const DEBUG_LOG_MAX=50;
function debugRead(){try{const v=JSON.parse(localStorage.getItem(DEBUG_LOG_KEY)||'[]');return Array.isArray(v)?v.slice(-DEBUG_LOG_MAX):[]}catch(_){return[]}}
function debugWrite(v){try{localStorage.setItem(DEBUG_LOG_KEY,JSON.stringify(v.slice(-DEBUG_LOG_MAX)))}catch(_){} }
function debugSnapshot(type,extra={}){const n=$('.wd-reader-topbar');const cs=n?getComputedStyle(n):null;const r=n?n.getBoundingClientRect():null;const vv=window.visualViewport;const e={type,timestamp:new Date().toISOString(),fullscreen:!!document.fullscreenElement,devicePixelRatio:window.devicePixelRatio,viewport:{innerWidth:window.innerWidth,innerHeight:window.innerHeight,scale:vv?.scale??1,width:vv?.width??null,height:vv?.height??null,offsetTop:vv?.offsetTop??null,offsetLeft:vv?.offsetLeft??null},topbarExists:!!n,hidden:n?n.hidden:null,display:cs?.display||null,visibility:cs?.visibility||null,width:r?.width||0,height:r?.height||0,zIndex:cs?.zIndex||null,...extra};const logs=debugRead();logs.push(e);debugWrite(logs);}
function scheduleDebug(type,extra){debugSnapshot(type,extra)}
window.addEventListener('error',e=>scheduleDebug('window_error',{message:String(e.message||''),source:e.filename||'',line:e.lineno||0,column:e.colno||0}));window.addEventListener('unhandledrejection',e=>scheduleDebug('unhandled_rejection',{message:String(e.reason?.message||e.reason||'')}));document.addEventListener('fullscreenchange',()=>scheduleDebug('fullscreenchange'));window.addEventListener('resize',()=>scheduleDebug('resize'));document.addEventListener('visibilitychange',()=>scheduleDebug('visibilitychange'));['dblclick','pointerdown','pointerup','touchstart','touchend'].forEach(type=>document.addEventListener(type,e=>scheduleDebug(type,{target:e.target?.id||e.target?.className||e.target?.tagName||''}),{passive:true}));if(window.visualViewport){window.visualViewport.addEventListener('resize',()=>scheduleDebug('visualViewport_resize'));window.visualViewport.addEventListener('scroll',()=>scheduleDebug('visualViewport_scroll'));}
const interactionInFlight=new Map();
function interactionKey(op,context={}){const keys=Object.keys(context).filter(k=>k!=='position').sort();return op+'|'+keys.map(k=>k+':'+String(context[k])).join('|')}
async function api(op,context={}){
 const r=await fetch('/bookoasis/api/media/context-menu/book/plugins/action',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({plugin_id:pluginId,action_id:'wikidocs_rpc',context:{op,...context}})});
 const d=await r.json();if(!r.ok||d.success===false)throw Error(d.error||'요청에 실패했습니다.');return d
}
function runInteraction(op,context={},options={}){
 const key=options.key||interactionKey(op,context);
 const existing=interactionInFlight.get(key); if(existing)return existing;
 const request=(async()=>api(op,context))(); let tracked;
 tracked=request.finally(()=>{if(interactionInFlight.get(key)===tracked)interactionInFlight.delete(key)});
 interactionInFlight.set(key,tracked); return tracked;
}
const latestInteractionState=new Map();
function runLatestInteraction(op,context,key){
 let state=latestInteractionState.get(key);
 if(state){state.context=context;return state.promise}
 state={context,promise:null};
 state.promise=(async()=>{try{while(state.context){const next=state.context;state.context=null;await api(op,next)}}finally{latestInteractionState.delete(key)}})();
 latestInteractionState.set(key,state);return state.promise
}
function withButtonLock(button,work){
 if(!button||button.dataset.wdBusy==='1')return Promise.resolve(null);
 button.dataset.wdBusy='1';button.setAttribute('aria-busy','true');
 const label=button.textContent;let timer=setTimeout(()=>{button.dataset.wdLoadingLabel=label;button.textContent='⟳ '+label},180);
 return Promise.resolve().then(work).finally(()=>{clearTimeout(timer);if(button.dataset.wdLoadingLabel!==undefined){button.textContent=button.dataset.wdLoadingLabel;delete button.dataset.wdLoadingLabel}button.dataset.wdBusy='0';button.removeAttribute('aria-busy')});
}
async function sendBrowserLogs(){const button=$('#wd-browser-log-send'),status=$('#wd-browser-log-status');if(!button||button.dataset.wdBusy==='1')return;if(!debugRead().length){alert('전송할 브라우저 로그가 없습니다.');return}return withButtonLock(button,async()=>{if(status)status.textContent='';const events=debugRead();const r=await fetch('/bookoasis/api/media/context-menu/book/plugins/action',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({plugin_id:pluginId,action_id:'wikidocs_rpc',context:{op:'browser_debug',enabled:true,events}})});const d=await r.json().catch(()=>({}));if(!r.ok||d.success===false)throw Error(d.error||'브라우저 로그 전송에 실패했습니다.');alert(`브라우저 로그 ${events.length}개를 전송했습니다.`)})}
let debugToolsVisible=false;function setDebugToolsVisible(visible){debugToolsVisible=visible;const n=$('.wd-debug-tools');if(n)n.hidden=!visible;}
setDebugToolsVisible(false);let debugTitleLastTap=0;$('#wd-debug-title')?.addEventListener('dblclick',()=>{setDebugToolsVisible(!debugToolsVisible);scheduleDebug('debug_tools_toggle',{visible:debugToolsVisible});});
function showError(e){console.error('[WikiDocs]',e);const n=$('#wd-error');if(n)n.textContent=e.message||String(e)}
async function search(){const q=$('#wd-query').value.trim();if(!q)return;const resultNode=$('#wd-results');resultNode.innerHTML='<div class="wd-page-loading" aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>검색 중...</span></div>';const d=await api('search',{query:q,page:1});$('#wd-results').innerHTML=d.items.map(x=>`<article class="wd-result"><b>${esc(x.title)}</b><small>#${x.wikidocs_book_id}</small><button data-add="${x.wikidocs_book_id}">내 책에 추가</button></article>`).join('')||'<p>검색 결과가 없습니다.</p>'}
let publicPage=1;
async function loadPublicBooks(page=publicPage, fromPagination=false){publicPage=Math.max(1,page);const n=$('#wd-public-books');n.innerHTML='<div class="wd-page-loading" aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>불러오는 중...</span></div>';const d=await api('public_books',{page:publicPage});n.innerHTML=d.items.map(x=>`<article class="wd-result"><b>${esc(x.title)}</b><small>${esc(x.author||'')} ${esc(x.published_at||'')}</small><div class="wd-book-actions">${x.in_my_books?`<button data-public-open="${x.book_id}">이어 읽기</button>`:`<button data-public-add="${x.wikidocs_book_id}">내 책에 추가</button>`}<a href="${esc(x.url)}" target="_blank" rel="noopener">WikiDocs에서 보기</a></div></article>`).join('')||'<p>공개 도서를 불러오지 못했습니다.</p>';const pg=$('#wd-public-pagination');pg.innerHTML=`<button data-public-page="${publicPage-1}" ${d.has_prev?'':'disabled'}>이전</button><span>${publicPage} 페이지</span><button data-public-page="${publicPage+1}" ${d.has_next?'':'disabled'}>다음</button>`; if(fromPagination) document.getElementById('wd-public-books').scrollIntoView({behavior:'smooth',block:'start'})}
async function loadBooks(){const n=$('#wd-books');n.innerHTML='<div class="wd-page-loading" aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>불러오는 중...</span></div>';const d=await api('books');const items=(d.items||[]).filter(x=>!x.progress?.is_completed);$('#wd-books').innerHTML=items.map(x=>{const pr=x.progress||{};const pct=Number(pr.total_pages)>0?Math.round(Number(pr.pages_read||0)/Number(pr.total_pages)*100):0;return `<article class="wd-result"><b>${esc(x.title)}</b><small>${pct+'%'}</small><div class="wd-book-actions"><button data-book="${x.id}">열기</button><button data-complete-book="${x.id}">읽음 완료</button></div></article>`}).join('')||'<p>내 책이 없습니다.</p>'}
async function openBook(id){scheduleDebug('open_start',{bookId:Number(id)});const modal=$('#wd-reader-modal');modal.hidden=false;document.body.classList.add('wd-reader-open');$('#wd-reader').innerHTML='<div class="wd-loading" aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>로딩 중...</span></div>';await enterReaderFullscreen();scheduleDebug('fullscreen_complete');const d=await api('detail',{book_id:id});const pages=d.pages||[];let p=d.progress||{};const title=String(d.book?.title||'');const titleChars=[...title];const titleLimit=window.matchMedia('(min-width:801px)').matches?25:10;$('#wd-reader-brand').textContent=titleChars.length>titleLimit?titleChars.slice(0,titleLimit).join('')+'...':title;$('#wd-reader').innerHTML=`<select id="wd-toc-select" class="wd-toc-select" aria-label="책 목차">${pages.map((x,i)=>`<option value="${i}">${esc(x.title)}</option>`).join('')}</select><div id="wd-pages" class="wd-pages"><div id="wd-loading" class="wd-loading" hidden aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>로딩 중...</span></div><article id="wd-content">페이지를 선택하세요.</article><article id="wd-content-right" hidden></article></div><nav class="wd-nav"><button id="wd-prev">이전</button><button id="wd-next">다음</button></nav>`;
let idx=Number(p.page_id?pages.findIndex(x=>x.id===p.page_id):-1); if(idx<0)idx=0;
async function openPage(i,restore=true){
 if(!pages.length)return;
 idx=Math.max(0,Math.min(i,pages.length-1));
 const select=$('#wd-toc-select'); if(select)select.value=String(idx);
 const x=pages[idx];
 const loader=$('#wd-loading'); if(loader)loader.hidden=false;
 const el=$('#wd-content'); if(el)el.hidden=true;
 try {
  const pd=await api('page',{book_id:id,page_id:x.id});
  el.innerHTML=pd.page.content_html||'';
 } finally {
  if(loader)loader.hidden=true;
  if(el)el.hidden=false;
 }
 const right=$('#wd-content-right');
 if(right){right.hidden=true;right.innerHTML=''}
 if(false){
  const pd2=await api('page',{book_id:id,page_id:pages[idx+1].id});
  right.innerHTML=pd2.page.content_html||'';
 }else if(right) right.innerHTML='';
 const total=pages.length, savedPage=Number(p.page_id||0), savedPosition=Number(p.position||0);
 if(restore&&savedPage===Number(x.id)&&savedPosition>0) requestAnimationFrame(()=>{const max=Math.max(0,el.scrollHeight-el.clientHeight);el.scrollTop=Math.max(0,Math.min(max,max*savedPosition));});
 else el.scrollTop=0;
 if(!(restore&&savedPage===Number(x.id))) await runInteraction('progress',{book_id:id,page_id:x.id,position:0,pages_read:idx+1,total_pages:total},{key:`progress-page|${id}|${x.id}`});
}
$('#wd-toc-select').onchange=e=>openPage(Number(e.target.value)).catch(showError);const pageStep=()=>1;$('#wd-prev').onclick=()=>openPage(idx-pageStep()).catch(showError);$('#wd-next').onclick=()=>openPage(idx+pageStep()).catch(showError);
let saveTimer;const content=$('#wd-content');content.onscroll=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>{const max=Math.max(1,content.scrollHeight-content.clientHeight);runLatestInteraction('progress',{book_id:id,page_id:pages[idx]?.id,position:content.scrollTop/max,pages_read:idx+1,total_pages:pages.length},`progress-scroll|${id}`).catch(showError)},300)};
await openPage(idx);scheduleDebug('open_complete');}

let autoScrollTimer=null,autoScrollSpeed=1;function stopAutoScroll(){if(autoScrollTimer){clearInterval(autoScrollTimer);autoScrollTimer=null}const b=$('#wd-reader-autoscroll');if(b){b.textContent='▶';b.setAttribute('aria-label','자동 스크롤 시작')}}function startAutoScroll(){stopAutoScroll();const el=$('#wd-content');if(!el)return;const b=$('#wd-reader-autoscroll');if(b){b.textContent='Ⅱ';b.setAttribute('aria-label','자동 스크롤 정지')}let target=el;autoScrollTimer=setInterval(()=>{const max=target.scrollHeight-target.clientHeight;if(max<=1||target.scrollTop>=max-1){stopAutoScroll();return}target.scrollTop=Math.min(max,target.scrollTop+autoScrollSpeed)},50)}function setAutoScrollSpeed(v){autoScrollSpeed=Number(v)||1;if(autoScrollTimer)startAutoScroll()}async function enterReaderFullscreen(){const el=$('#wd-reader-dialog');if(!el||!document.fullscreenEnabled||!el.requestFullscreen)return false;try{await el.requestFullscreen({navigationUI:'hide'});return true}catch(e){console.debug('Fullscreen unavailable:',e);return false}}async function exitReaderFullscreen(){if(document.fullscreenElement){try{await document.exitFullscreen()}catch(e){console.debug('Fullscreen exit failed:',e)}}}async function closeReader(){scheduleDebug('close_start');stopAutoScroll();await exitReaderFullscreen();const modal=$('#wd-reader-modal');modal.hidden=true;document.body.classList.remove('wd-reader-open');$('#wd-reader').innerHTML='';scheduleDebug('close_complete')}
$('#wd-reader-close').onclick=()=>closeReader();$('#wd-reader-autoscroll').onclick=()=>autoScrollTimer?stopAutoScroll():startAutoScroll();$('#wd-reader-speed').onchange=e=>setAutoScrollSpeed(e.target.value);$('#wd-reader-theme').onclick=()=>{const d=document.querySelector('.wd-reader-dialog');const dark=d.classList.toggle('wd-reader-dark');$('#wd-reader-theme').textContent=dark?'☀':'☾';$('#wd-reader-theme').setAttribute('aria-label',dark?'화이트 모드':'다크 모드')};$('#wd-reader-modal').onclick=e=>{if(e.target===e.currentTarget)closeReader()};document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#wd-reader-modal').hidden)closeReader()});
$('#wd-browser-log-send').onclick=()=>sendBrowserLogs().catch(showError);$('#wd-search').onclick=()=>search().catch(showError);$('#wd-query').onkeydown=e=>{if(e.key==='Enter')search().catch(showError)};$('#wd-public-pagination').onclick=e=>{const p=e.target.dataset.publicPage;if(p&&!e.target.disabled)loadPublicBooks(Number(p),true).catch(showError)};$('#wd-public-books').onclick=async e=>{const add=e.target.dataset.publicAdd;if(add){try{const added=await withButtonLock(e.target,()=>runInteraction('add',{remote_id:add},{key:`add|${add}`}));await loadBooks();await loadPublicBooks(publicPage);await openBook(Number(added.book_id))}catch(err){showError(err)}}const open=e.target.dataset.publicOpen;if(open)openBook(Number(open)).catch(showError)};$('#wd-results').onclick=e=>{const id=e.target.dataset.add;if(id)withButtonLock(e.target,()=>runInteraction('add',{remote_id:id},{key:`add|${id}`})).then(loadBooks).catch(showError)};$('#wd-books').onclick=async e=>{const id=e.target.dataset.book;if(id){openBook(id).catch(showError);return}const complete=e.target.dataset.completeBook;if(complete){try{const d=await api('detail',{book_id:Number(complete)});await withButtonLock(e.target,()=>runInteraction('complete',{book_id:Number(complete),total_pages:(d.pages||[]).length},{key:`complete|${complete}`}));await loadBooks()}catch(err){showError(err)}return}const reset=e.target.dataset.resetBook;if(reset){try{await withButtonLock(e.target,()=>runInteraction('reset',{book_id:Number(reset)},{key:`reset|${reset}`}));await loadBooks()}catch(err){showError(err)}}};await Promise.all([loadPublicBooks().catch(showError),loadBooks().catch(showError)]);
})(pluginId,container);
