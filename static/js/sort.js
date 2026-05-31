/**
 * Sort Management Module
 */

const Sort = {
    current: 'status',

    /**
     * Load sort preference from localStorage
     */
    load() {
        this.current = localStorage.getItem('ksu-harapeco-sort') || 'status';
    },

    /**
     * Save sort preference to localStorage
     */
    save() {
        localStorage.setItem('ksu-harapeco-sort', this.current);
    },

    /**
     * Initialize sort UI
     * @param {Function} onUpdate - Callback when sort changes
     */
    initUI(onUpdate) {
        document.querySelectorAll('.sort-radio').forEach(radio => {
            if (radio.value === this.current) radio.checked = true;
            radio.addEventListener('change', (e) => {
                this.current = e.target.value;
                this.save();
                onUpdate();
            });
        });
    },

    /**
     * Sort an array of shops
     * @param {Array} shops 
     * @param {Function} getStatusLabel - Function to get status label for a shop
     * @param {string} openLabel - Constant for 'Open' label
     * @returns {Array} Sorted shops
     */
    sort(shops, getStatusLabel, openLabel) {
        return [...shops].sort((a, b) => {
            if (this.current === 'status') {
                const aOpen = getStatusLabel(a) === openLabel;
                const bOpen = getStatusLabel(b) === openLabel;
                if (aOpen !== bOpen) return aOpen ? -1 : 1;
                return a.name.localeCompare(b.name, 'ja');
            } else if (this.current === 'name') {
                return a.name.localeCompare(b.name, 'ja');
            } else if (this.current === 'location') {
                return a.location.localeCompare(b.location, 'ja') || a.name.localeCompare(b.name, 'ja');
            }
            return 0;
        });
    }
};
