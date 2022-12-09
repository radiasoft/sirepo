import { mapProperties } from "../utility/object";
import React from "react";
import { FormFieldState, FormModelState } from "../store/formState";
import { Dependency } from "./dependency";
import { ModelState } from "../store/models";
import { Schema, SchemaModel } from "../utility/schema";
import { ModelsAccessor } from "./accessor";
import { AbstractModelsWrapper } from "./wrapper";
import { InputLayout } from "../layout/input/input";



export let formStateFromModel = (model: ModelState, modelSchema: SchemaModel) => mapProperties(modelSchema, (fieldName, { type }) => {
    return {
        valid: type.validate(model[fieldName]),
        value: type.fromModelValue(model[fieldName]),
        touched: false,
        active: true
    }
})

export const CFormController = React.createContext<FormController>(undefined);

export function fieldStateFromValue<T>(value: any, lastState: FormFieldState<T>, type: InputLayout): FormFieldState<T> {
    return {
        valid: type.validate(value),
        value,
        active: lastState.active,
        touched: true
    }
}

export class FormController {
    formStatesAccessor: ModelsAccessor<FormModelState, FormFieldState<unknown>>;
    modelStatesAccessor: ModelsAccessor<ModelState, unknown>;
    constructor(
        private formStatesWrapper: AbstractModelsWrapper<FormModelState, FormFieldState<unknown>>, 
        private modelsWrapper: AbstractModelsWrapper<ModelState, unknown>, 
        private dependencies: Dependency[],
        private schema: Schema
    ) {
        this.formStatesAccessor = new ModelsAccessor(formStatesWrapper, dependencies);
        this.modelStatesAccessor = new ModelsAccessor(modelsWrapper, dependencies)
    }

    saveToModels = () => {
        let f = this.formStatesAccessor.getValues();
        this.formStatesAccessor.getModelNames().map(mn => {
            return {
                modelName: mn,
                changes: Object.fromEntries(f.filter(v => v.dependency.modelName == mn).map(mv => {
                    let modelSchema = this.schema.models[mn];
                    let v = modelSchema[mv.dependency.fieldName].type.toModelValue(mv.value.value);
                    return [
                        mv.dependency.fieldName,
                        v
                    ]
                }))
            }
        }).forEach(modelChanges => {
            let m = this.modelStatesAccessor.getModelValue(modelChanges.modelName);
            m = {...m}; //copy
            Object.assign(m, modelChanges.changes);

            console.log("submitting value ", m, " to ", modelChanges.modelName);
            this.modelsWrapper.updateModel(modelChanges.modelName, m);
            // this should make sure that if any part of the reducers are inconsistent / cause mutations
            // then the form state should remain consistent with saved model copy
            // TODO: this line has been changed with recent update, evaluate
            this.formStatesWrapper.updateModel(modelChanges.modelName, formStateFromModel(m, this.schema.models[modelChanges.modelName]))
        })
    }

    getFormStateAccessor = (): ModelsAccessor<FormModelState, FormFieldState<unknown>> => {
        return this.formStatesAccessor;
    }

    getModelsAccessor = (): ModelsAccessor<ModelState, unknown> => {
        return this.modelStatesAccessor;
    }

    getDependencies = (): Dependency[] => {
        return this.dependencies;
    }

    cancelChanges = () => {
        this.formStatesAccessor.modelNames.map(modelName => {
            this.formStatesWrapper.updateModel(modelName, formStateFromModel(
                this.modelStatesAccessor.getModelValue(modelName), 
                this.schema.models[modelName]));
        });
    }

    isFormStateDirty = () => {
        return this.formStatesAccessor.getValues().map(fv => !!fv.value.touched).includes(true);
    }
    isFormStateValid = () => {
        return !this.formStatesAccessor.getValues().map(fv => !!fv.value.valid).includes(false);
    }
}
