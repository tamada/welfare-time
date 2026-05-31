/**
 * Filter Management Module
 */

const Filter = {
    state: {
        categories: [], // Selected category names
        openOnly: false
    },

    /**
     * Load state from localStorage
     */
    load() {
        const saved = localStorage.getItem('welfare-time-filter-state');
        if (saved) {
            try {
                this.state = JSON.parse(saved);
            } catch (e) {
                console.error('Failed to parse filter state', e);
            }
        }
    },

    /**
     * Save state to localStorage
     */
    save() {
        localStorage.setItem('welfare-time-filter-state', JSON.stringify(this.state));
    },

    /**
     * Initialize filters UI
     * @param {Array} allCategories - List of all available categories
     * @param {Function} onUpdate - Callback when filters change
     */
    initUI(allCategories, onUpdate) {
        const body = document.getElementById('filter-options-body');
        if (!body) return;
        body.innerHTML = '';

        // If state is uninitialized, check everything by default
        if (this.state.categories.length === 0) {
            this.state.categories = [...allCategories];
        }

        // 1. Open Only Toggle
        const divOpen = document.createElement('div');
        divOpen.className = 'flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors border-b border-slate-100 dark:border-slate-700 mb-2';
        divOpen.innerHTML = `
            <input class="w-4 h-4 text-ksu border-slate-300 rounded focus:ring-ksu dark:border-slate-600 dark:bg-slate-700 filter-checkbox" type="checkbox" id="filter-open" ${this.state.openOnly ? 'checked' : ''}>
            <label class="text-sm font-bold text-slate-700 dark:text-slate-200 cursor-pointer flex-1" for="filter-open">営業中のみ表示</label>`;
        body.appendChild(divOpen);
        
        divOpen.querySelector('input').addEventListener('change', (e) => {
            this.state.openOnly = e.target.checked;
            this.save();
            onUpdate();
        });

        // 2. Category Filters
        allCategories.forEach(cat => {
            const isChecked = this.state.categories.includes(cat);
            const div = document.createElement('div');
            div.className = 'flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors';
            div.innerHTML = `
                <input class="w-4 h-4 text-ksu border-slate-300 rounded focus:ring-ksu dark:border-slate-600 dark:bg-slate-700 filter-checkbox" type="checkbox" value="${cat}" id="filter-${cat}" ${isChecked ? 'checked' : ''}>
                <label class="text-sm text-slate-600 dark:text-slate-300 cursor-pointer flex-1" for="filter-${cat}">${cat}</label>`;
            body.appendChild(div);
            
            div.querySelector('input').addEventListener('change', (e) => {
                if (e.target.checked) {
                    if (!this.state.categories.includes(cat)) this.state.categories.push(cat);
                } else {
                    this.state.categories = this.state.categories.filter(c => c !== cat);
                }
                this.save();
                onUpdate();
            });
        });

        // 3. Reset Button
        const resetBtn = document.getElementById('reset-filter');
        if (resetBtn) {
            resetBtn.onclick = () => {
                this.state.categories = [...allCategories];
                this.state.openOnly = false;
                this.save();
                // Update UI and trigger update
                this.initUI(allCategories, onUpdate);
                onUpdate();
            };
        }
    },

    /**
     * Check if a shop passes the filters
     * @param {Object} shop 
     * @param {string} statusLabel - Current status of the shop
     * @param {string} openLabel - Constant for 'Open' label
     * @returns {boolean}
     */
    match(shop, statusLabel, openLabel) {
        const isCategoryMatch = this.state.categories.includes(shop.category || '店舗');
        const isOpenMatch = !this.state.openOnly || statusLabel === openLabel;
        return isCategoryMatch && isOpenMatch;
    }
};
