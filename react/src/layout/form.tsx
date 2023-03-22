import { LayoutProps, LayoutType, Layout } from "./layout";
import React, { useContext } from "react";
import {
    Row,
    Col,
    Form,
    Container
} from "react-bootstrap";
import { Dependency } from "../data/dependency";
import { FieldInput, LabeledFieldInput } from "../component/reusable/input";
import { CFormController, fieldStateFromValue, FormController } from "../data/formController";
import { useShown } from "../hook/shown";
import { CModelsWrapper, CFormStateWrapper, ModelsWrapperWithAliases, AbstractModelsWrapper, ModelAliases, ModelHandle } from "../data/wrapper";
import { useStore } from "react-redux";
import { CSchema } from "../data/appwrapper";
import { ValueSelectors } from "../utility/string";
import { Schema } from "../utility/schema";

export function FormControllerElement(props: {children?: React.ReactNode, dependencies: Dependency[]}) {
    let formState = useContext(CFormStateWrapper);
    let schema = useContext(CSchema);
    let modelsWrapper = useContext(CModelsWrapper);
    let formController = new FormController(formState, modelsWrapper, props.dependencies, schema);

    return (
        <CFormController.Provider value={formController}>
            { props.children }
        </CFormController.Provider>
    )
}

export function LayoutWithFormController<C, P>(Child: LayoutType<C, P>): LayoutType<C, P> {
    return class extends Child {
        constructor(config: C) {
            super(config);

            let childComponent = this.component;

            this.component = (props) => {
                let ChildComponent = childComponent;
                return (
                    <FormControllerElement dependencies={this.getFormDependencies()} {...props}>
                        <ChildComponent {...props}/>
                    </FormControllerElement>
                )
            };
        }
    };
}

export type FieldGridRow = {
    label?: string,
    description?: string,
    fields: string[],
    shown?: string
}

export type FieldGridConfig = {
    columns: string[],
    rows: FieldGridRow[],
    shown?: string,
}

export class FieldGridLayout extends Layout<FieldGridConfig, {}> {
    getFormDependencies = () => {
        let fields = [];
        for(let row of this.config.rows) {
            fields.push(...(row.fields));
        }
        return fields.map(f => new Dependency(f));
    }

    component = (props: LayoutProps<{}>) => {
        let formController = useContext(CFormController);
        let formState = useContext(CFormStateWrapper);
        let schema = useContext(CSchema);
        let store = useStore();
        let gridShown = useShown(this.config.shown, true, formState, ValueSelectors.Fields);

        if (! gridShown) {
            return <></>
        }

        let columns = this.config.columns;
        let rows = this.config.rows;

        let els = [];

        let someRowHasLabel = rows.reduce<boolean>((prev: boolean, cur: FieldGridRow) => prev || !!cur.label, false);
        els.push( // header row
            <Row className="mb-2" key={"header"}>
                {(someRowHasLabel ? <Col key={"label_dummy"}></Col> : undefined)}
                {columns.map(colName => <Col key={colName}><div className={"lead text-center"}>{colName}</div></Col>)}
            </Row>
        )

        for(let idx = 0; idx < rows.length; idx++) {
            let row = rows[idx];
            let shown = useShown(row.shown, true, formState, ValueSelectors.Fields);
            let fields = row.fields;
            let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
            let rowElement = shown ? (
                <Row className="mb-2" key={idx}>
                    {labelElement ? <Col className="text-end">{labelElement}</Col> : undefined}
                    {columns.map((_, index) => {
                        let fieldDepString = fields[index];
                        let fieldDependency = new Dependency(fieldDepString);
                        let fieldValue = formController.getFormStateAccessor().getFieldValue(fieldDependency);
                        let fieldType = schema.models[fieldDependency.modelName][fieldDependency.fieldName].type;
                        return (<Col key={index}>
                            <FieldInput
                                key={index}
                                value={fieldValue}
                                updateField={(value: unknown): void => {
                                    formState.updateField(
                                        fieldDependency.fieldName,
                                        fieldDependency.modelName,
                                        store.getState(),
                                        fieldStateFromValue(value, fieldValue, fieldType));
                                }}
                                dependency={fieldDependency}
                                inputComponent={fieldType.component}/>
                        </Col>)
                    })}
                </Row>
            ) : undefined;
            els.push(rowElement);
        }

        return <>{els}</>
    }
}

export type FieldListConfig = {
    fields: string[]
}

export class FieldListLayout extends Layout<FieldListConfig, {}> {
    constructor(config: FieldListConfig) {
        super(config);
    }

    getFormDependencies = () => {
        return (this.config.fields || []).map(f => new Dependency(f));
    }

    component = (props: LayoutProps<{}>) => {
        let formController = useContext(CFormController);
        let formState = useContext(CFormStateWrapper);
        let schema = useContext(CSchema);
        let store = useStore();

        let fields = this.config.fields;

        return <>
            {fields.map((fieldDepString, idx) => {
                let fieldDep = new Dependency(fieldDepString);
                let fieldValue = formController.getFormStateAccessor().getFieldValue(fieldDep);
                let fieldSchema = schema.models[fieldDep.modelName][fieldDep.fieldName];
                let shown = useShown(fieldSchema.shown, true, formState, ValueSelectors.Fields);

                if(shown && fieldValue.active) {
                    return <LabeledFieldInput
                    key={idx}
                    value={fieldValue}
                    dependency={fieldDep}
                    displayName={fieldSchema.displayName}
                    description={fieldSchema.description}
                    updateField={(value: unknown): void => {
                        formState.updateField(
                            fieldDep.fieldName,
                            fieldDep.modelName,
                            store.getState(),
                            fieldStateFromValue(value, fieldValue, fieldSchema.type));
                    }}
                    inputComponent={fieldSchema.type.component}/>
                }

                return undefined;
            })}
        </>
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
