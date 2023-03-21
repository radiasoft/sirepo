import React, { useContext, useState } from "react";
import { FunctionComponent } from "react";
import { Container, Modal } from "react-bootstrap";
import { useStore } from "react-redux";
import { formActionFunctions } from "../component/reusable/form";
import { ViewPanelActionButtons } from "../component/reusable/panel";
import { ModelsAccessor } from "../data/accessor";
import { CSchema, CSimulationInfoPromise } from "../data/appwrapper";
import { Dependency } from "../data/dependency";
import { CFormController, formStateFromModel } from "../data/formController";
import { AbstractModelsWrapper, CFormStateWrapper, CModelsWrapper, ModelAliases, ModelHandle, ModelsWrapper, ModelsWrapperWithAliases } from "../data/wrapper";
import { FormFieldState, FormModelState } from "../store/formState";
import { CRouteHelper } from "../utility/route";
import { Schema, SchemaLayout } from "../utility/schema";
import { FormControllerElement } from "./form";
import { ArrayField, ArrayModelElement } from "./input/array";
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
    let formController = useContext(CFormController);
    let store = useStore();
    let simulationInfoPromise = useContext(CSimulationInfoPromise);
    let modelsWrapper = useContext(CModelsWrapper);
    let schema = useContext(CSchema);

    // TODO: override form controller
    //console.log("ele", ele);
    //console.log("id", id);
    console.log("modalShown", modalShown);

    let { submit: _submit, cancel: _cancel } = formActionFunctions(formController, store, simulationInfoPromise, schema, modelsWrapper as ModelsWrapper);

    let isDirty = formController.isFormStateDirty();
    let isValid = formController.isFormStateValid();
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

    getFormDependencies(): Dependency[] {
        return [new Dependency(this.config.beamlineDependency)];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props: LayoutProps<{}>) => {
        console.log("RENDER");
        let routeHelper = useContext(CRouteHelper);
        let formStateWrapper = useContext(CFormStateWrapper);
        let modelsWrapper = useContext(CModelsWrapper);
        let formController = useContext(CFormController);
        let store = useStore();
        let simulationInfoPromise = useContext(CSimulationInfoPromise);
        let schema = useContext(CSchema);

        let beamlineDependency: Dependency = new Dependency(this.config.beamlineDependency);

        let [shownModal, updateShownModal] = useState<number>(undefined);
        console.log("shownModal", shownModal);

        let accessor = new ModelsAccessor(formStateWrapper, [beamlineDependency]);

        let beamlineValue: ArrayField<FormModelState> = accessor.getFieldValue(beamlineDependency) as any as ArrayField<FormModelState>;

        let addBeamlineElement = (element: BeamlineElement) => {
            let ms = schema.models[element.model];
            // TODO: use generic methods
            let prev: FormModelState | undefined = beamlineValue.length > 0 ? beamlineValue[beamlineValue.length - 1].item : undefined
            let nextPosition: number = prev ? prev.position.value + 5 : 0;
            let nextId: number = prev ? prev.id.value + 1 : 1;
            let mv = formStateFromModel({
                id: nextId,
                position: nextPosition,
                type: element.model
            }, ms, schema);
            let bv = [...beamlineValue];
            bv.push({
                item: mv,
                model: element.model
            });
            let m = formStateWrapper.getModel(beamlineDependency.modelName, store.getState());
            m = formStateWrapper.setFieldInModel(beamlineDependency.fieldName, m, bv as any as FormFieldState<unknown>);
            formStateWrapper.updateModel(beamlineDependency.modelName, m, store.getState());
            console.log("ADD ELEMENT");
        }

        let elementThumbnails = this.elements.map((e, i) => {
            return (
                <BeamlineThumbnail onClick={() => addBeamlineElement(e)} key={i} name={e.name} iconSrc={routeHelper.globalRoute("svg", { fileName: e.icon })}/>
            )
        })

        //console.log("elements", this.elements);

        let findBaseElementByModel = (model: string) => {
            let r = this.elements.filter(e => e.model === model);
            if(r.length > 1) {
                throw new Error(`multiple beamline base elements found with model=${model}`);
            }
            return r[0];
        }

        //console.log("beamlineValue", beamlineValue);
        let beamlineComponents = beamlineValue.map((e, i) => {
            let model = e.model;
            let ele: FormModelState = e.item;
            let id = ele.id.value;
            let baseElement = findBaseElementByModel(model);
            let deps = baseElement.layouts.flatMap(l => l.getFormDependencies());
            let aliases: FormControllerAliases = [
                {
                    real: {
                        modelName: beamlineDependency.modelName,
                        fieldName: beamlineDependency.fieldName,
                        index: i
                    },
                    fake: model,
                    realSchemaName: model
                }
            ];
            return (
                <React.Fragment key={id}>
                    <AliasedFormControllerWrapper aliases={aliases}>
                        <FormControllerElement dependencies={deps}>
                            <BeamlineItem baseElement={baseElement} onClick={() => updateShownModal(i)} modalShown={shownModal === i} onHideModal={() => shownModal === i && updateShownModal(undefined)}/>
                        </FormControllerElement>
                    </AliasedFormControllerWrapper>   
                </React.Fragment>
            )
        })

        let { submit: _submit, cancel: _cancel } = formActionFunctions(formController, store, simulationInfoPromise, schema, modelsWrapper as ModelsWrapper);

        let isDirty = formController.isFormStateDirty();
        let isValid = formController.isFormStateValid();
        let actionButtons = <ViewPanelActionButtons canSave={isValid} onSave={_submit} onCancel={_cancel}></ViewPanelActionButtons>

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
                    <div>
                        {isDirty && actionButtons}
                    </div>
                </div>
            </>
        )
    }
}

export function arrayPositionHandle<M, F>(modelsWrapper: AbstractModelsWrapper<M, F>, realArrayDep: Dependency, arrayIndex: number): ModelHandle<M, F> {
    let handle: ModelHandle<M, F> = {
        updateModel: (modelName: string, value: M, state: any) => {
            let m = modelsWrapper.getModel(realArrayDep.modelName, state);
            let nm = modelsWrapper.setArrayFieldAtIndex(realArrayDep.fieldName, arrayIndex, m, {
                model: modelName,
                item: value
            });
            modelsWrapper.updateModel(realArrayDep.modelName, nm, state);
        },
        getModel: (modelName: string, state: any): M => {
            let m = modelsWrapper.getModel(realArrayDep.modelName, state);
            return modelsWrapper.getArrayFieldAtIndex(realArrayDep.fieldName, arrayIndex, m)?.item;
        },
        hookModel: (modelName: string): M => {
            let m = modelsWrapper.hookModel(realArrayDep.modelName);
            return modelsWrapper.getArrayFieldAtIndex(realArrayDep.fieldName, arrayIndex, m)?.item;
        }
    }
    return handle;
}

export type FormControllerAliases = { real: { modelName: string, fieldName: string, index: number }, fake: string, realSchemaName: string }[]
export function AliasedFormControllerWrapper(props: { aliases: FormControllerAliases, children?: React.ReactNode }) {
    let { aliases } = props;

    let schema = useContext(CSchema);
    let modelsWrapper = useContext(CModelsWrapper);
    let formStateWrapper = useContext(CFormStateWrapper);

    let nSchema: Schema = {...schema};
    

    for(let alias of aliases) {
        nSchema.models[alias.fake] = nSchema.models[alias.realSchemaName];
    }

    function aliasesForWrapper<M, F>(wrapper: AbstractModelsWrapper<M, F>, aliases: FormControllerAliases): ModelAliases<M, F> {
        return Object.fromEntries(
            aliases.map(alias => {
                return [
                    alias.fake,
                    {
                        handle: arrayPositionHandle(wrapper, new Dependency(`${alias.real.modelName}.${alias.real.fieldName}`), alias.real.index),
                        realSchemaName: alias.realSchemaName
                    }
                ]
            })
        );
    }

    let nModelsWrapper = new ModelsWrapperWithAliases(modelsWrapper, aliasesForWrapper(modelsWrapper, aliases));
    let nFormStateWrapper = new ModelsWrapperWithAliases(formStateWrapper, aliasesForWrapper(formStateWrapper, aliases));

    return (
        <CSchema.Provider value={nSchema}>
            <CModelsWrapper.Provider value={nModelsWrapper}>
                <CFormStateWrapper.Provider value={nFormStateWrapper}>
                    {props.children}
                </CFormStateWrapper.Provider>
            </CModelsWrapper.Provider>
        </CSchema.Provider>
    )
}
