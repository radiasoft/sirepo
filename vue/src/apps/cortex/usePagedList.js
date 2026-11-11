import { computed, ref, watch } from 'vue';

export const DEFAULT_PAGE_SIZE = 50;

/**
 * Filter and page a list that is all in the browser.
 *
 * @param {Ref} items - the whole list, which may be sorted in place
 * @param {Function} matches - (item, lower case filter text) => true if shown
 * @param {Object} options
 * @param {Ref} options.filter - the filter text, which is set elsewhere if supplied
 * @param {Ref} options.page - the page, which is set elsewhere if supplied
 * @param {number} options.pageSize - rows per page
 */
export const usePagedList = (
    items,
    matches,
    { filter = ref(''), page = ref(1), pageSize = DEFAULT_PAGE_SIZE } = {},
) => {

    // always a new array so sorting items in place is seen by pageItems
    const visible = computed(() => {
        const f = filter.value.trim().toLowerCase();
        return items.value.filter(i => ! f || matches(i, f));
    });
    const pageCount = computed(() => Math.max(1, Math.ceil(visible.value.length / pageSize)));
    const pageItems = computed(() => {
        const i = (page.value - 1) * pageSize;
        return visible.value.slice(i, i + pageSize);
    });
    const pageRange = computed(() => {
        const n = visible.value.length;
        return n ? `${(page.value - 1) * pageSize + 1}-${Math.min(page.value * pageSize, n)}` : '0';
    });

    watch(filter, () => {
        page.value = 1;
    });
    // a shorter list may leave the page out of range
    watch([pageCount, items], () => {
        if (page.value > pageCount.value) {
            page.value = pageCount.value;
        }
    });

    return { filter, page, pageCount, pageItems, pageRange, visible };
};
