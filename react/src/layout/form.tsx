import { View } from "./layout";
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
import "./form.scss";
import { useShown } from "../hook/shown";
import { CModelsWrapper, CFormStateWrapper } from "../data/wrapper";
import { useStore } from "react-redux";
import { CSchema } from "../data/appwrapper";
import { ValueSelectors } from "../hook/string";

export function LayoutWithFormController<P>(Child: new() => View<P>): (new() => View<P>) {
    let child = new Child();

    return new class extends View<P> {
        getFormDependencies(config: P): Dependency[] {
            return child.getFormDependencies(config);
        }

        formComponent = (props) => {
            let { config } = props;
    
            let contextFn = useContext;
            let formState = contextFn(CFormStateWrapper);
            let schema = contextFn(CSchema);
            let modelsWrapper = contextFn(CModelsWrapper);
    
            let dependencies = this.getFormDependencies(config);
    
            let formController = new FormController(formState, modelsWrapper, dependencies, schema);
    
            return (
                <CFormController.Provider value={formController}>
                    { props.children }
                </CFormController.Provider>
            )
        };

        component: React.FunctionComponent<{ config: P; }> = (props) => {
            let ChildComponent = child.component;
            let FormComponent = this.formComponent;
            return (
                <FormComponent {...props}>
                    <ChildComponent {...props}/>
                </FormComponent>
            )
        };
    } as unknown as (new() => View<P>);
}

export type FieldGridRow = {
    label?: string,
    description?: string,
    fields: string[],
    shown?: string
}

export type FieldGridConfig = {
    columns: string[],
    rows: FieldGridRow[]
}

export type FieldGridProps = {
    config: FieldGridConfig
}

export class FieldGridLayout extends View<FieldGridConfig> {
    getFormDependencies = (config) => {
        let fields = [];
        for(let row of config.rows) {
            fields.push(...(row.fields));
        }
        return fields.map(f => new Dependency(f));
    }

    component = (props: FieldGridProps) => {
        let { config } = props;

        let formController = useContext(CFormController);
        let formState = useContext(CFormStateWrapper);
        let schema = useContext(CSchema);
        let store = useStore();

        let columns = config.columns;
        let rows = config.rows;

        let els = [];

        let someRowHasLabel = rows.reduce<boolean>((prev: boolean, cur: FieldGridRow) => prev || !!cur.label, false);
        
        els.push( // header row
            <Row className="sr-form-row" key={"header"}>
                {(someRowHasLabel ? <Col key={"label_dummy"}></Col> : undefined)}
                {columns.map(colName => <Col key={colName}><Form.Label size={"sm"}>{colName}</Form.Label></Col>)}
            </Row>
        )

        let shownFn = useShown;

        for(let idx = 0; idx < rows.length; idx++) {
            let row = rows[idx];
            let shown = shownFn(row.shown, true, formState, ValueSelectors.Fields);
            let fields = row.fields;
            let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
            let rowElement = shown ? (
                <Row className="sr-form-row" key={idx}>
                    {labelElement ? <Col>{labelElement}</Col> : undefined}
                    {columns.map((_, index) => {
                        let fieldDepString = fields[index];
                        let fieldDependency = new Dependency(fieldDepString);
                        let fieldValue = formController.getFormStateAccessor().getFieldValue(fieldDependency);
                        let fieldType = schema.models[fieldDependency.modelName][fieldDependency.fieldName].type;
                        return <FieldInput 
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
                    })}
                </Row>
            ) : undefined;
            els.push(rowElement);
        }

        return <Container>{els}</Container>
    }
}

export type FieldListConfig = {
    fields: string[]
}

export type FieldListProps = {
    config: FieldListConfig
}

export class FieldListLayout extends View<FieldListConfig> {
    getFormDependencies = (config) => {
        return (config.fields || []).map(f => new Dependency(f));
    }

    component = (props: FieldListProps) => {
        let { config } = props;

        let formController = useContext(CFormController);
        let formState = useContext(CFormStateWrapper);
        let schema = useContext(CSchema);
        let store = useStore();

        let fields = config.fields;

        return <Container>
            {fields.map((fieldDepString, idx) => {
                let fieldDep = new Dependency(fieldDepString);
                let fieldValue = formController.getFormStateAccessor().getFieldValue(fieldDep);
                let fieldSchema = schema.models[fieldDep.modelName][fieldDep.fieldName];

                if(fieldValue.active) {
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
        </Container>
    }
}
