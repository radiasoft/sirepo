/**
 * Helper function to create an object of the same shape as the input by mapping property values to a new value
 * @param {{[name: string]: T}} obj
 * @param {(name: string, value: T) => *} mapFunc
 * @returns {T} An object with the same fields having mapFunc applied
 */
export function mapProperties(obj, mapFunc) {
    return Object.fromEntries(
        Object.entries(obj).map(([propName, propValue]) => {
            return [propName, mapFunc(propName, propValue)]
        })
    )
}

/**
 * @param {string} str 
 */
export function removeSeparators(str, {front=true, end=true}) {
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
            let tp = removeSeparators(p, { front: i !== 0 });
            if(tp.trim().length > 0) {
                path += (i > 0 ? '/' : '') + tp;
            }
        }
    }

    return path;
}

/**
 * This exists to provide a point of reference to use
 * while linking to new routes. Used to create
 * proper relative links while not needing to be
 * aware of parent routing details.
 */
export class RouteHelper {
    constructor(pathPrefix) {
        this.pathPrefix = pathPrefix;
    }

    getCurrentPath() { 
        return joinPath(this.pathPrefix.pathname, this.pathPrefix.search);
    }

    getRelativePath(route) {
        let path = joinPath(this.pathPrefix.pathname, route, this.pathPrefix.search);
        return path;
    }
}
