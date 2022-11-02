import { mapProperties } from "../utility/object";
import { useDispatch, useSelector } from "react-redux";
import { useShown, ValueSelector } from "../hook/shown";
import React from "react";
import { FormActions, FormFieldState, FormSelectors, FormModelState } from "../store/formState";
import { AnyAction, Dispatch } from "redux";
import { Dependency, HookedDependency, HookedModel } from "./dependency";
import { ModelState } from "../store/models";
import { Schema } from "../utility/schema";


export abstract class AbstractModelsWrapper<M, F> {
    abstract getModel(modelName: string, state: any): M;
    abstract hookModel(modelName: string): M;
    abstract updateModel(modelName: string, value: M): void;
    abstract getFieldFromModel(fieldName: string, model: M): F;
    abstract setFieldInModel(fieldName: string, model: M, value: F): M;

    updateField = (fieldName: string, modelName: string, state: any, value: F): void => {
        let model = this.getModel(modelName, state);
        model = this.setFieldInModel(fieldName, model, value);
        this.updateModel(modelName, model);
    }
}

export class ModelsAccessor<M, F> {
    modelValues: {[key: string]: M};
    modelNames: string[];
    constructor(private modelsWrapper: AbstractModelsWrapper<M, F>, private dependencies: Dependency[]) {
        this.modelNames = [...new Set<string>(dependencies.map(d => d.modelName))];
        this.modelValues = Object.fromEntries(this.modelNames.map(modelName => {
            return [
                modelName,
                modelsWrapper.hookModel(modelName)
            ]
        }))
    }

    getFieldValue = (dependency: Dependency): F => {
        let m =  this.modelValues[dependency.modelName];
        return this.modelsWrapper.getFieldFromModel(dependency.fieldName, m);
    }

    getModelValue = (modelName: string): M => {
        return this.modelValues[modelName];
    }

    getValues = (): { dependency: Dependency, value: F }[] => {
        return this.dependencies.map(d => {
            return {
                dependency: d,
                value: this.getFieldValue(d)
            }
        })
    }

    getModelNames = (): string[] => {
        return this.modelNames;
    }
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

export class FormStateWrapper extends AbstractModelsWrapper<FormModelState, FormFieldState<unknown>> {
    formActions: FormActions;
    formSelectors: FormSelectors;
    dispatch: Dispatch<AnyAction>;
    constructor({ formActions, formSelectors }: { formActions: FormActions, formSelectors: FormSelectors }) {
        super();
        this.formActions = formActions;
        this.formSelectors = formSelectors;

        let dispatchFn = useDispatch;
        this.dispatch = dispatchFn();
    }

    override getModel = (modelName: string, state: any) => {
        return this.formSelectors.selectFormState(modelName)(state);
    }

    override updateModel = (modelName: string, value: any) => {
        console.log("dispatching update form to ", modelName, " changing to value ", value);
        this.dispatch(this.formActions.updateFormState({
            name: modelName,
            value
        }))
    }

    override hookModel = (modelName: string) => {
        let selectFn = useSelector;
        return selectFn(this.formSelectors.selectFormState(modelName));
    }

    getFieldFromModel(fieldName: string, model: FormModelState): FormFieldState<unknown> {
        return model[fieldName];
    }
    
    setFieldInModel(fieldName: string, model: FormModelState, value: FormFieldState<unknown>): FormModelState {
        let m = {...model};
        m[fieldName] = value;
        return m;
    }
}

export const ContextRelativeFormState = React.createContext<FormStateWrapper>(undefined);
export const ContextRelativeFormController = React.createContext<FormController>(undefined);

export class FormController {
    formStatesAccessor: ModelsAccessor<FormModelState, FormFieldState<unknown>>;
    modelStatesAccessor: ModelsAccessor<ModelState, unknown>;
    constructor(
        private formStatesWrapper: AbstractModelsWrapper<FormModelState, FormFieldState<unknown>>, 
        private modelsWrapper: AbstractModelsWrapper<ModelState, unknown>, 
        dependencies: Dependency[],
        private schema: Schema
    ) {
        this.formStatesAccessor = new ModelsAccessor(formStatesWrapper, dependencies);
        this.modelStatesAccessor = new ModelsAccessor(modelsWrapper, dependencies)
    }

    saveToModels = () => {
        let fv = this.formStatesAccessor.getValues();
        this.formStatesAccessor.getModelNames().map(mn => {
            let modelValues = fv.filter(v => v.dependency.modelName == mn)
            return {
                modelName: mn,
                changes: Object.fromEntries(modelValues.map(mv => {
                    let modelSchema = this.schema.models[mn];
                    let v = modelSchema[mv.dependency.fieldName].type.dbValue(mv.value.value);
                    return [
                        mv.dependency.fieldName,
                        v
                    ]
                }))
            }
        }).forEach(modelChanges => {
            let modelValue = this.modelStatesAccessor.getModelValue(modelChanges.modelName);
            modelValue = {...modelValue}; //copy
            Object.assign(modelValue, modelChanges.changes);

            console.log("submitting value ", modelValue, " to ", modelChanges.modelName);
            this.modelsWrapper.updateModel(modelChanges.modelName, modelValue);
            // this should make sure that if any part of the reducers are inconsistent / cause mutations
            // then the form state should remain consistent with saved model copy
            // TODO: this line has been changed with recent update, evaluate
            this.formStatesWrapper.updateModel(modelChanges.modelName, formStateFromModel(modelValue, this.schema.models[modelChanges.modelName]))
        })
    }

    cancelChanges = () => {
        this.formStatesAccessor.modelNames.map(modelName => {
            let mv = this.modelStatesAccessor.getModelValue(modelName);
            let ms = this.schema.models[modelName];
            this.formStatesWrapper.updateModel(modelName, formStateFromModel(mv, ms));
        });
    }

    isFormStateDirty = () => {
        return this.formStatesAccessor.getValues().map(fv => !!fv.value.touched).includes(true);
    }
    isFormStateValid = () => {
        return !this.formStatesAccessor.getValues().map(fv => !!fv.value.valid).includes(false);
    }
}
