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
        let routePattern = /([?]?):(\w+)(\/)?/i;

        let route = routeTemplate;

        let allParamNames = [];
        let match: RegExpExecArray;
        do {
            match = routePattern.exec(route);
            if(!match) {
                break;
            }
            let o = match[1] === '?'; // optional ?
            let p = match[2]; // matched word
            allParamNames.push(p);
            let s = match[3] || ""; // optional /
            let e = match.index + match[0].length;

            if(!params || !Object.keys(params).includes(p)) {
                if(!o) {
                    throw new Error(`non optional param=${p} was missing for route=${routeTemplate}`)
                }
                route = route.substring(0, match.index) + (e < route.length ? route.substring(e) : "");
            } else {
                route = route.substring(0, match.index) + params[p] + s + (e < route.length ? route.substring(match.index + match[0].length) : "");
            }
        } while(!!match)

        let unusedParams = Object.keys(params || {}).filter(p => !allParamNames.includes(p));
        if(unusedParams.length > 0) {
            throw new Error(`unused param(s)=${unusedParams} defined for route=${routeTemplate}; route params=${allParamNames}`)
        }

        return route;
    }

    private getRoute = (routeType: 'reactRoute' | 'route', routeName: string) => {
        let routes = this.schema[routeType];

        if(!routes) {
            throw new Error(`routes field=${routeType} was not found in schema=${Object.keys(this.schema)}`)
        }

        if(!(Object.keys(routes).includes(routeName))) {
            throw new Error(`route name=${routeName} not found in routes=${routeType}`)
        }
        return routes[routeName]
    }

    localRoutePattern = (routeName: string): string => {
        return this.getRoute('reactRoute', routeName);
    }

    localRoute = (routeName: string, params?: RouteParams): string => {
        return `/${this.appName}${this.replaceRouteParams(this.localRoutePattern(routeName), params)}`;
    }

    globalRoutePattern = (routeName: string): string => {
        return this.getRoute('route', routeName);
    }

    globalRoute = (routeName: string, params?: RouteParams): string => {
        return this.replaceRouteParams(this.globalRoutePattern(routeName), params);
    }
}
