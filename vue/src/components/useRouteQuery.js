import { computed, shallowRef } from 'vue';
import { useRoute, useRouter } from 'vue-router';

// Changes made in one tick are applied in one navigation, so setting two
// values together doesn't lose the first to a stale route.query.
// Don't set a value and navigate in the same tick: the flush would apply
// the query to the old path and likely cancel the navigation.
const pending = shallowRef(null);

const flush = (router) => {
    const p = pending.value;
    pending.value = null;
    const c = router.currentRoute.value;
    router[p.push ? 'push' : 'replace']({ path: c.path, query: p.query, hash: c.hash });
};

const parsers = {
    number: (v) => {
        const rv = Number(v);
        return Number.isInteger(rv) ? rv : undefined;
    },
    string: (v) => v,
};

/**
 * A value kept in the route's query, so refresh, Back and shared links show
 * the same view.
 *
 * The value is omitted from the url when it is the default. A missing,
 * unparsable or invalid value reads as the default.
 *
 * @param {string} name - query parameter
 * @param {string|number} defaultValue - value when not in the query
 * @param {Object} options
 * @param {Function} options.isValid - (value) => false to read the default
 * @param {boolean} options.push - add a history entry, so Back returns to the
 *     previous value (default replaces the current entry)
 * @returns {WritableComputedRef}
 */
export function useRouteQuery(name, defaultValue, { isValid = () => true, push = false } = {}) {
    const route = useRoute();
    const router = useRouter();
    const parse = parsers[typeof defaultValue === 'number' ? 'number' : 'string'];

    return computed({
        get: () => {
            const q = pending.value?.query || route.query;
            const v = q[name] === undefined ? undefined : parse(q[name]);
            return v === undefined || ! isValid(v) ? defaultValue : v;
        },
        set: (value) => {
            if (! pending.value) {
                pending.value = { query: { ...route.query }, push: false };
                queueMicrotask(() => flush(router));
            }
            const q = { ...pending.value.query };
            if (value === defaultValue || value === undefined || value === null || value === '') {
                delete q[name];
            }
            else {
                q[name] = String(value);
            }
            pending.value = { query: q, push: pending.value.push || push };
        },
    });
}
