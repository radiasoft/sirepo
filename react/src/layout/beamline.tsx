import React from "react";
import { FunctionComponent } from "react";
import { Dependency } from "../data/dependency";
import { SchemaLayout } from "../utility/schema";
import { Layout, LayoutProps } from "./layout";
import { createLayouts } from "./layouts";

export type BeamlineElement = {
    items: SchemaLayout[],
    name: string,
    icon: string
}

export type BeamlineConfig = {
    elements: BeamlineElement[]
}

export class BeamlineLayout extends Layout<BeamlineConfig, {}> {
    private elements: (BeamlineElement & {layouts: Layout[]})[];

    constructor(config: BeamlineConfig) {
        super(config);
        this.elements = config.elements.map(e => createLayouts(e, "items"));
    }

    getFormDependencies(): Dependency[] {
        return [];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        let elementThumbnails = this.elements.map(e => {
            return (
                <div style={{height: '100%'}}>
                    <img>
                    </img>

                </div>
            )
        })
        return (
            <></>
        )
    }
}
