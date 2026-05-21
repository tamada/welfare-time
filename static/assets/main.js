const API_BASE = '/shikaku/api/schedule';
const STATUS_API = '/shikaku/api/status/index.json';
let currentData = null;
const isListMode = window.location.pathname.endsWith('list.html') || window.location.pathname.endsWith('map.html');
const currentView = isListMode ? 'list' : (localStorage.getItem('ksu-harapeco-view') || 'grid');
let activeFilters = JSON.parse(localStorage.getItem('ksu-harapeco-filters') || '[]');
let currentSort = localStorage.getItem('ksu-harapeco-sort') || 'status';

function getTargetDateStr() {
    const urlParams = new URLSearchParams(window.location.search);
    let dateStr = urlParams.get('date');
    if (!dateStr || dateStr === 'today') {
        dateStr = new Date().toLocaleDateString('sv-SE');
    }
    return dateStr;
}

function getShopStatus(startTime, endTime, targetDateStr) {
    if (!startTime || !endTime || startTime === '00:00') return { label: '休業', class: 'status-closed' };
    const now = new Date();
    const todayStr = now.toLocaleDateString('sv-SE');
    if (targetDateStr < todayStr) return { label: '営業終了', class: 'status-closed' };
    if (targetDateStr > todayStr) return { label: '準備中', class: 'status-closed' };

    const nowTotal = now.getHours() * 60 + now.getMinutes();
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    if (nowTotal < (sh*60+sm)) return { label: '準備中', class: 'status-closed' };
    if (nowTotal >= (sh*60+sm) && nowTotal < (eh*60+em)) return { label: '営業中', class: 'status-open' };
    return { label: '営業終了', class: 'status-closed' };
}

function updateElementText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setElementDisplay(id, display) {
    const el = document.getElementById(id);
    if (el) el.style.display = display;
}

async function fetchData(renderCallback) {
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
        const [scheduleRes, statusRes] = await Promise.all([
            fetch(`${API_BASE}/${targetDateStr}/index.json`),
            fetch(`${STATUS_API}`)
        ]);
        
        const shopGrid = document.getElementById('shop-grid');
        if (scheduleRes.ok) {
            currentData = await scheduleRes.json();
            setupFilters();
            
            const isMap = window.location.pathname.includes('/map/');
            render(undefined, isMap ? initMapInteractions : undefined);
            
            renderProvenance(currentData.sources);
        } else if (shopGrid) {
            shopGrid.innerHTML = '<div class="col-12 text-center text-muted py-5">営業予定が見つかりませんでした</div>';
        }

        if (statusRes.ok) {
            const status = await statusRes.json();
            updateElementText('status-info', '最終更新: ' + new Date(status.last_updated).toLocaleString('ja-JP'));
            updateElementText('header-data-range', '提供範囲: ' + status.data_range.start + ' ～ ' + status.data_range.end);
        }
    } catch (e) {
        const shopGrid = document.getElementById('shop-grid');
        if (shopGrid) shopGrid.innerHTML = '<div class="col-12 text-center text-muted py-5">エラーが発生しました</div>';
    } finally {
        setElementDisplay('loading-overlay', 'none');
    }
}

function setupFilters() {
    const categories = new Set();
    [...currentData.cafeterias, ...currentData.kitchen_cars].forEach(s => categories.add(s.category || '店舗'));
    const body = document.getElementById('filter-options-body');
    body.innerHTML = '';
    const sortedCats = Array.from(categories).sort();
    const isOpenOnly = activeFilters.includes('open-only');
    const divOpen = document.createElement('div');
    divOpen.className = 'form-check mb-3 border-bottom pb-2';
    divOpen.innerHTML = '<input class="form-check-input filter-checkbox" type="checkbox" value="open-only" id="filter-open" ' + (isOpenOnly ? 'checked' : '') + '><label class="form-check-label w-100 fw-bold" for="filter-open">営業中のみ表示</label>';
    body.appendChild(divOpen);
    divOpen.querySelector('input').addEventListener('change', applyFilters);
    sortedCats.forEach(cat => {
        const isChecked = activeFilters.includes(cat);
        const div = document.createElement('div');
        div.className = 'form-check mb-2';
        div.innerHTML = '<input class="form-check-input filter-checkbox" type="checkbox" value="' + cat + '" id="filter-' + cat + '" ' + (isChecked ? 'checked' : '') + '><label class="form-check-label w-100" for="filter-' + cat + '">' + cat + '</label>';
        body.appendChild(div);
        div.querySelector('input').addEventListener('change', applyFilters);
    });
}

function applyFilters() {
    const checkboxes = document.querySelectorAll('.filter-checkbox');
    activeFilters = [];
    checkboxes.forEach(cb => { if (cb.checked) activeFilters.push(cb.value); });
    localStorage.setItem('ksu-harapeco-filters', JSON.stringify(activeFilters));
    
    const isMap = window.location.pathname.includes('/map/');
    render(isMap ? 'col-12' : undefined, isMap ? initMapInteractions : undefined);
}

function renderProvenance(sources) {
    const sourceLinks = document.getElementById('source-links');
    if (sourceLinks && sources && sources.length > 0) {
        sourceLinks.innerHTML = '情報元PDF: ' + sources.map(s => '<a href="' + s.url + '" class="footer-link mx-2" target="_blank"><i class="bi bi-file-pdf"></i> ' + s.name + '</a>').join('');
    }
}

function render(gridClass, callback) {
    if (!currentData) return;
    if (!gridClass) gridClass = window.location.pathname.includes('/map/') ? 'col-12' : 'col-6 col-md-4 col-lg-3';
    
    const grid = document.getElementById('shop-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    let allShops = [...currentData.cafeterias, ...currentData.kitchen_cars];
    const targetDateStr = getTargetDateStr();
    const isOpenOnly = activeFilters.includes('open-only');
    
    allShops = allShops.filter(s => {
        const categoryMatch = activeFilters.length === 0 || activeFilters.includes(s.category || '店舗');
        if (isOpenOnly) {
            const status = getShopStatus(s.start_time, s.end_time, targetDateStr);
            return categoryMatch && status.label === '営業中';
        }
        return categoryMatch;
    });
    allShops.sort((a, b) => {
        if (currentSort === 'status') {
            const aOpen = getShopStatus(a.start_time, a.end_time, targetDateStr).label === '営業中';
            const bOpen = getShopStatus(b.start_time, b.end_time, targetDateStr).label === '営業中';
            if (aOpen !== bOpen) return bOpen - aOpen;
        } else if (currentSort === 'name') return a.name.localeCompare(b.name, 'ja');
        else if (currentSort === 'location') return a.location.localeCompare(b.location, 'ja');
        return 0;
    });

    if (allShops.length === 0) {
        grid.innerHTML = '<div class="col-12 text-center text-muted py-5">条件に一致する店舗がありません</div>';
        return;
    }

    allShops.forEach(shop => {
        const status = getShopStatus(shop.start_time, shop.end_time, targetDateStr);
        const category = shop.category || '店舗';
        const isGrid = currentView === 'grid';
        const itemClass = isGrid ? gridClass : 'list-view-item';
        
        const html = '<div class="' + itemClass + '" id="card-' + shop.id + '" data-location="' + shop.location + '">' +
            (isGrid ? '<div class="card h-100 p-2">' : '<div class="shop-info-main">') +
            '<div class="d-flex justify-content-between align-items-center mb-1">' +
                '<span class="' + (isGrid ? 'shop-category-tag' : 'shop-category-tag mb-0') + '">' + category + '</span>' +
                '<span class="status-badge ' + status.class + '">' + status.label + '</span>' +
            '</div>' +
            '<div class="shop-name text-truncate" title="' + shop.name + '">' + shop.name + '</div>' +
            (shop.headline ? '<div class="headline-text text-truncate mb-1" title="' + shop.headline + '">' + shop.headline + '</div>' : '') +
            '<div class="d-flex gap-2 mb-1">' +
                '<div class="location-text text-truncate flex-grow-1"><i class="bi bi-geo-alt"></i> ' + shop.location + '</div>' +
                '<div class="time-text text-nowrap"><i class="bi bi-clock"></i> ' + shop.start_time + '～' + shop.end_time + '</div>' +
            '</div>' +
            (shop.note ? '<div class="note-box">' + shop.note + '</div>' : '') +
            (isGrid ? '</div>' : '</div>') +
            (!isGrid ? '<div class="shop-status-side"><span class="shop-badge ' + status.class + '">' + status.label + '</span></div>' : '') +
            (shop.url ? '<a href="' + shop.url + '" target="_blank" class="stretched-link"></a>' : '') +
            '</div>';
        grid.insertAdjacentHTML('beforeend', html);
    });

    if (callback) callback(allShops);
}

// --- Map Logic ---
let master = null;
async function initMapInteractions(displayedShops) {
    if (!master) {
        try { const response = await fetch('/shikaku/assets/master.json'); master = await response.json(); } catch(e) { console.error(e); return; }
    }
    const overlay = document.getElementById('overlay');
    const tooltip = document.getElementById('tooltip');
    const shopGrid = document.getElementById('shop-grid');
    if (!overlay || !shopGrid) return;
    overlay.innerHTML = '';
    Object.entries(master.buildings).forEach(([id, b]) => {
        const div = document.createElement('div');
        div.className = 'building-area'; div.id = 'area-' + id;
        overlay.appendChild(div);
        div.onmouseenter = () => {
            console.log(`Hovering building: ${b.name}, ID: ${id}`);
            console.log(`Building area: left=${div.style.left}, top=${div.style.top}, width=${div.style.width}, height=${div.style.height}`);
            
            tooltip.style.display = 'block';
            const matchedShops = displayedShops.filter(s => (id === 'pilotis' && s.location === '大学内指定場所') || b.shops.includes(s.id));
            const matchedIds = matchedShops.map(s => 'card-' + s.id);
            shopGrid.querySelectorAll('.list-view-item, .card').forEach(card => {
                const cardEl = card.closest('[id^="card-"]');
                if(!cardEl) return;
                const isMatch = matchedIds.includes(cardEl.id);
                card.style.opacity = isMatch ? '1' : '0.2';
                if (isMatch) { card.classList.add('border-primary'); shopGrid.prepend(card); }
            });
            const dateStr = getTargetDateStr();
            tooltip.innerHTML = '<strong>' + b.name + '</strong><br>' + (matchedShops.length > 0 ? matchedShops.map(s => '<div class="shop-info">' + s.name + '<br><span class="' + getShopStatus(s.start_time, s.end_time, dateStr).class + '">' + getShopStatus(s.start_time, s.end_time, dateStr).label + '</span></div>').join('') : '<div class="shop-info text-muted">該当する店舗なし</div>');
        };
        div.onmouseleave = () => { tooltip.style.display = 'none'; render(); };
    });
    shopGrid.querySelectorAll('.list-view-item, .card').forEach(card => {
        card.onmouseenter = () => {
            const wrapper = card.closest('[id^="card-"]');
            const shopId = wrapper.id.replace('card-', '');
            let bId = Object.keys(master.buildings).find(k => master.buildings[k].shops.includes(shopId));
            if (!bId && wrapper.dataset.location === '大学内指定場所') bId = 'pilotis';
            if (bId) {
                document.getElementById('area-' + bId)?.classList.add('highlighted');
            } else {
                const feedback = document.getElementById('map-feedback-overlay');
                if (feedback) { feedback.innerText = 'この店舗はマップ外です'; feedback.classList.add('active'); }
                const wrapper = document.getElementById('map-wrapper');
                if (wrapper) wrapper.classList.add('dimmed');
            }
            shopGrid.querySelectorAll('.list-view-item, .card').forEach(c => { if (c !== card) c.style.opacity = '0.3'; });
        };
        card.onmouseleave = () => {
            const feedback = document.getElementById('map-feedback-overlay');
            if (feedback) { feedback.innerText = ''; feedback.classList.remove('active'); }
            const wrapper = document.getElementById('map-wrapper');
            if (wrapper) wrapper.classList.remove('dimmed');
            overlay.querySelectorAll('.building-area').forEach(area => area.classList.remove('highlighted'));
            shopGrid.querySelectorAll('.list-view-item, .card').forEach(c => { if (c !== card) c.style.opacity = '1'; });
        };
    });
    updateOverlay();
}

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
window.addEventListener('resize', updateOverlay);
document.querySelector('#map-wrapper img')?.addEventListener('load', updateOverlay);

document.querySelectorAll('.sort-radio').forEach(radio => {
    if (radio.value === currentSort) radio.checked = true;
    radio.addEventListener('change', (e) => {
        currentSort = e.target.value;
        localStorage.setItem('ksu-harapeco-sort', currentSort);
        render();
    });
});
const resetFilter = document.getElementById('reset-filter');
if (resetFilter) {
    resetFilter.onclick = () => {
        document.querySelectorAll('.filter-checkbox').forEach(cb => cb.checked = true);
        document.getElementById('filter-open').checked = false;
        applyFilters();
    };
}
document.querySelectorAll('nav a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === (window.location.pathname.split('/').pop() || 'index.html')) a.classList.add('active-view');
});
const targetDateStr = getTargetDateStr();
document.querySelectorAll('nav a').forEach(a => {
    const url = new URL(a.href, window.location.origin);
    url.searchParams.set('date', targetDateStr);
    a.href = url.toString();
});
const themeBtn = document.getElementById('btn-theme');
if (themeBtn) {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    const icon = themeBtn.querySelector('i');
    if (icon) icon.className = savedTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    themeBtn.onclick = () => {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        if (icon) icon.className = newTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    };
}
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
    const isDataPage = ['index.html', 'list.html', 'map.html', ''].some(page => window.location.pathname.endsWith(page));
    if (isDataPage) fetchData();
});
