import { Form, Row, Col, Tabs, Tab, Container } from "react-bootstrap";
import { LabelTooltip } from "./label";
import { useSelector, useDispatch, useStore } from "react-redux";
import { mapProperties } from "../helper";
import { ContextReduxFormActions, ContextReduxFormSelectors, ContextReduxModelActions, ContextReduxModelSelectors, ContextSimulationInfoPromise } from './context'
import { useContext } from "react";
import { useSetup } from "../hooks";
import { EditorPanel } from './panel';
import { DependencyCollector } from '../dependency';
import { selectModels } from '../models';
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
    constructor({ formActions, formSelectors }) {
        this.formActions = formActions;
        this.formSelectors = formSelectors;
        this.models = {};
        this.fields = [];
    }

    getModel = (modelName, dependency) => {
        let selectFn = useSelector;
        let dispatchFn = useDispatch;

        let dispatch = dispatchFn();

        let { selectFormState } = this.formSelectors;
        let { updateFormState } = this.formActions;

        if (!(modelName in this.models)) {
            let model = {
                dependency,
                value: { ...selectFn(selectFormState(modelName)) }, // TODO evaluate this clone, it feels like its needed to be safe
                updateValue: (v) => dispatch(updateFormState({ name: modelName, value: v }))
            }
            this.models[modelName] = model;
        }
        return this.models[modelName];
    }

    getField = (dep) => {
        let dispatchFn = useDispatch;

        let dispatch = dispatchFn();

        let { fieldName, modelName } = dep;
        let { updateFormFieldState } = this.formActions;

        let findField = (modelName, fieldName) => {
            return this.fields.find((o) => {
                return o.modelName === modelName && o.fieldName === fieldName;
            })
        }

        var field = findField(modelName, fieldName);
        if (!field) {
            let model = this.getModel(modelName, dep.model);
            let currentValue = model.value[fieldName];
            field = {
                fieldName,
                modelName,
                model,
                value: currentValue,
                dependency: dep,
                updateValue: (v) => dispatch(updateFormFieldState({
                    name: modelName,
                    field: fieldName,
                    value: { // TODO, value should be defined as the param to the function??
                        value: v,
                        valid: dep.type.validate(v),
                        touched: true,
                        active: currentValue.active
                    }
                })),
                updateActive: (a) => dispatch(updateFormFieldState({
                    name: modelName,
                    field: fieldName,
                    value: { // TODO, value should be defined as the param to the function??
                        ...currentValue,
                        active: a
                    }
                }))
            }
            this.fields.push(field);
        }
        return field;
    }

    hookField = (fieldModelDep) => {
        return this.getField(fieldModelDep);
    }

    submitChanges = () => {
        Object.entries(this.models).forEach(([modelName, model]) => {
            let changesObj = mapProperties(model.value, (fieldName, fieldState) => fieldState.value);

            let nextModelValue = { ...model.dependency.value };
            Object.assign(nextModelValue, changesObj);

            model.dependency.updateValue(nextModelValue);
            // this should make sure that if any part of the reducers are inconsistent / cause mutations
            // then the form state should remain consistent with saved model copy
            model.updateValue(formStateFromModel(model.dependency.value, model.dependency.schema));
        })
    }

    cancelChanges = () => {
        Object.entries(this.models).forEach(([modelName, model]) => {
            model.updateValue(formStateFromModel(model.dependency.value, model.dependency.schema));
        })
    }

    isFormStateDirty = () => {
        let d = Object.values(this.fields).map(({ value: { active, touched } }) => active && touched).includes(true);
        return d;
    }
    isFormStateValid = () => {
        let v = !Object.values(this.fields).map(({ value: { active, valid } }) => !active || valid).includes(false); // TODO: check completeness (missing defined variables?)
        return v;
    }
}

function createFieldInput(field) {
    const onChange = (event) => {
        let nextValue = event.target.value;
        if (field.value.value !== nextValue) { // TODO fix field.value.value naming
            field.updateValue(nextValue);
        }
    }
    let InputComponent = field.dependency.type.component;
    return (<InputComponent
        valid={field.value.valid}
        touched={field.value.touched}
        value={field.value.value}
        onChange={onChange}
    />)
}

function createLabeledFieldInput(field) {
    let fieldInput = createFieldInput(field);
    
    return (
        <FormField label={field.dependency.displayName} tooltip={field.dependency.description} key={field.dependency.fieldName}>
            {fieldInput}
        </FormField>
    )
}

export function EditorFieldGrid(config, { dependencyCollector, formController }) {
    let columns = config.columns;
    let rows = config.rows;

    let els = [];

    let someRowHasLabel = rows.reduce((prev, cur) => prev || !!cur.label);
    
    els.push( // header row
        <Row>
            {(someRowHasLabel ? <Col></Col> : undefined)}
            {columns.map(colName => <Col><Form.Label size={"sm"}>{colName}</Form.Label></Col>)}
        </Row>
    )

    for(let row of rows) {
        let fields = row.fields;
        let labelElement = someRowHasLabel ? (<Form.Label size={"sm"}>{row.label || ""}</Form.Label>) : undefined;
        let rowElement = (
            <Row>
                {labelElement ? <Col>{labelElement}</Col> : undefined}
                {columns.map((_, index) => {
                    let field = fields[index];
                    let hookedField = formController.hookField(dependencyCollector.hookModelDependency(field));
                    let inputElement = createFieldInput(hookedField);
                    return inputElement;
                })}
            </Row>
        )
        els.push(rowElement);
    }

    return <Container>{els}</Container>
}

export function EditorFieldList(config, { dependencyCollector, formController }) {
    let fields = config.fields;

    return <Container>
        {fields.map(field => createLabeledFieldInput(
            formController.hookField(dependencyCollector.hookModelDependency(field))
        ))}
    </Container>
}

export function EditorTabs(config, { dependencyCollector, formController }) {
    let tabs = config.tabs;

    let tabEls = [];

    let firstTabKey = undefined;

    for(let tabConfig of tabs) {
        let name = tabConfig.name;
        let layouts = tabConfig.items;
        firstTabKey = firstTabKey || name;
        tabEls.push(
            <Tab eventKey={name} title={name}>
                {createElementsFromLayouts(layouts, { dependencyCollector, formController })}
            </Tab>
        )
    }

    return (
        <Tabs defaultActiveKey={firstTabKey}>
            {tabEls}
        </Tabs>
    )
}

function SpacedLayout(layoutFactory) {
    let formatChild = (child) => {
        return (
            <div className="sr-form-layout">
                {child}
            </div>
        )
    }

    return (cfg, {dependencyCollector, formController}) => {
        return formatChild(
            layoutFactory(cfg, {dependencyCollector, formController})
        );
    }
}

export function elementFactoryForLayoutName(layoutName) {
    switch(layoutName) {
        case "fieldList":
            return SpacedLayout(EditorFieldList);
        case "fieldTable":
            return SpacedLayout(EditorFieldGrid);
        case "tabs":
            return EditorTabs;
    }

    return undefined;
}

export function createElementFromLayout(layoutConfig, { dependencyCollector, formController }) {
    let factory = elementFactoryForLayoutName(layoutConfig.layout);
    return factory(layoutConfig, { dependencyCollector, formController });
}

export function createElementsFromLayouts(layoutConfigs, { dependencyCollector, formController }) { 
    return layoutConfigs?.map(cfg => createElementFromLayout(cfg, { dependencyCollector, formController }));
}

export let FormEditorPanel = ({ schema }) => ({ view, viewName }) => {
    let FormEditorPanelComponent = (props) => {
        let formActions = useContext(ContextReduxFormActions); // TODO: make these generic
        let formSelectors = useContext(ContextReduxFormSelectors);
        let modelActions = useContext(ContextReduxModelActions);
        let modelSelectors = useContext(ContextReduxModelSelectors);

        let simulationInfoPromise = useContext(ContextSimulationInfoPromise);

        let store = useStore();

        let getModels = () => {
            console.log("state", store.getState());
            return modelSelectors.selectModels(store.getState());
        }

        let saveToServer = (models) => {
            simulationInfoPromise.then((simulationInfo) => {
                simulationInfo.models = models;
                fetch("/save-simulation", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(simulationInfo)
                }).then(resp => {
                    // TODO: error handling
                    console.log("resp", resp);
                })
            })
        }

        let dependencyCollector = new DependencyCollector({ modelActions, modelSelectors, schema });
        let formController = new FormController({ formActions, formSelectors, simulationInfoPromise });

        let submit = () => {
            let models = getModels();
            formController.submitChanges();
            saveToServer(models);
        }

        let basic = view.config.basic;
        let advanced = view.config.advanced;

        let mainChildren = (!!basic) ? createElementsFromLayouts(basic, { dependencyCollector, formController }) : undefined;
        let modalChildren = (!!advanced) ? createElementsFromLayouts(advanced, { dependencyCollector, formController }) : undefined;

        let formProps = {
            submit: submit,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren,
            modalChildren,
            title: view.title || viewName,
            id: viewName
        }

        return (
            <EditorPanel {...formProps}>
            </EditorPanel>
        )
    }
    return FormEditorPanelComponent;
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
