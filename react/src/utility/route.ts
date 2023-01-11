import React from "react";
import { Path } from "react-router-dom";
import { joinPath } from "./path";
import { Schema } from "./schema";

export const CRelativeRouterHelper = React.createContext<RelativeRouteHelper>(undefined);
export const CRouteHelper = React.createContext<RouteHelper>(undefined);
/**
 * This exists to provide a point of reference to use
 * while linking to new routes. Used to create
 * proper relative links while not needing to be
 * aware of parent routing details.
 */
 export class RelativeRouteHelper {
    pathPrefix: Path;

    constructor(pathPrefix: Path) {
        this.pathPrefix = pathPrefix;
    }

    getCurrentPath() { 
        return joinPath(this.pathPrefix.pathname, this.pathPrefix.search);
    }

    getRelativePath(route: string) {
        let path = joinPath(this.pathPrefix.pathname, route, this.pathPrefix.search);
        return path;
    }
}

export type RouteParams = {
    [key: string]: string
}

export class RouteHelper {
    constructor(private appName: string, private schema: Schema) {

    }

    private replaceRouteParams = (routeTemplate: string, params?: RouteParams): string => {
        let routePattern = /([?]?):(\w+)(\/)?/g;

        let allParamNames = [];
        
        let match: RegExpExecArray;
        do {
            match = routePattern.exec(routeTemplate);
            let o = match.groups[0] === '?'; // optional ?
            let p = match.groups[1]; // matched word
            allParamNames.push(p);
            let s = match.groups[2] || ""; // optional /
            let e = match.index + match.length;

            if(!params || !Object.keys(params).includes(p)) {
                if(!o) {
                    throw new Error(`non optional param=${p} was missing for route=${routeTemplate}`)
                }
                routeTemplate = routeTemplate.substring(0, match.index) + (e < routeTemplate.length ? routeTemplate.substring(e) : "");
            } else {
                routeTemplate = routeTemplate.substring(0, match.index) + params[p] + s + (e < routeTemplate.length ? routeTemplate.substring(match.index + match.length) : "");
            }
        } while(!!match)

        let unusedParams = Object.keys(params || {}).filter(p => !allParamNames.includes(p));
        if(unusedParams.length > 0) {
            throw new Error(`unused param(s)=${unusedParams} defined for route=${routeTemplate}; route params=${allParamNames}`)
        }

        return `/${this.appName}/${routeTemplate}`;
    }

    private getRoute = (routeType: 'reactRoutes' | 'routes', routeName: string) => {
        let routes = this.schema[routeType];

        if(!(Object.keys(routes).includes(routeName))) {
            throw new Error(`route name=${routeName} not found in routes=${routeType}`)
        }
        return routes[routeName]
    }

    localRoute = (routeName: string, params?: RouteParams): string => {
        return this.replaceRouteParams(this.getRoute('reactRoutes', routeName), params);
    }

    globalRoute = (routeName: string, params?: RouteParams): string => {
        return this.replaceRouteParams(this.getRoute('routes', routeName), params);
    }
}
