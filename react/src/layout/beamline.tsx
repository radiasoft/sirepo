import React, { useContext, useState } from "react";
import { FunctionComponent } from "react";
import { Container, Modal } from "react-bootstrap";
import { useDispatch, useStore } from "react-redux";
import { formActionFunctions } from "../component/reusable/form";
import { ViewPanelActionButtons } from "../component/reusable/panel";
import { ArrayAliases, HandleFactoryWithArrayAliases } from "../data/alias";
import { CAppWrapper, CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { newModelFromSchema, StoreTypes } from "../data/data";
import { Dependency } from "../data/dependency";
import { formStateFromModelState, FormStateHandleFactory } from "../data/form";
import { CHandleFactory } from "../data/handle";
import { ArrayFieldState } from "../store/common";
import { FormFieldState, FormModelState } from "../store/formState";
import { CRouteHelper } from "../utility/route";
import { Schema, SchemaLayout } from "../utility/schema";
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

export function BeamlineThumbnail(props: { name: string, iconSrc: string, onClick?: () => void }) {
    return (
        <div onClick={props.onClick} style={{ width: '100px', border: "1px solid #ccc", borderRadius: "4px", backgroundColor: "#fff", margin: "2px", minWidth: "80px" }}>
            <div style={{height: "100px", width: "100%", display: "flex", flexFlow: "column nowrap", justifyContent: "center"}}>
                <img style={{ minWidth: "80px" }} src={props.iconSrc}/>
            </div>
            <p className="text-center">{props.name}</p>
        </div>
    )
}

export function BeamlineItem(props: { baseElement: BeamlineElement & { layouts: Layout[] }, onClick?: () => void, modalShown: boolean, onHideModal?: () => void }) {
    let { baseElement, onClick, modalShown, onHideModal } = props;
    
    let routeHelper = useContext(CRouteHelper);
    let store = useStore();
    let simulationInfoPromise = useContext(CSimulationInfoPromise);
    let formHandleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
    let dispatch = useDispatch();
    let appWrapper = useContext(CAppWrapper);

    let { submit: _submit, cancel: _cancel } = formActionFunctions({
        formHandleFactory,
        store,
        simulationInfoPromise,
        appWrapper,
        dispatch
    });

    let isDirty = formHandleFactory.isDirty();
    let isValid = formHandleFactory.isValid(store.getState());
    let actionButtons = <ViewPanelActionButtons canSave={isValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>
    return (
        <>
            <div onClick={onClick}>
                <BeamlineThumbnail name={baseElement.name} iconSrc={routeHelper.globalRoute("svg", { fileName: baseElement.icon })}/>
            </div>
            <Modal show={modalShown} onHide={() => {
                //_cancel();
                onHideModal();
            }}>
                <Modal.Header>
                    {baseElement.name}
                </Modal.Header>
                <Modal.Body as={Container}>
                    {
                        baseElement.layouts.map((l, i) => {
                            let Comp = l.component;
                            return <Comp key={i}/>
                        })
                    }
                    {isDirty && actionButtons}
                </Modal.Body>
            </Modal>
        </>     
    )
}

export class BeamlineLayout extends Layout<BeamlineConfig, {}> {
    private elements: (BeamlineElement & {layouts: Layout[]})[];

    constructor(config: BeamlineConfig) {
        super(config);
        this.elements = config.elements.map(e => createLayouts(e, "items"));
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        console.log("RENDER BEAMLINE");
        let routeHelper = useContext(CRouteHelper);
        let store = useStore();
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let schema = useContext(CSchema);
        let dispatch = useDispatch();
        let formHandleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        let appWrapper = useContext(CAppWrapper);

        let beamlineDependency: Dependency = new Dependency(this.config.beamlineDependency);

        let [shownModal, updateShownModal] = useState<number>(undefined);

        let handle = formHandleFactory.createHandle<FormModelState, FormFieldState<ArrayFieldState<FormModelState>>>(beamlineDependency, StoreTypes.FormState).hook(); // TODO: form or model?

        let addBeamlineElement = (element: BeamlineElement) => {
            console.log("AAA");
            let ms = schema.models[element.model];
            // TODO: use generic methods
            let l = handle.value.value.length;
            let prev: FormModelState | undefined = l > 0 ? handle.value.value[l - 1].item : undefined
            let nextPosition: string = prev ? `${parseFloat(prev.position.value) + 5}` : "0";
            let nextId: string = prev ? `${parseInt(prev.id.value) + 1}` : "1";
            let mv = newModelFromSchema(ms, {
                id: nextId,
                position: nextPosition,
                type: element.model
            })
            
            console.log("new beamline element mv", mv);
            let bv = [...handle.value.value];
            bv.push({
                item: formStateFromModelState(mv),
                model: element.model
            });
            handle.write({
                ...handle.value,
                touched: true,
                value: bv
            }, store.getState()[StoreTypes.FormState.name], dispatch);
            console.log("ADD ELEMENT");
        }

        let elementThumbnails = this.elements.map((e, i) => {
            return (
                <BeamlineThumbnail onClick={() => addBeamlineElement(e)} key={i} name={e.name} iconSrc={routeHelper.globalRoute("svg", { fileName: e.icon })}/>
            )
        })

        let findBaseElementByModel = (model: string) => {
            let r = this.elements.filter(e => e.model === model);
            if(r.length > 1) {
                throw new Error(`multiple beamline base elements found with model=${model}`);
            }
            return r[0];
        }

        console.log("MAPPING BEAMLINE ELEMENTS");

        let beamlineComponents = handle.value.value.map((e, i) => {
            let model = e.model;
            let ele: FormModelState = e.item;
            let id = ele.id.value;
            console.log("id", id);
            let baseElement = findBaseElementByModel(model);
            let aliases: ArrayAliases = [
                {
                    realDataLocation: {
                        modelName: beamlineDependency.modelName,
                        fieldName: beamlineDependency.fieldName,
                        index: i
                    },
                    realSchemaName: model,
                    fake: model
                }
            ];

            let aliasedHandleFactory = new HandleFactoryWithArrayAliases(schema, aliases, formHandleFactory);
            return (
                <CHandleFactory.Provider value={aliasedHandleFactory}>
                    <BeamlineItem baseElement={baseElement} onClick={() => updateShownModal(i)} modalShown={shownModal === i} onHideModal={() => shownModal === i && updateShownModal(undefined)}/>
                </CHandleFactory.Provider>
            )
        })

        let { submit: _submit, cancel: _cancel } = formActionFunctions({
            formHandleFactory,
            store,
            simulationInfoPromise,
            appWrapper,
            dispatch
        });

        let isDirty = formHandleFactory.isDirty();
        let isValid = formHandleFactory.isValid(store.getState());
        let actionButtons = <ViewPanelActionButtons canSave={isValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>

        return (
            <div>
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
                    <div>
                        {isDirty && actionButtons}
                    </div>
                </div>
            </div>
        )
    }
}

