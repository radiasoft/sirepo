import React from "react";
import { Dependency } from "../data/dependency";
import { LayoutWrapper } from "./layouts";

export type LayoutType<C, P> = new(layoutWrapper: LayoutWrapper) => View<C, P>

export type LayoutProps<C, P> = { config: C } & P & { [key: string]: any };

export abstract class View<C, P> {
    name: string;

    constructor(public layoutsWrapper: LayoutWrapper) {
        this.name = this.constructor.name; // this probably will always return 'View' with typescript
    }

    abstract getFormDependencies(config: C): Dependency[];

    component: React.FunctionComponent<LayoutProps<C, P>>;
}
