import React from "react";
import { FunctionComponent } from "react";
import { Dependency } from "../data/dependency";
import { Layout } from "./layout";

export class ColumnBreakLayout extends Layout<{}, {}> {
    getFormDependencies(): Dependency[] {
        return [];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        return (
            <div className="clearfix"></div>
        )
    };
}
