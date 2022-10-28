import { joinPath } from "../utility/path";

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
