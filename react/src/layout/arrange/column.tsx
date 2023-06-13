import React, { FunctionComponent } from "react";
import { Col } from "react-bootstrap";
import { Dependency } from "../../data/dependency";
import { LAYOUTS } from "../layouts";
import { Layout } from "../layout";
import { SchemaLayout } from "../../utility/schema";

export type ColumnConfig = {
    item: SchemaLayout,
}

export class ColumnLayout extends Layout<ColumnConfig, {}> {
    child: Layout;

    constructor(config: ColumnConfig) {
        super(config);
        this.child = LAYOUTS.getLayoutForSchema(config.item);
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let LayoutComponent = this.child.component;
        return (
            //TODO(pjm): config to handle classes
            <Col sm={12} className="px-3 py-2">
                <LayoutComponent />
            </Col>
        )
    };
}
