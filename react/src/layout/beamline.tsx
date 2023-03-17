import React, { useContext } from "react";
import { FunctionComponent } from "react";
import { Modal } from "react-bootstrap";
import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";
import { CFormStateWrapper } from "../data/wrapper";
import { FormModelState } from "../store/formState";
import { CRouteHelper } from "../utility/route";
import { SchemaLayout } from "../utility/schema";
import { FormControllerElement } from "./form";
import { ArrayField } from "./input/array";
import { Layout, LayoutProps } from "./layout";
import { createLayouts } from "./layouts";

export type BeamlineElement = {
    items: SchemaLayout[],
    name: string,
    model: string,
    icon: string
}

export type BeamlineConfig = {
    beamlineDependency: string,
    elements: BeamlineElement[]
}

export function BeamlineItem(props: { name: string, iconSrc: string }) {
    return (
        <div style={{ width: '100px', border: "1px solid #ccc", borderRadius: "4px", backgroundColor: "#fff", margin: "2px", minWidth: "80px" }}>
            <div style={{height: "100px", width: "100%", display: "flex", flexFlow: "column nowrap", justifyContent: "center"}}>
                <img style={{ minWidth: "80px" }} src={props.iconSrc}/>
            </div>
            <p className="text-center">{props.name}</p>
        </div>
    )
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

        let beamlineValue: ArrayField<FormModelState> = accessor.getFieldValue(beamlineDependency).value as ArrayField<FormModelState>;

        let elementThumbnails = this.elements.map((e, i) => {
            return (
                <BeamlineItem key={i} name={e.name} iconSrc={routeHelper.globalRoute("svg", { fileName: e.icon })}/>
            )
        })

        console.log("elements", this.elements);

        let findBaseElementByModel = (model: string) => {
            let r = this.elements.filter(e => e.model === model);
            if(r.length > 1) {
                throw new Error(`multiple beamline base elements found with model=${model}`);
            }
            return r[0];
        }

        console.log("beamlineValue", beamlineValue);
        let beamlineComponents = beamlineValue.map((e, i) => {
            let model = e.model;
            let ele: FormModelState = e.item;

            let baseElement = findBaseElementByModel(model);
            //let deps = baseElement.layouts.flatMap(l => l.getFormDependencies());
            let deps = [];
            
            /*let modal = (
                <Modal.Dialog>
                    {
                        baseElement.layouts.map(l => {
                            let Comp = l.component;
                            return <Comp/>
                        })
                    }
                </Modal.Dialog>
            )*/
            // TODO: override form controller
            return (
                <FormControllerElement key={i} dependencies={deps}>
                    <BeamlineItem name={baseElement.name} iconSrc={routeHelper.globalRoute("svg", { fileName: baseElement.icon })}/>
                </FormControllerElement>
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
                    <div style={{ display: "flex", flexFlow: "row nowrap", justifyContent: "center" }}>
                        {beamlineComponents}
                    </div>
                </div>
            </>
        )
    }
}
