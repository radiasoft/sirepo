import React from "react";
import { Dependency } from "../data/dependency";

export type LayoutType<C = unknown, P = unknown, V extends Layout<C, P> = any> = new(config: C) => V

export type LayoutProps<P> = P & { [key: string]: any };

export abstract class Layout<C = unknown, P = unknown> {
    name: string;

    constructor(protected config: C) {
        this.name = this.constructor.name; // this probably will always return 'Layout' with typescript
    }

    abstract getFormDependencies(): Dependency[];

    component: React.FunctionComponent<LayoutProps<P>>;
}
