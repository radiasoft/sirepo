import React from "react";
import { Dependency } from "../data/dependency";
import { SchemaView } from "../utility/schema";
import { LayoutsWrapper } from "./layouts";

export abstract class View {
    layoutsWrapper: LayoutsWrapper;
    name: string;

    constructor(layoutsWrapper: LayoutsWrapper) {
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
