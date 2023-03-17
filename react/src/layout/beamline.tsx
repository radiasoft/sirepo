import React, { useContext } from "react";
import { FunctionComponent } from "react";
import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";
import { CFormStateWrapper } from "../data/wrapper";
import { FormModelState } from "../store/formState";
import { CRouteHelper } from "../utility/route";
import { SchemaLayout } from "../utility/schema";
import { ArrayField } from "./input/array";
import { Layout, LayoutProps } from "./layout";
import { createLayouts } from "./layouts";

export type BeamlineElement = {
    items: SchemaLayout[],
    name: string,
    icon: string
}

export type BeamlineConfig = {
    beamlineDependency: string,
    elements: BeamlineElement[]
}

export class BeamlineLayout extends Layout<BeamlineConfig, {}> {
    private elements: (BeamlineElement & {layouts: Layout[]})[];

    constructor(config: BeamlineConfig) {
        super(config);
        this.elements = config.elements.map(e => createLayouts(e, "items"));
    }

    getFormDependencies(): Dependency[] {
        return [new Dependency(this.config.beamlineDependency)];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        let routeHelper = useContext(CRouteHelper);
        let formStateWrapper = useContext(CFormStateWrapper);
        let beamlineDependency: Dependency = new Dependency(this.config.beamlineDependency);

        let accessor = new ModelsAccessor(formStateWrapper, [beamlineDependency]);

        let beamlineValue: ArrayField<FormModelState> = accessor.getFieldValue(beamlineDependency) as any as ArrayField<FormModelState>;

        let elementThumbnails = this.elements.map((e, i) => {
            return (
                <div key={i} style={{ width: '100px', border: "1px solid #ccc", borderRadius: "4px", backgroundColor: "#fff", margin: "2px", minWidth: "80px" }}>
                    <div style={{height: "100px", width: "100%", display: "flex", flexFlow: "column nowrap", justifyContent: "center"}}>
                        <img style={{ minWidth: "80px" }} src={routeHelper.globalRoute("svg", { fileName: e.icon })}/>
                    </div>
                    <p className="text-center">{e.name}</p>
                </div>
            )
        })
        return (
            <>
                <div className="col-sm-12" style={{ display: "flex", flexFlow: "row nowrap", justifyContent: "center", backgroundColor: "#d9edf7", borderRadius: "6px", marginBottom: "15px" }}>
                    {elementThumbnails}
                </div>
                <div className="col-sm-12" style={{ display: "flex", flexFlow: "column nowrap", justifyContent: "center", backgroundColor: "#eee", borderRadius: "6px", padding: "10px" }}>
                    <div>
                        <p className="lead text-center">
                            beamline definition area
                            <br/>
                            <small>
                                <em>
                                    click optical elements to define the beamline
                                </em>
                            </small>
                        </p>
                    </div>
                    
                </div>
            </>
        )
    }
}
