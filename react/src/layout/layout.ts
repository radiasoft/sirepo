import React from "react";
import { Dependency } from "../data/dependency";
import { SchemaView } from "../utility/schema";
import { LayoutWrapper } from "./layouts";

export abstract class View {
    layoutsWrapper: LayoutWrapper;
    name: string;

    constructor(layoutsWrapper: LayoutWrapper) {
        this.layoutsWrapper = layoutsWrapper;

        this.name = this.constructor.name; // this probably will always return 'View' with typescript
    }

    /**
     * Gets declared dependencies for this view so that
     * parent elements can make required hooks
     * @param {*} config 
     */
    abstract getFormDependencies(config: SchemaView): Dependency[];
    /**
     * Creates a new component for this view
     * @param {{ config: * }} props 
     */
    component: React.FunctionComponent;
}
