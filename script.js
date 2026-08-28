(async function(pluginId, container) {
'use strict';

class Dom {
  constructor(root) { this.root = root; }
  $(selector) { return this.root.querySelector(selector); }
  on(selector, event, handler, options) {
    const node = this.$(selector); if (node) node.addEventListener(event, handler, options);
    return node;
  }
}

class WikiDocsApi {
  constructor(fetchImpl, pluginId) { this.fetch = fetchImpl; this.pluginId = pluginId; }
  async call(op, context = {}) {
    const response = await this.fetch('/bookoasis/api/media/context-menu/book/plugins/action', {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({plugin_id: this.pluginId, action_id: 'wikidocs_rpc', context: {op, ...context}})
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) throw Error(data.error || '요청에 실패했습니다.');
    return data;
  }
}

class InteractionQueue {
  constructor(api) { this.api = api; this.inFlight = new Map(); this.latest = new Map(); }
  key(op, context = {}) {
    return op + '|' + Object.keys(context).filter(k => k !== 'position').sort().map(k => k + ':' + String(context[k])).join('|');
  }
  run(op, context = {}, options = {}) {
    const key = options.key || this.key(op, context), existing = this.inFlight.get(key);
    if (existing) return existing;
    const request = this.api.call(op, context);
    let tracked = request.finally(() => { if (this.inFlight.get(key) === tracked) this.inFlight.delete(key); });
    this.inFlight.set(key, tracked); return tracked;
  }
  runLatest(op, context, key) {
    let state = this.latest.get(key);
    if (state) { state.context = context; return state.promise; }
    state = {context, promise: null};
    state.promise = (async () => {
      try { let result=null; while (state.context) { const next = state.context; state.context = null; result=await this.api.call(op, next); } return result; }
      finally { this.latest.delete(key); }
    })();
    this.latest.set(key, state); return state.promise;
  }
}

class LoadingManager {
  constructor(dom) { this.dom = dom; }
  page(node, label) {
    if (node) node.innerHTML = `<div class="wd-page-loading" aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>${label}</span></div>`;
  }
  reader(node) {
    if (node) node.innerHTML = '<div class="wd-loading" aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>로딩 중...</span></div>';
  }
}

class ButtonBusyGuard {
  run(button, work) {
    if (!button || button.dataset.wdBusy === '1') return Promise.resolve(null);
    button.dataset.wdBusy = '1'; button.setAttribute('aria-busy', 'true');
    const label = button.textContent;
    const timer = setTimeout(() => { button.dataset.wdLoadingLabel = label; button.textContent = '⟳ ' + label; }, 180);
    return Promise.resolve().then(work).finally(() => {
      clearTimeout(timer);
      if (button.dataset.wdLoadingLabel !== undefined) { button.textContent = button.dataset.wdLoadingLabel; delete button.dataset.wdLoadingLabel; }
      button.dataset.wdBusy = '0'; button.removeAttribute('aria-busy');
    });
  }
}

class BrowserDebugLogger {
  constructor(dom, storage = window.localStorage) { this.dom = dom; this.storage = storage; this.key = 'wikidocs_reader_browser_logs'; this.max = 50; }
  read() { try { const value = JSON.parse(this.storage.getItem(this.key) || '[]'); return Array.isArray(value) ? value.slice(-this.max) : []; } catch (_) { return []; } }
  write(events) { try { this.storage.setItem(this.key, JSON.stringify(events.slice(-this.max))); } catch (_) {} }
  snapshot(type, extra = {}) {
    const node = this.dom.$('.wd-reader-topbar'), cs = node ? getComputedStyle(node) : null, rect = node ? node.getBoundingClientRect() : null, vv = window.visualViewport;
    this.write([...this.read(), {type, timestamp: new Date().toISOString(), fullscreen: !!document.fullscreenElement,
      devicePixelRatio: window.devicePixelRatio,
      viewport: {innerWidth: window.innerWidth, innerHeight: window.innerHeight, scale: vv?.scale ?? 1, width: vv?.width ?? null, height: vv?.height ?? null, offsetTop: vv?.offsetTop ?? null, offsetLeft: vv?.offsetLeft ?? null},
      topbarExists: !!node, hidden: node?.hidden ?? null, display: cs?.display || null, visibility: cs?.visibility || null,
      width: rect?.width || 0, height: rect?.height || 0, zIndex: cs?.zIndex || null, ...extra}]);
  }
  install() {
    const log = (type, extra) => this.snapshot(type, extra);
    window.addEventListener('error', e => log('window_error', {message: String(e.message || ''), source: e.filename || '', line: e.lineno || 0, column: e.colno || 0}));
    window.addEventListener('unhandledrejection', e => log('unhandled_rejection', {message: String(e.reason?.message || e.reason || '')}));
    document.addEventListener('fullscreenchange', () => log('fullscreenchange'));
    window.addEventListener('resize', () => log('resize'));
    document.addEventListener('visibilitychange', () => log('visibilitychange'));
    ['dblclick','pointerdown','pointerup','touchstart','touchend'].forEach(type => document.addEventListener(type, e => log(type, {target: e.target?.id || e.target?.className || e.target?.tagName || ''}), {passive: true}));
    if (window.visualViewport) { window.visualViewport.addEventListener('resize', () => log('visualViewport_resize')); window.visualViewport.addEventListener('scroll', () => log('visualViewport_scroll')); }
  }
}

class DebugPanel {
  constructor(dom, logger, busyGuard) { this.dom = dom; this.logger = logger; this.busy = busyGuard; this.visible = false; }
  setVisible(visible) { this.visible = visible; const panel = this.dom.$('.wd-debug-tools'); if (panel) panel.hidden = !visible; }
  async send(api) {
    const button = this.dom.$('#wd-browser-log-send');
    if (!button || button.dataset.wdBusy === '1') return;
    const events = this.logger.read();
    if (!events.length) { alert('전송할 브라우저 로그가 없습니다.'); return; }
    await this.busy.run(button, async () => {
      const data = await api.call('browser_debug', {enabled: true, events});
      alert(`브라우저 로그 ${events.length}개를 전송했습니다.`);
      return data;
    });
  }
  install(api) {
    this.setVisible(false);
    this.dom.on('#wd-debug-title', 'dblclick', () => { this.setVisible(!this.visible); this.logger.snapshot('debug_tools_toggle', {visible: this.visible}); });
    this.dom.on('#wd-browser-log-send', 'click', () => this.send(api).catch(showError));
  }
}

class LibraryController {
  constructor(dom, api, interactions, loading, busy) { this.dom = dom; this.api = api; this.interactions = interactions; this.loading = loading; this.busy = busy; this.publicPage = 1; this.publicSort = this.loadPublicSort(); }
  loadPublicSort() { try { const value = window.localStorage.getItem('wikidocs_reader_public_sort'); return ['recent','recommend','popular'].includes(value) ? value : 'recent'; } catch { return 'recent'; } }
  savePublicSort(value) { try { window.localStorage.setItem('wikidocs_reader_public_sort', value); } catch {} }
  esc(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  async search() {
    const query = this.dom.$('#wd-query')?.value.trim(); if (!query) return;
    const node = this.dom.$('#wd-results'); this.loading.page(node, '검색 중...');
    const data = await this.api.call('search', {query, page: 1});
    node.innerHTML = data.items.map(x => `<article class="wd-result"><b>${this.esc(x.title)}</b><small>#${x.wikidocs_book_id}</small><button data-add="${x.wikidocs_book_id}">내 책에 추가</button></article>`).join('') || '<p>검색 결과가 없습니다.</p>';
  }
  async loadPublicBooks(page = this.publicPage, fromPagination = false, sortType = this.publicSort) {
    this.publicPage = Math.max(1, page); this.publicSort = ['recent','recommend','popular'].includes(sortType) ? sortType : 'recent'; const node = this.dom.$('#wd-public-books'); const sort=this.dom.$('#wd-public-sort'); if(sort) sort.value=this.publicSort; this.loading.page(node, '불러오는 중...');
    const data = await this.api.call('public_books', {page: this.publicPage, sort_type: this.publicSort});
    node.innerHTML = data.items.map(x => `<article class="wd-result"><b>${this.esc(x.title)}</b><small>${this.esc(x.author || '')} ${this.esc(x.published_at || '')}</small><div class="wd-book-actions">${x.in_my_books ? `<button data-public-open="${x.book_id}">이어 읽기</button>` : `<button data-public-add="${x.wikidocs_book_id}">내 책에 추가</button>`}<a href="${this.esc(x.url)}" target="_blank" rel="noopener">WikiDocs에서 보기</a></div></article>`).join('') || '<p>공개 도서를 불러오지 못했습니다.</p>';
    const pagination = this.dom.$('#wd-public-pagination'); pagination.innerHTML = `<button data-public-page="${this.publicPage-1}" ${data.has_prev?'':'disabled'}>이전</button><span>${this.publicPage} 페이지</span><button data-public-page="${this.publicPage+1}" ${data.has_next?'':'disabled'}>다음</button>`;
    if (fromPagination) node.scrollIntoView({behavior:'smooth', block:'start'});
  }
  async loadBooks() {
    const node = this.dom.$('#wd-books'); this.loading.page(node, '불러오는 중...'); const data = await this.api.call('books');
    const items = (data.items || []).filter(x => !x.progress?.is_completed);
    node.innerHTML = items.map(x => { const p=x.progress||{}, pct=Number(p.total_pages)>0?Math.round(Number(p.pages_read||0)/Number(p.total_pages)*100):0; return `<article class="wd-result"><b>${this.esc(x.title)}</b><small>${pct}%</small><div class="wd-book-actions"><button data-book="${x.id}">열기</button><button data-complete-book="${x.id}">읽음 완료</button></div></article>`; }).join('') || '<p>내 책이 없습니다.</p>';
  }
  install(reader) {
    this.dom.on('#wd-search','click',()=>this.search().catch(showError));
    this.dom.on('#wd-query','keydown',e=>{if(e.key==='Enter')this.search().catch(showError);});
    this.dom.on('#wd-public-title','dblclick',()=>{const el=this.dom.$('#wd-public-sort');if(el){el.hidden=!el.hidden;if(!el.hidden)el.focus();}});
    this.dom.on('#wd-public-pagination','click',e=>{const page=e.target.dataset.publicPage;if(page&&!e.target.disabled)this.loadPublicBooks(Number(page),true).catch(showError);});
    this.dom.on('#wd-public-sort','change',e=>{const value=e.target.value;this.savePublicSort(value);this.loadPublicBooks(1,false,value).catch(showError);e.target.hidden=true;});
    this.dom.on('#wd-public-books','click',async e=>{const add=e.target.dataset.publicAdd, open=e.target.dataset.publicOpen;if(add){try{const added=await this.busy.run(e.target,()=>this.interactions.run('add',{remote_id:add},{key:`add|${add}`}));await this.loadBooks();await this.loadPublicBooks(this.publicPage);await reader.openBook(Number(added.book_id));}catch(err){showError(err)}} if(open)reader.openBook(Number(open)).catch(showError);});
    this.dom.on('#wd-results','click',e=>{const id=e.target.dataset.add;if(id)this.busy.run(e.target,()=>this.interactions.run('add',{remote_id:id},{key:`add|${id}`})).then(()=>this.loadBooks()).catch(showError);});
    this.dom.on('#wd-books','click',async e=>{const id=e.target.dataset.book, complete=e.target.dataset.completeBook, reset=e.target.dataset.resetBook;if(id){reader.openBook(id).catch(showError);return;}try{if(complete){const d=await this.api.call('detail',{book_id:Number(complete)});await this.busy.run(e.target,()=>this.interactions.run('complete',{book_id:Number(complete),total_pages:(d.pages||[]).length},{key:`complete|${complete}`}));await this.loadBooks();}else if(reset){await this.busy.run(e.target,()=>this.interactions.run('reset',{book_id:Number(reset)},{key:`reset|${reset}`}));await this.loadBooks();}}catch(err){showError(err)}});
  }
}

class ReaderController {
  constructor(dom, api, interactions, loading) { this.dom=dom;this.api=api;this.interactions=interactions;this.loading=loading;this.autoScrollTimer=null;this.autoScrollTransition=false;this.autoScrollSpeed=1;this.saveTimer=null;this.pages=[];this.index=0;this.bookId=null;this.progress={};this.pagePositions=new Map();this.storage=window.localStorage; }
  async enterFullscreen(){const el=this.dom.$('#wd-reader-dialog');if(!el||!document.fullscreenEnabled||!el.requestFullscreen)return false;try{await el.requestFullscreen({navigationUI:'hide'});return true;}catch(e){console.debug('Fullscreen unavailable:',e);return false;}}
  async exitFullscreen(){if(document.fullscreenElement)try{await document.exitFullscreen()}catch(e){console.debug('Fullscreen exit failed:',e)}}
  async openBook(id){this.bookId=Number(id);this.dom.$('#wd-reader-modal').hidden=false;document.body.classList.add('wd-reader-open');this.loading.reader(this.dom.$('#wd-reader'));await this.enterFullscreen();const data=await this.api.call('detail',{book_id:this.bookId});this.pages=data.pages||[];this.progress=data.progress||{};this.pagePositions=this.loadPagePositions();if(this.progress.page_id!=null&&!this.pagePositions.has(Number(this.progress.page_id)))this.pagePositions.set(Number(this.progress.page_id),Math.max(0,Math.min(1,Number(this.progress.position||0))));const title=String(data.book?.title||'');const titleChars=[...title];const limit=window.matchMedia('(min-width:801px)').matches?25:10;this.dom.$('#wd-reader-brand').textContent=titleChars.slice(0,limit).join('')+(titleChars.length>limit?'...':'');this.renderShell();const savedPageId=this.getSavedPageId();const targetPageId=savedPageId??this.progress.page_id;this.index=Math.max(0,this.pages.findIndex(x=>x.id===targetPageId));if(this.index<0)this.index=0;await this.openPage(this.index,true,false);}
  positionStorageKey(){return `wikidocs_reader_positions_${this.bookId}`;}
  getSavedPageId(){try{const raw=this.storage.getItem(this.positionStorageKey());const data=raw?JSON.parse(raw):{};const id=Number(data.__currentPageId);return Number.isFinite(id)&&id>0?id:null;}catch{return null;}}
  loadPagePositions(){try{const raw=this.storage.getItem(this.positionStorageKey());const data=raw?JSON.parse(raw):{};return new Map(Object.entries(data).filter(([k])=>k!=='__currentPageId').map(([k,v])=>[Number(k),Math.max(0,Math.min(1,Number(v)))]).filter(([k,v])=>Number.isFinite(k)&&Number.isFinite(v)));}catch{return new Map();}}
  persistPagePositions(){try{const data={};for(const [k,v] of this.pagePositions)data[k]=v;data.__currentPageId=this.pages[this.index]?.id??null;this.storage.setItem(this.positionStorageKey(),JSON.stringify(data));}catch{}}
  renderShell(){this.dom.$('#wd-reader').innerHTML=`<select id="wd-toc-select" class="wd-toc-select" aria-label="책 목차">${this.pages.map((x,i)=>`<option value="${i}">${this.esc(x.title)}</option>`).join('')}</select><div id="wd-pages" class="wd-pages"><div id="wd-loading" class="wd-loading" hidden aria-live="polite"><span class="wd-loading-spinner" aria-hidden="true"></span><span>로딩 중...</span></div><article id="wd-content">페이지를 선택하세요.</article><article id="wd-content-right" hidden></article></div><nav class="wd-nav"><button id="wd-prev">이전</button><button id="wd-next">다음</button></nav>`;this.dom.on('#wd-toc-select','change',e=>this.openPage(Number(e.target.value)).catch(showError));this.dom.on('#wd-prev','click',()=>this.openPage(this.index-1).catch(showError));this.dom.on('#wd-next','click',()=>this.openPage(this.index+1).catch(showError));const content=this.dom.$('#wd-content');content.onscroll=()=>{clearTimeout(this.saveTimer);this.saveTimer=setTimeout(()=>{this.saveCurrentPosition().catch(showError)},300);};}
  async saveCurrentPosition(){clearTimeout(this.saveTimer);this.saveTimer=null;const el=this.dom.$('#wd-content'),page=this.pages[this.index];if(!el||!page)return;const max=Math.max(1,el.scrollHeight-el.clientHeight),position=Math.max(0,Math.min(1,el.scrollTop/max));this.pagePositions.set(Number(page.id),position);this.persistPagePositions();const data=await this.interactions.runLatest('progress',{book_id:this.bookId,page_id:page.id,position,pages_read:this.index+1,total_pages:this.pages.length},`progress-scroll|${this.bookId}`);if(data?.progress)this.progress=data.progress;}

  esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  async openPage(index,restore=true,saveCurrent=true){if(!this.pages.length)return;const wasAutoScrolling=!!this.autoScrollTimer&&!this.autoScrollTransition;this.stopAutoScroll();if(saveCurrent)await this.saveCurrentPosition();this.index=Math.max(0,Math.min(index,this.pages.length-1));const select=this.dom.$('#wd-toc-select');if(select)select.value=String(this.index);const loader=this.dom.$('#wd-loading'),el=this.dom.$('#wd-content'),page=this.pages[this.index];if(loader)loader.hidden=false;if(el)el.hidden=true;try{const data=await this.api.call('page',{book_id:this.bookId,page_id:page.id});el.innerHTML=data.page.content_html||'';}finally{if(loader)loader.hidden=true;if(el)el.hidden=false;}if(restore){const images=el.querySelectorAll?Array.from(el.querySelectorAll('img')).filter(img=>!img.complete):[];if(images.length)await Promise.all(images.map(img=>new Promise(resolve=>{img.addEventListener('load',resolve,{once:true});img.addEventListener('error',resolve,{once:true});})));}const right=this.dom.$('#wd-content-right');if(right){right.hidden=true;right.innerHTML='';}const savedPosition=this.pagePositions.get(Number(page.id));if(restore&&savedPosition!=null){const applyPosition=()=>{const max=Math.max(0,el.scrollHeight-el.clientHeight);el.scrollTop=Math.max(0,Math.min(max,max*savedPosition));};requestAnimationFrame(()=>requestAnimationFrame(applyPosition));}else el.scrollTop=0;if(!this.pagePositions.has(Number(page.id))){const data=await this.interactions.run('progress',{book_id:this.bookId,page_id:page.id,position:0,pages_read:this.index+1,total_pages:this.pages.length},{key:`progress-page|${this.bookId}|${page.id}`});this.pagePositions.set(Number(page.id),0);this.persistPagePositions();if(data?.progress)this.progress=data.progress;}if(wasAutoScrolling)this.startAutoScroll();}
  stopAutoScroll(){if(this.autoScrollTimer){clearInterval(this.autoScrollTimer);this.autoScrollTimer=null}const b=this.dom.$('#wd-reader-autoscroll');if(b){b.textContent='▶';b.setAttribute('aria-label','자동 스크롤 시작');}}
  startAutoScroll(){this.stopAutoScroll();const el=this.dom.$('#wd-content');if(!el)return;const b=this.dom.$('#wd-reader-autoscroll');if(b){b.textContent='Ⅱ';b.setAttribute('aria-label','자동 스크롤 정지');}this.autoScrollTimer=setInterval(async()=>{const current=this.dom.$('#wd-content');if(!current)return;const max=current.scrollHeight-current.clientHeight;if(max<=1||current.scrollTop>=max-1){if(this.index<this.pages.length-1){this.autoScrollTransition=true;this.stopAutoScroll();try{await this.openPage(this.index+1,false);if(this.index<this.pages.length)this.startAutoScroll();}catch(e){showError(e);this.stopAutoScroll();}finally{this.autoScrollTransition=false;}}else this.stopAutoScroll();return;}current.scrollTop=Math.min(max,current.scrollTop+this.autoScrollSpeed)},50);}
  setSpeed(value){this.autoScrollSpeed=Number(value)||1;if(this.autoScrollTimer)this.startAutoScroll();}
  async close(){this.stopAutoScroll();if(this.bookId&&this.pages.length)await this.saveCurrentPosition();await this.exitFullscreen();const modal=this.dom.$('#wd-reader-modal');modal.hidden=true;document.body.classList.remove('wd-reader-open');this.dom.$('#wd-reader').innerHTML='';}
  install(){this.dom.on('#wd-reader-close','click',()=>this.close().catch(showError));this.dom.on('#wd-reader-autoscroll','click',()=>this.autoScrollTimer?this.stopAutoScroll():this.startAutoScroll());this.dom.on('#wd-reader-speed','change',e=>this.setSpeed(e.target.value));this.dom.on('#wd-reader-theme','click',()=>{const d=this.dom.$('.wd-reader-dialog'),dark=d.classList.toggle('wd-reader-dark'),b=this.dom.$('#wd-reader-theme');b.textContent=dark?'☀':'☾';b.setAttribute('aria-label',dark?'화이트 모드':'다크 모드');});this.dom.on('#wd-reader-modal','click',e=>{if(e.target===e.currentTarget)this.close().catch(showError)});document.addEventListener('keydown',e=>{const modal=this.dom.$('#wd-reader-modal');if(!modal||modal.hidden)return;if(e.key==='Escape'){this.close().catch(showError);return;}if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','PageUp','PageDown','Home','End'].includes(e.key))return;const target=e.target;if(target instanceof HTMLInputElement||target instanceof HTMLTextAreaElement||target instanceof HTMLSelectElement||target instanceof HTMLButtonElement||target?.isContentEditable)return;if(e.key==='Home'||e.key==='End'||e.key==='ArrowUp'||e.key==='ArrowDown'||e.key==='PageUp'||e.key==='PageDown'){e.preventDefault();const content=this.dom.$('#wd-content');if(!content)return;if(e.key==='Home'||e.key==='End'){content.scrollTo({top:e.key==='Home'?0:content.scrollHeight,behavior:'smooth'});return;}const amount=e.key==='PageUp'||e.key==='PageDown'?content.clientHeight:Math.max(40,Math.round(content.clientHeight*0.15));content.scrollBy({top:(e.key==='ArrowUp'||e.key==='PageUp'?-1:1)*amount,behavior:'smooth'});return;}e.preventDefault();const nextIndex=this.index+(e.key==='ArrowLeft'?-1:1);if(nextIndex>=0&&nextIndex<this.pages.length)this.openPage(nextIndex).catch(showError);});}
}

function showError(error){console.error('[WikiDocs]',error);const node=container.querySelector('#wd-error');if(node)node.textContent=error?.message||String(error);}

const dom=new Dom(container), api=new WikiDocsApi(window.fetch.bind(window),pluginId), interactions=new InteractionQueue(api), loading=new LoadingManager(dom), busy=new ButtonBusyGuard();
const logger=new BrowserDebugLogger(dom), debug=new DebugPanel(dom,logger,busy), reader=new ReaderController(dom,api,interactions,loading), library=new LibraryController(dom,api,interactions,loading,busy);
logger.install();debug.install(api);reader.install();library.install(reader);
await Promise.all([library.loadPublicBooks().catch(showError),library.loadBooks().catch(showError)]);
})(pluginId, container);
