const BASE_PATH = '/welfare-time';
const API_BASE = `${BASE_PATH}/api/schedule`;
const STATUS_API = `${BASE_PATH}/api/status`;
const LABE_NOW_OPEN = '🟢 営業中';
const LABE_PREPARING = '🟡 準備中';
const LABE_CLOSED = '🔵 営業終了';

let currentData = null;
let master = null;

// Path detection
const currentPath = window.location.pathname.replace(/\/$/, '');
const isMapPage = currentPath.endsWith('/map') || currentPath.endsWith('/map/index.html') || currentPath.endsWith('/map.html');
const isListPage = currentPath.endsWith('/list') || currentPath.endsWith('/list/index.html') || currentPath.endsWith('/list.html');

const currentView = (isMapPage || isListPage) ? 'list' : (localStorage.getItem('ksu-harapeco-view') || 'grid');

function getTargetDateStr() {
    const urlParams = new URLSearchParams(window.location.search);
    let dateStr = urlParams.get('date');
    if (!dateStr || dateStr === 'today') {
        dateStr = new Date().toLocaleDateString('sv-SE');
    }
    return dateStr;
}

function getShopStatus(startTime, endTime, targetDateStr) {
    const closedStatus = { label: '休業', class: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' };
    if (!startTime || !endTime || startTime === '00:00') return closedStatus;
    const now = new Date();
    const todayStr = now.toLocaleDateString('sv-SE');
    if (targetDateStr < todayStr) return { label: LABE_CLOSED, class: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' };
    if (targetDateStr > todayStr) return { label: LABE_PREPARING, class: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' };

    const nowTotal = now.getHours() * 60 + now.getMinutes();
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    if (nowTotal < (sh*60+sm)) return { label: LABE_PREPARING, class: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' };
    if (nowTotal >= (sh*60+sm) && nowTotal < (eh*60+em)) return { label: LABE_NOW_OPEN, class: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' };
    return { label: LABE_CLOSED, class: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' };
}

function updateElementText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setElementDisplay(id, display) {
    const el = document.getElementById(id);
    if (el) {
        if (display === 'none') el.classList.add('hidden');
        else {
            el.classList.remove('hidden');
            if (display === 'flex') el.classList.add('flex');
        }
    }
}

async function fetchData() {
    const targetDateStr = getTargetDateStr();
    const dateObj = new Date(targetDateStr);
    const dayOfWeek = ['日', '月', '火', '水', '木', '金', '土'][dateObj.getDay()];
    
    updateElementText('current-date-display', `${targetDateStr} (${dayOfWeek})`);
    setElementDisplay('loading-overlay', 'flex');
    
    const current = new Date(targetDateStr);
    const prev = new Date(current); prev.setDate(prev.getDate() - 1);
    const next = new Date(current); next.setDate(next.getDate() + 1);
    
    const prevBtn = document.getElementById('prev-day');
    if (prevBtn) prevBtn.onclick = () => window.location.search = "date=" + prev.toLocaleDateString('sv-SE');
    
    const nextBtn = document.getElementById('next-day');
    if (nextBtn) nextBtn.onclick = () => window.location.search = "date=" + next.toLocaleDateString('sv-SE');
    
    const todayBtn = document.getElementById('today-btn');
    if (todayBtn) {
        todayBtn.onclick = () => window.location.search = '';
        todayBtn.disabled = (targetDateStr === new Date().toLocaleDateString('sv-SE'));
    }

    try {
        const [scheduleRes, statusRes, masterRes] = await Promise.all([
            fetch(`${API_BASE}/${targetDateStr}`),
            fetch(`${STATUS_API}`),
            fetch(`${BASE_PATH}/assets/master.json`)
        ]);

        if (masterRes.ok) master = await masterRes.json();
        
        const shopGrid = document.getElementById('shop-grid');
        if (scheduleRes.ok) {
            currentData = await scheduleRes.json();
            
            // Initialize Filter and Sort Modules
            Filter.load();
            Sort.load();
            Filter.initUI(master.categories || [], render);
            Sort.initUI(render);
            
            render();
            renderProvenance(currentData.sources);
        } else if (shopGrid) {
            shopGrid.innerHTML = '<div class="col-span-full text-center text-slate-400 py-12">営業予定が見つかりませんでした</div>';
        }

        if (statusRes.ok) {
            const status = await statusRes.json();
            updateElementText('status-info', '最終更新: ' + new Date(status.last_updated).toLocaleString('ja-JP'));
            updateElementText('header-data-range', '提供範囲: ' + status.data_range.start + ' ～ ' + status.data_range.end);
        }
    } catch (e) {
        const shopGrid = document.getElementById('shop-grid');
        if (shopGrid) shopGrid.innerHTML = '<div class="col-span-full text-center text-red-400 py-12">エラーが発生しました</div>';
        console.error(e);
    } finally {
        setElementDisplay('loading-overlay', 'none');
    }
}

function render() {
    if (!currentData) return;
    const grid = document.getElementById('shop-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    let allShops = [...currentData.cafeterias, ...currentData.kitchen_cars];
    const targetDateStr = getTargetDateStr();

    // Helper to get status label for filter and sort
    const getLabel = (s) => getShopStatus(s.start_time, s.end_time, targetDateStr).label;
    
    // 1. Filter
    allShops = allShops.filter(s => Filter.match(s, getLabel(s), LABE_NOW_OPEN));

    // 2. Sort
    allShops = Sort.sort(allShops, getLabel, LABE_NOW_OPEN);

    if (allShops.length === 0) {
        grid.innerHTML = '<div class="col-span-full text-center text-slate-400 py-12 font-medium bg-white dark:bg-slate-800 rounded-xl border border-dashed border-slate-200 dark:border-slate-700">条件に一致する店舗がありません</div>';
        return;
    }

    allShops.forEach(shop => {
        const status = getShopStatus(shop.start_time, shop.end_time, targetDateStr);
        const category = shop.category || '店舗';
        let html = '';
        if (currentView === 'grid') {
            html = `
            <div id="card-${shop.id}" data-location="${shop.location}" class="group relative flex flex-col bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3 shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-1">
                <div class="flex justify-between items-start mb-2 gap-2">
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 uppercase tracking-wider shrink-0">${category}</span>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-black tracking-tight shrink-0 ${status.class}">${status.label}</span>
                </div>
                <h3 class="font-black text-slate-900 dark:text-white mb-1 leading-tight line-clamp-2" title="${shop.name}">${shop.name}</h3>
                ${shop.headline ? `<p class="text-[10px] text-ksu dark:text-blue-400 font-bold line-clamp-1 mb-2">${shop.headline}</p>` : ''}
                
                <div class="mt-auto pt-2 border-t border-slate-50 dark:border-slate-700/50">
                    <div class="flex items-center justify-between gap-2 text-[10px] sm:text-[11px]">
                        <div class="flex items-center gap-1 text-slate-500 dark:text-slate-400 min-w-0">
                            <i class="bi bi-geo-alt shrink-0"></i>
                            <span class="truncate">${shop.location}</span>
                        </div>
                        <div class="flex items-center gap-1 font-bold text-slate-700 dark:text-slate-300 shrink-0">
                            <i class="bi bi-clock shrink-0 text-ksu dark:text-blue-400"></i>
                            <span>${shop.start_time}～${shop.end_time}</span>
                        </div>
                    </div>
                </div>
                
                ${shop.note ? `<div class="mt-2 p-1.5 bg-slate-50 dark:bg-slate-900/50 rounded text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed border border-slate-100 dark:border-slate-800">${shop.note}</div>` : ''}
                ${shop.url ? `<a href="${shop.url}" target="_blank" class="absolute inset-0 z-10" aria-label="${shop.name}の情報を開く"></a>` : ''}
            </div>`;
        } else {
            html = `
            <div id="card-${shop.id}" data-location="${shop.location}" class="group relative flex flex-col bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm hover:shadow-md transition-all duration-200">
                <div class="flex justify-between items-start mb-2 gap-2">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 uppercase tracking-wider shrink-0">${category}</span>
                        <h3 class="font-black text-slate-900 dark:text-white truncate" title="${shop.name}">${shop.name}</h3>
                    </div>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-black tracking-tight shrink-0 ${status.class}">${status.label}</span>
                </div>
                ${shop.headline ? `<p class="text-[10px] text-ksu dark:text-blue-400 font-bold mb-2 truncate">${shop.headline}</p>` : ''}
                <div class="flex items-center justify-between gap-4 text-[11px] mt-auto">
                    <div class="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 min-w-0">
                        <i class="bi bi-geo-alt shrink-0"></i>
                        <span class="truncate">${shop.location}</span>
                    </div>
                    <div class="flex items-center gap-1.5 font-bold text-slate-700 dark:text-slate-300 shrink-0">
                        <i class="bi bi-clock shrink-0 text-ksu dark:text-blue-400"></i>
                        <span>${shop.start_time}～${shop.end_time}</span>
                    </div>
                </div>
                ${shop.note ? `<div class="mt-2 text-[10px] text-slate-400 dark:text-slate-500 line-clamp-1 italic">${shop.note}</div>` : ''}
                ${shop.url ? `<a href="${shop.url}" target="_blank" class="absolute inset-0 z-10" aria-label="${shop.name}の情報を開く"></a>` : ''}
            </div>`;
        }
        grid.insertAdjacentHTML('beforeend', html);
    });

    const isMap = window.location.pathname.includes('/map/');
    if (isMap && typeof initMapInteractions === 'function') {
        initMapInteractions(allShops);
    }
}

function renderProvenance(sources) {
    const sourceLinks = document.getElementById('source-links');
    if (!sourceLinks) return;

    let html = '';
    
    // 1. General Welfare Info Source
    html += `
        <a href="https://www.kyoto-su.ac.jp/campus/welfare/" class="flex items-center gap-2 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-sm text-slate-600 dark:text-slate-300 transition-colors" target="_blank">
            <i class="bi bi-info-circle text-ksu dark:text-blue-400"></i>
            <span class="flex-1 text-truncate">学食・施設情報（京都産業大学）</span>
            <i class="bi bi-box-arrow-up-right text-[10px]"></i>
        </a>
    `;

    // 2. Kitchen Car Official Source
    html += `
        <a href="https://schedule.mellow.jp/ss_web/markets/KqTl8N" class="flex items-center gap-2 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-sm text-slate-600 dark:text-slate-300 transition-colors" target="_blank">
            <i class="bi bi-truck text-ksu dark:text-blue-400"></i>
            <span class="flex-1 text-truncate">キッチンカー営業情報（Mellow）</span>
            <i class="bi bi-box-arrow-up-right text-[10px]"></i>
        </a>
    `;

    // 3. Cafeteria PDF Sources
    if (sources && sources.length > 0) {
        html += sources.map(s => `
            <a href="${s.url}" class="flex items-center gap-2 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-sm text-slate-600 dark:text-slate-300 transition-colors" target="_blank">
                <i class="bi bi-file-pdf text-red-500"></i>
                <span class="flex-1 text-truncate">学食営業カレンダー（${s.name}）</span>
                <i class="bi bi-box-arrow-up-right text-[10px]"></i>
            </a>
        `).join('');
    }

    sourceLinks.innerHTML = html;
}

// --- Theme Switcher ---
const themeBtn = document.getElementById('btn-theme');
if (themeBtn) {
    const applyTheme = (theme) => {
        if (theme === 'dark') document.documentElement.classList.add('dark');
        else document.documentElement.classList.remove('dark');
        const icon = themeBtn.querySelector('i');
        if (icon) icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        localStorage.setItem('theme', theme);
    };
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(savedTheme);
    themeBtn.onclick = () => applyTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
}

// --- Map Logic ---
const IMAGE_WIDTH = 1019, IMAGE_HEIGHT = 747;
function updateOverlay() {
    if (!master) return;
    const img = document.querySelector('#map-wrapper img');
    if (!img || img.naturalWidth === 0) return;
    const scaleX = img.clientWidth / IMAGE_WIDTH, scaleY = img.clientHeight / IMAGE_HEIGHT;
    Object.entries(master.buildings).forEach(([id, b]) => {
        const div = document.getElementById('area-' + id);
        if (div) {
            div.style.left = (b.area.x1 * scaleX) + 'px';
            div.style.top = (b.area.y1 * scaleY) + 'px';
            div.style.width = ((b.area.x2 - b.area.x1) * scaleX) + 'px';
            div.style.height = ((b.area.y2 - b.area.y1) * scaleY) + 'px';
        }
    });
}

async function initMapInteractions(displayedShops) {
    const overlay = document.getElementById('overlay');
    const shopGrid = document.getElementById('shop-grid');
    if (!overlay || !shopGrid || !master) return;
    overlay.innerHTML = '';
    
    Object.entries(master.buildings).forEach(([id, b]) => {
        const div = document.createElement('div');
        div.className = 'building-area'; 
        div.id = 'area-' + id;
        overlay.appendChild(div);
        
        div.onmouseenter = () => {
            const matchedShops = displayedShops.filter(s => (id === 'pilotis' && s.location === '大学内指定場所') || b.shops.includes(s.id));
            const matchedIds = matchedShops.map(s => 'card-' + s.id);
            shopGrid.querySelectorAll('[id^="card-"]').forEach(card => {
                const isMatch = matchedIds.includes(card.id);
                card.style.opacity = isMatch ? '1' : '0.2';
                if (isMatch) { 
                    card.classList.add('ring-2', 'ring-ksu', 'dark:ring-blue-500'); 
                    shopGrid.prepend(card); 
                }
            });
        };
        div.onmouseleave = () => render();
    });

    shopGrid.querySelectorAll('[id^="card-"]').forEach(card => {
        card.onmouseenter = () => {
            const shopId = card.id.replace('card-', '');
            let bId = Object.keys(master.buildings).find(k => master.buildings[k].shops.includes(shopId));
            if (!bId && card.dataset.location === '大学内指定場所') bId = 'pilotis';
            
            const feedbackOverlay = document.getElementById('map-feedback-overlay');
            const mapImg = document.querySelector('#map-wrapper img');
            if (bId) {
                const area = document.getElementById('area-' + bId);
                if (area) area.classList.add('highlighted');
                if (feedbackOverlay) feedbackOverlay.classList.add('hidden');
                if (mapImg) mapImg.style.opacity = '1';
            } else {
                if (feedbackOverlay) {
                    feedbackOverlay.classList.remove('hidden');
                    feedbackOverlay.classList.add('flex');
                }
                if (mapImg) mapImg.style.opacity = '0.5';
            }
            shopGrid.querySelectorAll('[id^="card-"]').forEach(c => { if (c !== card) c.style.opacity = '0.3'; });
        };
        card.onmouseleave = () => {
            overlay.querySelectorAll('.building-area').forEach(area => area.classList.remove('highlighted'));
            const feedbackOverlay = document.getElementById('map-feedback-overlay');
            const mapImg = document.querySelector('#map-wrapper img');
            if (feedbackOverlay) {
                feedbackOverlay.classList.add('hidden');
                feedbackOverlay.classList.remove('flex');
            }
            if (mapImg) mapImg.style.opacity = '1';
            shopGrid.querySelectorAll('[id^="card-"]').forEach(c => { c.style.opacity = '1'; });
        };
    });
    updateOverlay();
}

window.addEventListener('resize', updateOverlay);
document.querySelector('#map-wrapper img')?.addEventListener('load', updateOverlay);

// --- Initialization ---
const targetDateStr = getTargetDateStr();
document.querySelectorAll('nav a').forEach(a => {
    const url = new URL(a.href, window.location.origin);
    url.searchParams.set('date', targetDateStr);
    a.href = url.toString();
    
    const href = a.getAttribute('href').replace(/\/$/, '');
    const isHome = href === '' || href === `${BASE_PATH}`;
    const isMatch = (isHome && !isMapPage && !isListPage) || 
                    (href.endsWith('/map') && isMapPage) || 
                    (href.endsWith('/list') && isListPage);

    if (isMatch) a.classList.add('bg-slate-100', 'dark:bg-slate-800', 'text-ksu', 'dark:text-blue-400');
});

const dateSelector = document.getElementById('date-selector');
if (dateSelector && typeof flatpickr === 'function') {
    flatpickr(dateSelector, {
        locale: 'ja',
        dateFormat: 'Y-m-d',
        defaultDate: targetDateStr,
        onChange: (selectedDates, dateStr) => { if (dateStr) window.location.search = "date=" + dateStr; }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const isDataPage = ['index.html', 'list.html', 'map.html', '', '/'].some(page => window.location.pathname.endsWith(page));
    if (isDataPage) fetchData();
});
