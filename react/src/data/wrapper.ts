import React, { Dispatch } from "react";
import { useDispatch, useSelector } from "react-redux";
import { AnyAction } from "redux";
import { FormActions, FormFieldState, FormModelState, FormSelectors } from "../store/formState";
import { ModelActions, ModelSelectors, ModelState } from "../store/models";

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

export const CFormStateWrapper = React.createContext<FormStateWrapper>(undefined);
export const CModelsWrapper = React.createContext<ModelsWrapper>(undefined);

export function getModelValues<M, F>(modelNames: string[], modelsWrapper: AbstractModelsWrapper<M, F>, state: any): {[modelName: string]: M} {
    return Object.fromEntries(modelNames.map(mn => [mn, modelsWrapper.getModel(mn, state)]));
}

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
        //console.log("dispatching update form to ", modelName, " changing to value ", value);
        this.dispatch(this.formActions.updateFormState({
            name: modelName,
            value
        }))
    }

    override hookModel = (modelName: string) => {
        let m = useSelector(this.formSelectors.selectFormState(modelName));
        if(m === undefined || m === null) {
            throw new Error("model could not be hooked because it was not found: " + modelName);
        }
        return m;
    }

    getFieldFromModel(fieldName: string, model: FormModelState): FormFieldState<unknown> {
        let fv = model[fieldName];
        if(fv === undefined || fv === null) {
            throw new Error(`field could not be found in model state: ${fieldName}, ${JSON.stringify(model)}`)
        }
        return fv;
    }

    setFieldInModel(fieldName: string, model: FormModelState, value: FormFieldState<unknown>): FormModelState {
        let m = {...model};
        m[fieldName] = value;
        return m;
    }
}

export class ModelsWrapper extends AbstractModelsWrapper<ModelState, unknown> {
    modelActions: ModelActions;
    modelSelectors: ModelSelectors;
    dispatch: Dispatch<AnyAction>;

    constructor({ modelActions, modelSelectors }: { modelActions: ModelActions, modelSelectors: ModelSelectors }) {
        super();
        this.modelActions = modelActions;
        this.modelSelectors = modelSelectors;

        let dispatchFn = useDispatch;
        this.dispatch = dispatchFn();
    }

    getModel = (modelName: string, state: any) => {
        return this.modelSelectors.selectModel(modelName)(state);
    }

    updateModel = (modelName: string, value: ModelState) => {
        //console.log("dispatching update to ", modelName, " changing to value ", value);
        this.dispatch(this.modelActions.updateModel({
            name: modelName,
            value
        }))
    }

    hookModel = (modelName: string) => {
        let m = useSelector(this.modelSelectors.selectModel(modelName));
        if(m === undefined || m === null) {
            throw new Error("model could not be hooked because it was not found: " + modelName);
        }
        return m;
    }

    getFieldFromModel(fieldName: string, model: ModelState): unknown {
        let fv = model[fieldName];
        if(fv === undefined || fv === null) {
            throw new Error(`field could not be found in model state: ${fieldName}, ${JSON.stringify(model)}`)
        }
        return fv;
    }

    setFieldInModel(fieldName: string, model: ModelState, value: unknown): ModelState {
        let m = {...model};
        m[fieldName] = value;
        return m;
    }

    // TODO: this should not be housed here, need separate abstraction to communicate to server, should just return formatted models
    saveToServer = (simulationInfo: any, modelNames: string[], state: any) => {
        let models = Object.fromEntries(modelNames.map(mn => [mn, this.getModel(mn, state)]));
        simulationInfo.models = models;
        fetch("/save-simulation", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(simulationInfo)
        }).then(resp => {
            // TODO: error handling
        })
    }
}
