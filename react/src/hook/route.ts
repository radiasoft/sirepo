import React from "react";
import { Path } from "react-router-dom";
import { joinPath } from "../utility/path";

export const CRelativeRouterHelper = React.createContext<RouteHelper>(undefined);
/**
 * This exists to provide a point of reference to use
 * while linking to new routes. Used to create
 * proper relative links while not needing to be
 * aware of parent routing details.
 */
// TODO move to utility or data
 export class RouteHelper {
    pathPrefix: Path;

    constructor(pathPrefix: Path) {
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
