import { LayoutProps, LayoutType, Layout } from "./layout";
import React, { useContext, useState } from "react";
import {
    Row,
    Col,
    Form
} from "react-bootstrap";
import { Dependency } from "../data/dependency";
import { FieldInput, LabeledFieldInput } from "../component/reusable/input";
import { useShown } from "../hook/shown";
import { useDispatch, useStore } from "react-redux";
import { CSchema } from "../data/appwrapper";
import { FormStateHandleFactory } from "../data/form";
import { CHandleFactory } from "../data/handle";
import { StoreTypes } from "../data/data";
import { useCoupledState } from "../hook/coupling";

export function FormControllerElement(props: {children?: React.ReactNode}) {
    let schema = useContext(CSchema);
    let handleFactory = useContext(CHandleFactory);
    let [formHandleFactory, _, hfChanged] = useCoupledState(handleFactory, new FormStateHandleFactory(schema, handleFactory));
    if(hfChanged) {
        return <></>
    }
    // TODO: form controller might need to "subscribe to updates" during save
    formHandleFactory.useUpdates(FormControllerElement);

    return (
        <CHandleFactory.Provider value={formHandleFactory}>
            { props.children }
        </CHandleFactory.Provider>
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
                    <FormControllerElement {...props}>
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
    component = (props: LayoutProps<{}>) => {
        let formHandleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        let schema = useContext(CSchema);
        let dispatch = useDispatch();
        let store = useStore();
        let gridShown = useShown(this.config.shown, true, StoreTypes.FormState);

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
            let shown = useShown(row.shown, true, StoreTypes.FormState);
            let fields = row.fields;
            let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
            let rowElement = shown ? (
                <Row className="mb-2" key={idx}>
                    {labelElement ? <Col className="text-end">{labelElement}</Col> : undefined}
                    {columns.map((_, index) => {
                        let fieldDependency = new Dependency(fields[index]);
                        let fieldHandle = formHandleFactory.createHandle(fieldDependency, StoreTypes.FormState).hook();
                        let fieldType = schema.models[fieldDependency.modelName][fieldDependency.fieldName].type;
                        return (<Col key={index}>
                            <FieldInput
                                key={index}
                                value={fieldHandle.value}
                                updateField={(value: unknown): void => {
                                    fieldHandle.write({
                                        valid: fieldType.validate(value),
                                        touched: true,
                                        value
                                    }, store.getState(), dispatch)
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

    component = (props: LayoutProps<{}>) => {
        let formHandleFactory = useContext(CHandleFactory) as FormStateHandleFactory;
        let schema = useContext(CSchema);
        let dispatch = useDispatch();
        let store = useStore();

        let fields = this.config.fields;
        let listShown = useShown(this.config.shown, true, StoreTypes.FormState);

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
                let fieldHandle = formHandleFactory.createHandle(fieldDep, StoreTypes.FormState).hook();
                let fieldType = schema.models[fieldDep.modelName][fieldDep.fieldName].type;
                let fieldSchema = schema.models[fieldDep.modelName][fieldDep.fieldName];
                let shown = useShown(fieldSchema.shown, true, StoreTypes.FormState);

                if(shown) {
                    return <LabeledFieldInput
                    key={idx}
                    value={fieldHandle.value}
                    dependency={fieldDep}
                    displayName={fieldSchema.displayName}
                    description={fieldSchema.description}
                    updateField={(value: unknown): void => {
                        fieldHandle.write({
                            valid: fieldType.validate(value),
                            touched: true,
                            value
                        }, store.getState(), dispatch)
                    }}
                    inputComponent={fieldSchema.type.component}/>
                }

                return undefined;
            })}
        </>
    }
}
