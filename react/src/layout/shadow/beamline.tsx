import React, { useContext, useState } from "react";
import { FunctionComponent } from "react";
import { Container, Modal } from "react-bootstrap";
import { useDispatch, useStore } from "react-redux";
import { formActionFunctions } from "../../component/reusable/form";
import { ViewPanelActionButtons } from "../../component/reusable/panel";
import { ArrayAliases, HandleFactoryWithArrayAliases } from "../../data/alias";
import { CSchema } from "../../data/appwrapper";
import { newModelFromSchema, StoreTypes } from "../../data/data";
import { Dependency } from "../../data/dependency";
import { formStateFromModelState, FormStateHandleFactory } from "../../data/form";
import { CHandleFactory } from "../../data/handle";
import { ArrayFieldState } from "../../store/common";
import { FormFieldState, FormModelState } from "../../store/formState";
import { CRouteHelper } from "../../utility/route";
import { SchemaLayout } from "../../utility/schema";
import { Layout, LayoutProps } from "../layout";
import { createLayouts } from "../layouts";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Icon from "@fortawesome/free-solid-svg-icons";
import "./beamline.scss";
import { useCoupledState } from "../../hook/coupling";

export type ShadowBeamlineElement = {
    items: SchemaLayout[],
    name: string,
    model: string,
    icon: string
}

export type ShadowBeamlineConfig = {
    beamlineDependency: string,
    elements: ShadowBeamlineElement[]
}

export function ShadowBeamlineThumbnail(props: { name: string, iconSrc: string, onClick?: () => void }) {
    return (
        <div onClick={props.onClick} style={{ width: '100px', border: "1px solid #ccc", borderRadius: "4px", backgroundColor: "#fff", margin: "2px", minWidth: "80px" }}>
            <div style={{height: "100px", width: "100%", display: "flex", flexFlow: "column nowrap", justifyContent: "center"}}>
                <img style={{ minWidth: "80px" }} src={props.iconSrc}/>
            </div>
            <p className="text-center">{props.name}</p>
        </div>
    )
}

export function ShadowBeamlineItem(props: { index: number, baseElement: ShadowBeamlineElement & { layouts: Layout[] }, header: string, aliases: ArrayAliases, onClick?: () => void, onDeleteClick?: () => void, modalShown: boolean, onHideModal?: () => void }) {
    let { index, baseElement, aliases, onClick, onDeleteClick, modalShown, onHideModal, header } = props;
    
    let routeHelper = useContext(CRouteHelper);
    let store = useStore();
    let schema = useContext(CSchema);
    let handleFactory = useContext(CHandleFactory);
    let createHandleFactory = () => new FormStateHandleFactory(schema, new HandleFactoryWithArrayAliases(schema, aliases, handleFactory))
    let [aliasedHandleFactory, _, indexChanged] = useCoupledState(index, createHandleFactory);
    if(indexChanged) {
        return <></>
    }

    let [isHover, updateIsHover] = useState(false);
    let dispatch = useDispatch();

    let actionFunctions = formActionFunctions({
        formHandleFactory: aliasedHandleFactory,
        store,
        dispatch
    });

    let _submit = () => {
        actionFunctions.submit();
        onHideModal();
    }

    let _cancel = () => {
        actionFunctions.cancel();
        onHideModal();
    }

    let isDirty = aliasedHandleFactory.isDirty();
    let isValid = aliasedHandleFactory.isValid(store.getState());
    let actionButtons = <ViewPanelActionButtons canSave={isValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>
    return (
        <CHandleFactory.Provider value={aliasedHandleFactory}>
            <div className="d-flex flex-column flex-nowrap justify-content-center align-items-center" onMouseEnter={() => updateIsHover(true)} onMouseLeave={() => updateIsHover(false)} onClick={onClick}>
                <div className="beamline-item-header">{header}</div>
                <div style={{ position: "relative" }}>
                    <div style={{position: "absolute", zIndex: "10", right: "7px", top: "1px", display: isHover ? undefined : "none"}} onClick={(e) => { e.stopPropagation(); if(onDeleteClick) onDeleteClick() }}>
                        <FontAwesomeIcon icon={Icon.faRemove}/>
                    </div>
                    <div style={{position: "relative"}}>
                        <ShadowBeamlineThumbnail name={baseElement.name} iconSrc={routeHelper.globalRoute("svg", { fileName: baseElement.icon })}/>
                    </div>
                </div>
                
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
        </CHandleFactory.Provider>  
    )
}

export class ShadowBeamlineLayout extends Layout<ShadowBeamlineConfig, {}> {
    private elements: (ShadowBeamlineElement & {layouts: Layout[]})[];

    constructor(config: ShadowBeamlineConfig) {
        super(config);
        this.elements = config.elements.map(e => createLayouts(e, "items"));
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        let routeHelper = useContext(CRouteHelper);
        let store = useStore();
        let schema = useContext(CSchema);
        let dispatch = useDispatch();
        let formHandleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        formHandleFactory.useUpdates(ShadowBeamlineLayout);

        let beamlineDependency: Dependency = new Dependency(this.config.beamlineDependency);

        let [shownModal, updateShownModal] = useState<string>(undefined);

        let handle = formHandleFactory.createHandle<FormModelState, FormFieldState<ArrayFieldState<FormModelState>>>(beamlineDependency, StoreTypes.FormState).hook(); // TODO: form or model?

        let addBeamlineElement = (element: ShadowBeamlineElement) => {
            let ms = schema.models[element.model];
            let nextId = handle.value.value.reduce((prev, cur) => Math.max(prev, parseInt(cur.item.id.value) + 1), 1);
            let nextPos = handle.value.value.reduce((prev, cur) => Math.max(prev, parseFloat(cur.item.position.value) + 5), 0);
            let mv = newModelFromSchema(ms, {
                id: `${nextId}`,
                position: `${nextPos}`,
                type: element.model
            })
            
            let bv = [...handle.value.value];
            bv.push({
                item: formStateFromModelState(mv),
                model: element.model
            });
            handle.write({
                ...handle.value,
                touched: true,
                value: bv
            }, store.getState(), dispatch);
        }

        let removeBeamlineElement = (index: number) => {
            let bv = [...handle.value.value];
            bv.splice(index, 1);
            handle.write({
                ...handle.value,
                touched: true,
                value: bv
            }, store.getState(), dispatch);
        }

        let elementThumbnails = this.elements.map((e, i) => {
            return (
                <ShadowBeamlineThumbnail onClick={() => addBeamlineElement(e)} key={i} name={e.name} iconSrc={routeHelper.globalRoute("svg", { fileName: e.icon })}/>
            )
        })

        let findBaseElementByModel = (model: string) => {
            let r = this.elements.filter(e => e.model === model);
            if(r.length > 1) {
                throw new Error(`multiple beamline base elements found with model=${model}`);
            }
            return r[0];
        }

        let beamlineComponents = handle.value.value.map((e, i) => {
            let model = e.model;
            let ele: FormModelState = e.item;
            let id = ele.id.value;
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
            
            return (
                <ShadowBeamlineItem key={id} index={i} header={`${ele.position.value} m`} baseElement={baseElement} aliases={aliases} onClick={() => updateShownModal(id)} onDeleteClick={() => removeBeamlineElement(i)} modalShown={shownModal === id} onHideModal={() => shownModal === id && updateShownModal(undefined)}/>
            )
        })

        let { submit: _submit, cancel: _cancel } = formActionFunctions({
            formHandleFactory,
            store,
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
                    <div className="beamline-outer">
                        <div className="beamline">
                            {beamlineComponents}
                        </div>
                    </div>
                    <div>
                        {isDirty && actionButtons}
                    </div>
                </div>
            </div>
        )
    }
}

