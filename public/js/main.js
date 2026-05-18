const API_BASE = 'api/schedule';
const STATUS_API = 'api/status/index.json';
let currentData = null;
let currentView = localStorage.getItem('ksu-harapeco-view') || 'grid';
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
    if (targetDateStr < todayStr) return { label: '終了', class: 'status-closed' };
    if (targetDateStr > todayStr) return { label: '準備中', class: 'status-closed' };

    const nowTotal = now.getHours() * 60 + now.getMinutes();
    const [sh, sm] = startTime.split(':').map(Number);
    const [eh, em] = endTime.split(':').map(Number);
    if (nowTotal < (sh*60+sm)) return { label: '準備中', class: 'status-closed' };
    if (nowTotal >= (sh*60+sm) && nowTotal < (eh*60+em)) return { label: '営業中', class: 'status-open' };
    return { label: '終了', class: 'status-closed' };
}

async function fetchData() {
    const targetDateStr = getTargetDateStr();
    document.getElementById('current-date-display').textContent = targetDateStr;
    document.getElementById('datepicker-input').value = targetDateStr;
    document.getElementById('loading-overlay').style.display = 'flex';
    
    const current = new Date(targetDateStr);
    const prev = new Date(current); prev.setDate(prev.getDate() - 1);
    const next = new Date(current); next.setDate(next.getDate() + 1);
    
    document.getElementById('prev-day').onclick = () => window.location.search = `date=${prev.toLocaleDateString('sv-SE')}`;
    document.getElementById('next-day').onclick = () => window.location.search = `date=${next.toLocaleDateString('sv-SE')}`;
    document.getElementById('today-btn').onclick = () => window.location.search = '';
    
    const todayBtn = document.getElementById('today-btn');
    todayBtn.disabled = (targetDateStr === new Date().toLocaleDateString('sv-SE'));

    try {
        const [scheduleRes, statusRes] = await Promise.all([
            fetch(`${API_BASE}/${targetDateStr}/index.json?_=${Date.now()}`),
            fetch(`${STATUS_API}?_=${Date.now()}`)
        ]);
        
        if (scheduleRes.ok) {
            currentData = await scheduleRes.json();
            setupFilters();
            render();
            renderProvenance(currentData.sources);
        } else {
            document.getElementById('shop-grid').innerHTML = '<div class="col-12 text-center text-muted py-5">営業予定が見つかりませんでした</div>';
        }

        if (statusRes.ok) {
            const status = await statusRes.json();
            document.getElementById('status-info').textContent = `最終更新: ${new Date(status.last_updated).toLocaleString('ja-JP')}`;
            document.getElementById('header-data-range').textContent = `提供範囲: ${status.data_range.start} ～ ${status.data_range.end}`;
        }
    } catch (e) {
        document.getElementById('shop-grid').innerHTML = '<div class="col-12 text-center text-muted py-5">エラーが発生しました</div>';
    } finally {
        document.getElementById('loading-overlay').style.display = 'none';
    }
}

function setupFilters() {
    const categories = new Set();
    [...currentData.cafeterias, ...currentData.kitchen_cars].forEach(s => categories.add(s.category || '店舗'));
    const body = document.getElementById('filter-options-body');
    body.innerHTML = '';
    const sortedCats = Array.from(categories).sort();
    if (activeFilters.length === 0) activeFilters = [...sortedCats];
    else activeFilters = activeFilters.filter(f => sortedCats.includes(f));
    if (activeFilters.length === 0) activeFilters = [...sortedCats];

    sortedCats.forEach(cat => {
        const isChecked = activeFilters.includes(cat);
        const div = document.createElement('div');
        div.className = 'form-check mb-2';
        div.innerHTML = `<input class="form-check-input filter-checkbox" type="checkbox" value="${cat}" id="filter-${cat}" ${isChecked ? 'checked' : ''}><label class="form-check-label w-100" for="filter-${cat}">${cat}</label>`;
        body.appendChild(div);
        div.querySelector('input').addEventListener('change', applyFilters);
    });
}

function applyFilters() {
    const checkboxes = document.querySelectorAll('.filter-checkbox');
    activeFilters = [];
    checkboxes.forEach(cb => { if (cb.checked) activeFilters.push(cb.value); });
    localStorage.setItem('ksu-harapeco-filters', JSON.stringify(activeFilters));
    render();
}

document.getElementById('reset-filter').onclick = () => {
    document.querySelectorAll('.filter-checkbox').forEach(cb => cb.checked = true);
    applyFilters();
};

document.querySelectorAll('.sort-radio').forEach(radio => {
    if (radio.value === currentSort) radio.checked = true;
    radio.addEventListener('change', (e) => {
        currentSort = e.target.value;
        localStorage.setItem('ksu-harapeco-sort', currentSort);
        render();
    });
});

document.getElementById('btn-reload').onclick = () => fetchData();

function renderProvenance(sources) {
    const sourceLinks = document.getElementById('source-links');
    if (sources && sources.length > 0) {
        sourceLinks.innerHTML = '情報元PDF: ' + sources.map(s => `<a href="${s.url}" class="footer-link mx-2" target="_blank"><i class="bi bi-file-pdf"></i> ${s.name}</a>`).join('');
    } else {
        sourceLinks.innerHTML = '';
    }
}

function render() {
    if (!currentData) return;
    const grid = document.getElementById('shop-grid');
    grid.innerHTML = '';
    let allShops = [...currentData.cafeterias, ...currentData.kitchen_cars];
    allShops = allShops.filter(s => activeFilters.includes(s.category || '店舗'));
    const targetDateStr = getTargetDateStr();
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
        let html = '';
        const category = shop.category || '店舗';
        if (currentView === 'grid') {
            html = `
            <div class="col-6 col-md-4 col-lg-3">
                <div class="card h-100 p-2">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="shop-category-tag">${category}</span>
                        <span class="status-badge ${status.class}">${status.label}</span>
                    </div>
                    <div class="shop-name text-truncate" title="${shop.name}">${shop.name}</div>
                    <div class="location-text text-truncate mb-1"><i class="bi bi-geo-alt"></i> ${shop.location}</div>
                    <div class="time-text"><i class="bi bi-clock"></i> ${shop.start_time}～${shop.end_time}</div>
                    ${shop.note ? `<div class="note-box">${shop.note}</div>' : ''}
                    ${shop.url ? `<a href="${shop.url}" target="_blank" class="stretched-link"></a>` : ''}
                </div>
            </div>`;
        } else {
            html = `
            <div class="col-12">
                <div class="list-view-item">
                    <div class="shop-info-main">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="shop-category-tag mb-0">${category}</span>
                            <div class="shop-name">${shop.name}</div>
                        </div>
                        <div class="d-flex gap-3">
                            <div class="location-text text-truncate"><i class="bi bi-geo-alt"></i> ${shop.location}</div>
                            <div class="time-text"><i class="bi bi-clock"></i> ${shop.start_time}～${shop.end_time}</div>
                        </div>
                        ${shop.note ? `<div class="note-box mt-1 py-1">${shop.note}</div>` : ''}
                    </div>
                    <div class="shop-status-side">
                        <span class="status-badge ${status.class}">${status.label}</span>
                    </div>
                    ${shop.url ? `<a href="${shop.url}" target="_blank" class="stretched-link"></a>` : ''}
                </div>
            </div>`;
        }
        grid.insertAdjacentHTML('beforeend', html);
    });
}

function switchView(view) {
    currentView = view;
    localStorage.setItem('ksu-harapeco-view', view);
    document.getElementById('btn-grid-view').classList.toggle('active-view', view === 'grid');
    document.getElementById('btn-list-view').classList.toggle('active-view', view === 'list');
    render();
}

document.getElementById('btn-grid-view').onclick = () => switchView('grid');
document.getElementById('btn-list-view').onclick = () => switchView('list');
document.getElementById('btn-grid-view').classList.toggle('active-view', currentView === 'grid');
document.getElementById('btn-list-view').classList.toggle('active-view', currentView === 'list');

document.getElementById('date-selector').onclick = () => document.getElementById('datepicker-input').showPicker();
document.getElementById('datepicker-input').onchange = (e) => { if (e.target.value) window.location.search = `date=${e.target.value}`; };

// Theme logic
const themeBtn = document.getElementById('btn-theme');
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-bs-theme', savedTheme);
updateThemeIcon(savedTheme);

themeBtn.onclick = () => {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
};

function updateThemeIcon(theme) {
    themeBtn.querySelector('i').className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
}

fetchData();
