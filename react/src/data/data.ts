import { ModelSelector, ModelWriteActionCreator } from "../store/common";
import { formActions, FormFieldState, FormModelState, formSelectors } from "../store/formState";
import { modelActions, modelSelectors, ModelState } from "../store/models";

export type StoreType<M, F> = "Models" | "FormState"

export const StoreTypes:{
    Models: StoreType<ModelState, unknown>,
    FormState: StoreType<FormModelState, FormFieldState<unknown>>
} = {
    Models: "Models",
    FormState: "FormState"
}

export const getModelReadSelector = <V>(type: StoreType<V, any>) => {
    return (type === StoreTypes.Models ? modelSelectors.selectModel : formSelectors.selectModel) as ModelSelector<V>;
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

export const getValueSelector = <F>(storeType: StoreType<any, F>): ((v: F) => any) | ((v: F) => any) => {
    return storeType === StoreTypes.Models ? ValueSelectors.Models : ValueSelectors.Form;
}
