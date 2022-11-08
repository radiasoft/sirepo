import React from "react";
import { Dependency } from "../data/dependency";
import { LayoutWrapper } from "./layouts";

export type LayoutType<P> = new(layoutWrapper: LayoutWrapper) => View<P>

export type LayoutProps<C> = { config: C };

export abstract class View<C> {
    name: string;

    constructor(public layoutsWrapper: LayoutWrapper) {
        this.name = this.constructor.name; // this probably will always return 'View' with typescript
    }

    /**
     * Gets declared dependencies for this view so that
     * parent elements can make required hooks
     * @param {*} config 
     */
    abstract getFormDependencies(config: C): Dependency[];


    component: React.FunctionComponent<LayoutProps<C>>;
}
