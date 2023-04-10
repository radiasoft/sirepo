import { ModelSelector, ModelWriteActionCreator } from "../store/common";
import { formActions, FormFieldState, FormModelState, formSelectors, formStatesSlice } from "../store/formState";
import { modelActions, modelSelectors, modelsSlice, ModelState } from "../store/models";
import { SchemaModel } from "../utility/schema";

export class StoreType<M, F> {
    constructor(public name: string) {}
}

export const StoreTypes:{
    Models: StoreType<ModelState, unknown>,
    FormState: StoreType<FormModelState, FormFieldState<unknown>>
} = {
    Models: new StoreType(modelsSlice.name),
    FormState: new StoreType(formStatesSlice.name)
}

export const getModelReadSelector = <M>(type: StoreType<M, any>) => {
    return (type === StoreTypes.Models ? modelSelectors.selectModel : formSelectors.selectModel) as ModelSelector<M>;
}
export const getModelWriteActionCreator = <V>(type: StoreType<V, any>) => {
    let mac = (type === StoreTypes.Models ? modelActions.updateModel : formActions.updateModel) as ModelWriteActionCreator<V>;
    return (name: string, value: V) => mac({ name, value });
}
export const getModelNamesSelector = (type: StoreType<any, any>) => {
    return (type === StoreTypes.Models ? modelSelectors.selectModelNames : formSelectors.selectModelNames);
}

export type ValueSelector<T> = (v: T) => any;

export const ValueSelectors = {
    Models: (v: any) => v,
    Form: (v: FormFieldState<unknown>) => v.value
}

export const getValueSelector = <F>(storeType: StoreType<any, F>): ((v: F) => any) => {
    return storeType === StoreTypes.Models ? ValueSelectors.Models : ValueSelectors.Form;
}

export function newModelFromSchema(modelSchema: SchemaModel, overrides: {[key: string]: any}): ModelState {
    let defaults = Object.fromEntries(Object.entries(modelSchema).filter(([name, value]) => value.defaultValue !== undefined).map(([name, value]) => [name, value.defaultValue]))
    return Object.assign(defaults, overrides);
}
