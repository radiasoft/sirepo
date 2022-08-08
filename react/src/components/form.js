import { Form, Row } from "react-bootstrap";
import { LabelTooltip } from "./label";
import { useSelector, useDispatch, useStore } from "react-redux";
import { mapProperties } from "../helper";
import { ContextReduxFormActions, ContextReduxFormSelectors, ContextReduxModelActions, ContextReduxModelSelectors } from './context'
import { useContext } from "react";
import { useSetup } from "../hooks";
import { EditorPanel } from './panel';
import { DependencyCollector } from '../dependency';
import { selectModels } from '../models';
import { updateFormState } from "../formState";

export function FormField(props) {
    let {label, tooltip} = props;
    return (
        <Form.Group size="sm" as={Row} className="mb-2">
            <Form.Label column="sm" sm={5} className="text-end">
                {label}
                {tooltip &&
                    <LabelTooltip text={tooltip} />
                }
            </Form.Label>
            {props.children}
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

        if(!(modelName in this.models)) {
            let model = {
                dependency ,
                value: {...selectFn(selectFormState(modelName))}, // TODO evaluate this clone, it feels like its needed to be safe
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
                return o.modelName == modelName && o.fieldName == fieldName;
            })
        }

        var field = findField(modelName, fieldName);
        if(!field) {
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

            let nextModelValue = {...model.dependency.value};
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

// TODO: build this call from schema
export const SchemaEditorPanel = ({ schema }) => ({ view, viewName }) => {
    let SchemaEditorPanelComponent = (props) => {
        let formActions = useContext(ContextReduxFormActions); // TODO: make these generic
        let formSelectors = useContext(ContextReduxFormSelectors);
        let modelActions = useContext(ContextReduxModelActions);
        let modelSelectors = useContext(ContextReduxModelSelectors);

        let depCollector = new DependencyCollector({ modelActions, modelSelectors, schema });
        let formController = new FormController({ formActions, formSelectors });

        let collectModelField = (depStr) => depCollector.hookModelDependency(depStr);
        let hookFormField = (dep) => formController.hookField(dep);

        let configFields = {
            basic: view.config.basicFields,
            advanced: view.config.advancedFields
        }

        let modelFields = mapProperties(configFields, (subviewName, depStrs) => depStrs.map(collectModelField));
        let formFields = mapProperties(modelFields, (subviewName, deps) => deps.map(hookFormField));
    
        let createFieldElementsForSubview = (subviewName) => {
            return (formFields[subviewName] || []).map(field => {
                const onChange = (event) => {
                    let nextValue = event.target.value;
                    if(field.value.value != nextValue) { // TODO fix field.value.value naming
                        field.updateValue(nextValue);
                    }
                }
                let InputComponent = field.dependency.type.component;
                return (
                    <FormField label={field.dependency.displayName} tooltip={field.dependency.description} key={field.dependency.fieldName}>
                        <InputComponent
                            valid={field.value.valid}
                            touched={field.value.touched}
                            value={field.value.value}
                            onChange={onChange}
                        />
                    </FormField>
                )
            })
        }

        let formProps = {
            submit: formController.submitChanges,
            cancel: formController.cancelChanges,
            showButtons: formController.isFormStateDirty(),
            formValid: formController.isFormStateValid(),
            mainChildren: createFieldElementsForSubview('basic'),
            modalChildren: createFieldElementsForSubview('advanced'),
            title: view.title || viewName,
            id: viewName
        }

        return (
            <EditorPanel {...formProps}>
            </EditorPanel>
        )
    }
    return SchemaEditorPanelComponent;
} 

export const FormStateInitializer = ({ schema }) => (child) => {
    let FormStateInitializerComponent = (props) => {
        let dispatch = useDispatch();
        let store = useStore();
        let hasInit = useSetup(true, (finishInitFormState) => {
            let models = selectModels(store.getState());

            Object.entries(models).forEach(([ modelName, model ]) => {
                if( modelName in schema.models ) { // TODO non-model data should not be stored with models in store
                    dispatch(updateFormState({ name: modelName, value: formStateFromModel(model, schema.models[modelName])})) // TODO automate this
                }
            })

            finishInitFormState();
        })
        let ChildComponent = child;
        return hasInit && <ChildComponent {...props}/>;
    }
    return FormStateInitializerComponent;
}
