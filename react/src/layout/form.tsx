import React, { useContext } from "react";
import { CFormController, fieldStateFromValue, FormController } from "../data/formController";
import { CModelsWrapper, CFormStateWrapper } from "../data/wrapper";
import { CSchema } from "../data/appwrapper";
import { Col, Form, Row } from "react-bootstrap";
import { Dependency } from "../data/dependency";
import { FieldInput, LabeledFieldInput } from "../component/reusable/input";
import { Layout, LayoutProps, LayoutType } from "./layout";
import { ValueSelectors } from "../hook/string";
import { useShown } from "../hook/shown";
import { useStore } from "react-redux";

export function LayoutWithFormController<C, P>(Child: LayoutType<C, P>): LayoutType<C, P> {
    return class extends Child {
        constructor(config: C) {
            super(config);

            let childComponent = this.component;

            this.component = (props) => {
                let ChildComponent = childComponent;
                let FormComponent = this.formComponent;
                return (
                    <FormComponent {...props}>
                        <ChildComponent {...props}/>
                    </FormComponent>
                )
            };
        }

        formComponent = (props: LayoutProps<P>) => {
            let formState = useContext(CFormStateWrapper);
            let schema = useContext(CSchema);
            let modelsWrapper = useContext(CModelsWrapper);

            let dependencies = this.getFormDependencies();

            let formController = new FormController(formState, modelsWrapper, dependencies, schema);

            return (
                <CFormController.Provider value={formController}>
                    { props.children }
                </CFormController.Provider>
            )
        };
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
    fields: string[],
    heading?: string,
    shown?: string,
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
        let listShown = useShown(this.config.shown, true, formState, ValueSelectors.Fields);

        if (! listShown) {
            return <></>
        }
        const heading = this.config.heading
            ? (
                <Row className="mb-2">
                    <Col>
                        <div className={"lead text-end"}>{ this.config.heading }</div>
                    </Col>
                    <Col></Col>
                </Row>
            )
            : undefined;
        return <>
            {heading}
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
