import { Form, Row, Col, Container } from "react-bootstrap";
import { LabelTooltip } from "./label";
import { useSelector, useDispatch, useStore } from "react-redux";
import { mapProperties } from "../helper";
import { ContextRelativeHookedDependencyGroup, ContextRelativeFormController } from './context'
import { useContext } from "react";
import { useRenderCount, useSetup } from "../hooks";
import { selectModels } from '../models';
import { Dependency } from "../dependency";
import { updateFormState } from "../formState";

import "./form.scss";

export function FormField(props) {
    let { label, tooltip } = props;
    return (
        <Form.Group size="sm" as={Row} className="justify-content-center">
            <Form.Label column className="text-start">
                {label}
                {tooltip &&
                    <LabelTooltip text={tooltip} />
                }
            </Form.Label>
            <Col>
                {props.children}
            </Col>
        </Form.Group>
    )
}

export let formStateFromModel = (model, modelSchema) => mapProperties(modelSchema, (fieldName, { type }) => {
    const valid = type.validate(model[fieldName])
    return {
        valid: valid,
        value: valid ? model[fieldName] : "",
        touched: false,
        active: true
    }
})

export class FormController {
    constructor({ formActions, formSelectors, hookedDependencies }) {
        this.formActions = formActions;
        this.formSelectors = formSelectors;

        let selectFn = useSelector;
        let dispatchFn = useDispatch;

        let dispatch = dispatchFn();

        let { selectFormState } = this.formSelectors;
        let { updateFormState, updateFormFieldState } = this.formActions;

        this.hookedModels = {};

        this.hookedFields = hookedDependencies.map(hookedDependency => {
            let { fieldName, modelName } = hookedDependency;

            if(!(modelName in this.hookedModels)) {
                let formStateValue = selectFn(selectFormState(modelName));

                this.hookedModels[modelName] = {
                    dependency: hookedDependency.model,
                    value: { ...formStateValue },
                    updateValue: (v) => {
                        console.log("updating value: ", v, " in ", modelName);
                        return dispatch(updateFormState({ name: modelName, value: v }))
                    }
                }
            }

            let model = this.hookedModels[modelName];

            let currentValue = model.value[fieldName];

            return {
                fieldName,
                modelName,
                model,
                value: currentValue,
                dependency: hookedDependency,
                updateValue: (v) => {
                    console.log("updating value: ", v, " in ", modelName, fieldName);
                    return dispatch(updateFormFieldState({
                        name: modelName,
                        field: fieldName,
                        value: { // TODO, value should be defined as the param to the function??
                            value: v,
                            valid: hookedDependency.type.validate(v),
                            touched: true,
                            active: currentValue.active
                        }
                    }))
                },
                updateActive: (a) => dispatch(updateFormFieldState({
                    name: modelName,
                    field: fieldName,
                    value: { // TODO, value should be defined as the param to the function??
                        ...currentValue,
                        active: a
                    }
                }))
            }
        })
    }

    getHookedField = (dependency) => {
        return this.hookedFields.find(hookedDependency => {
            return (dependency.modelName === hookedDependency.modelName &&
                dependency.fieldName === hookedDependency.fieldName);
        })
    }

    submitChanges = () => {
        Object.entries(this.hookedModels).forEach(([modelName, model]) => {
            let changesObj = mapProperties(model.value, (fieldName, fieldState) => {
                let hookedDependency = this.getHookedField({
                    fieldName,
                    modelName
                });
                return hookedDependency.type.dbValue(fieldState.value)
            });

            let nextModelValue = { ...model.dependency.value };
            Object.assign(nextModelValue, changesObj);

            console.log("submitting value ", nextModelValue, " to ", modelName);
            model.dependency.updateModel(nextModelValue);
            // this should make sure that if any part of the reducers are inconsistent / cause mutations
            // then the form state should remain consistent with saved model copy
            // TODO: this line has been changed with recent update, evaluate
            model.updateValue(formStateFromModel(nextModelValue, model.dependency.schema));
        })
    }

    cancelChanges = () => {
        Object.entries(this.hookedModels).forEach(([modelName, model]) => {
            model.updateValue(formStateFromModel(model.dependency.value, model.dependency.schema));
        })
    }

    isFormStateDirty = () => {
        let d = Object.values(this.hookedFields).map(({ value: { active, touched } }) => active && touched).includes(true);
        return d;
    }
    isFormStateValid = () => {
        let v = !Object.values(this.hookedFields).map(({ value: { active, valid } }) => !active || valid).includes(false); // TODO: check completeness (missing defined variables?)
        return v;
    }
}

function FieldInput(props) {
    let { field } = props;

    useRenderCount("FieldInput");

    const onChange = (event) => {
        console.log("field input onChange");
        let nextValue = event.target.value;
        console.log("field.value.value", field.value.value);
        console.log("nextValue", nextValue);
        if (field.value.value !== nextValue) { // TODO fix field.value.value naming
            field.updateValue(nextValue);
        }
    }
    let InputComponent = field.dependency.type.component;
    return (<InputComponent
        dependency={field.dependency}
        valid={field.value.valid}
        touched={field.value.touched}
        value={field.value.value}
        onChange={onChange}
    />)
}

function LabeledFieldInput(props) {
    let { field } = props;

    useRenderCount("LabeledFieldInput");

    return (
        <FormField label={field.dependency.displayName} tooltip={field.dependency.description} key={field.dependency.fieldName}>
            <FieldInput field={field}></FieldInput>
        </FormField>
    )
}

export let FieldGridLayout = {
    getDependencies: (config) => {
        let fields = [];
        for(let row of config.rows) {
            fields.push(...(row.fields));
        }
        return fields;
    },

    element: (props) => {
        let { config } = props;

        let renderCountFn = useRenderCount;
        let contextFn = useContext;

        renderCountFn("FieldGridLayout");

        let formController = contextFn(ContextRelativeFormController);

        let columns = config.columns;
        let rows = config.rows;

        let els = [];

        let someRowHasLabel = rows.reduce((prev, cur) => prev || !!cur.label);
        
        els.push( // header row
            <Row key={"header"}>
                {(someRowHasLabel ? <Col key={"label_dummy"}></Col> : undefined)}
                {columns.map(colName => <Col key={colName}><Form.Label size={"sm"}>{colName}</Form.Label></Col>)}
            </Row>
        )

        for(let idx = 0; idx < rows.length; idx++) {
            let row = rows[idx];
            let fields = row.fields;
            let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
            let rowElement = (
                <Row key={idx}>
                    {labelElement ? <Col>{labelElement}</Col> : undefined}
                    {columns.map((_, index) => {
                        let field = fields[index];
                        let hookedField = formController.getHookedField(new Dependency(field));
                        return <FieldInput key={index} field={hookedField}></FieldInput>
                    })}
                </Row>
            )
            els.push(rowElement);
        }

        return <Container>{els}</Container>
    }
}

export let FieldListLayout = {
    getDependencies: (config) => {
        return config.fields;
    },

    element: (props) => {
        let { config } = props;

        let renderCountFn = useRenderCount;
        let contextFn = useContext;

        renderCountFn("FieldListLayout");

        let formController = contextFn(ContextRelativeFormController);

        let fields = config.fields;

        return <Container>
            {fields.map((field, idx) => (
                <LabeledFieldInput key={idx} field={formController.getHookedField(new Dependency(field))}></LabeledFieldInput>
            ))}
        </Container>
    }
}

export const FormStateInitializer = ({ schema }) => (child) => {
    let FormStateInitializerComponent = (props) => {
        let dispatch = useDispatch();
        let store = useStore();
        let hasInit = useSetup(true, (finishInitFormState) => {
            let models = selectModels(store.getState());

            Object.entries(models).forEach(([modelName, model]) => {
                if (modelName in schema.models) { // TODO non-model data should not be stored with models in store
                    dispatch(updateFormState({ name: modelName, value: formStateFromModel(model, schema.models[modelName]) })) // TODO automate this
                }
            })

            finishInitFormState();
        })
        let ChildComponent = child;
        return hasInit && <ChildComponent {...props} />;
    }
    return FormStateInitializerComponent;
}
