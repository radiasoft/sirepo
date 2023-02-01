//TODO(pjm): use a library?
export function debounce(fn, ms) {
    let timer;
    // this must be a function() for "this" and "arguments" to work below
    return function() {
        clearTimeout(timer);
        timer = setTimeout(_ => {
            timer = null;
            fn.apply(this, arguments);
        }, ms);
    };
}
