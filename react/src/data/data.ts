import { ModelSelector, ModelWriteActionCreator } from "../store/common";
import { formActions, FormFieldState, FormModelState, formSelectors, formStatesSlice } from "../store/formState";
import { modelActions, modelSelectors, modelsSlice, ModelState } from "../store/models";
import { SchemaModel } from "../utility/schema";
import { mapProperties } from "../utility/object";

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
    console.log("modelSchema", modelSchema);
    let defaults = Object.fromEntries(Object.entries(modelSchema).filter(([name, value]) => value.defaultValue !== undefined).map(([name, value]) => [name, value.defaultValue]))
    return Object.assign(defaults, overrides);
}

export function expandDataStructure<T, R>(value: T, expansionFn: (v: T) => R): R {
    if(Array.isArray(value)) {
        return expansionFn(
            (value as any[]).map(ele => {
                return {
                    model: ele.model,
                    item: mapProperties(ele.item, (_, v) => expansionFn(v as T))
                }
            }) as T
        )
    }
    return expansionFn(value);
}

export function revertDataStructure<T, R>(value: T, revertFn: (v: T) => R): R {
    let v = revertFn(value);
    if(Array.isArray(v)) {
        return (v as any[]).map(ele => {
            return {
                model: ele.model,
                item: mapProperties(ele.item, (_, x) => revertFn(x as T))
            }
        }) as R
    }
    return v;
}
