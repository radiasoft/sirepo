import React from "react";
import { FunctionComponent, useContext } from "react";
import { ModelsAccessor } from "../../data/accessor";
import { Dependency } from "../../data/dependency";
import { CFormStateWrapper } from "../../data/wrapper";
import { SchemaLayout } from "../../utility/schema";
import { Layout } from "../layout";
import { LAYOUTS } from "../layouts";

export class BeamlineWatchpointReports extends Layout<{}, {}> {
    getFormDependencies(): Dependency[] {
        return [];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let b = new Dependency("watchpointReports.reports");
        let formStateWrapper = useContext(CFormStateWrapper);
        let accessor = new ModelsAccessor(formStateWrapper, [b]);
        return (<></>);
    };
}
