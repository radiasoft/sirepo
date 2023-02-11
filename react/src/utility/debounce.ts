export function debounce(fn: Function, ms: number) {
    let timer: number;
    // this must be a function() for "this" and "arguments" to work below
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(_ => {
            timer = undefined;
            fn(...args);
        }, ms);
    };
}
