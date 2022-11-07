import React from "react";
import { Dependency } from "../data/dependency";

export abstract class View<C> {
    name: string;

    constructor() {
        this.name = this.constructor.name; // this probably will always return 'View' with typescript
    }

    /**
     * Gets declared dependencies for this view so that
     * parent elements can make required hooks
     * @param {*} config 
     */
    abstract getFormDependencies(config: C): Dependency[];


    component: React.FunctionComponent<{ config: C }>;
}
