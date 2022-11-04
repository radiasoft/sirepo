/**
 * @param {string} str 
 */
 export function trimPathSeparators(str, {front=true, end=true}) {
    while(front && str.length > 0 && str.substring(0, 1) === '/') {
        str = str.substring(1);
    }
    while(end && str.length > 0 && str.substring(str.length - 1) === '/') {
        str = str.substring(0, str.length - 1);
    }
    return str;
}

/**
 * @param  {...string} paths 
 */
export function joinPath(...paths) {
    let path = '';

    paths = paths || [];
    for(let i = 0; i < paths.length; i++) {
        let p = paths[i];
        if(p) {
            let tp = trimPathSeparators(p, { front: i !== 0 });
            if(tp.trim().length > 0) {
                path += (i > 0 ? '/' : '') + tp;
            }
        }
    }

    return path;
}
