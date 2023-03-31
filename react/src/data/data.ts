import { ModelSelector, ModelWriteActionCreator } from "../store/common";
import { formActions, FormFieldState, formSelectors } from "../store/formState";
import { modelActions, modelSelectors } from "../store/models";

export enum StoreType {
    Models,
    FormState
}

export const getModelReadSelector = <V>(type: StoreType) => {
    return (type === StoreType.Models ? modelSelectors.selectModel : formSelectors.selectModel) as ModelSelector<V>;
}
export const getModelWriteActionCreator = <V>(type: StoreType) => {
    let mac = (type === StoreType.Models ? modelActions.updateModel : formActions.updateModel) as ModelWriteActionCreator<V>;
    return (name: string, value: V) => mac({ name, value });
}
export const getModelNamesSelector = (type: StoreType) => {
    return (type === StoreType.Models ? modelSelectors.selectModelNames : formSelectors.selectModelNames);
}

export type ValueSelector<T> = (v: T) => any;

export const ValueSelectors = {
    Models: (v: any) => v,
    Form: (v: FormFieldState<unknown>) => v.value
}

export const getValueSelector = (storeType: StoreType): ((v: any) => any) | ((v: FormFieldState<unknown>) => unknown) => {
    return storeType === StoreType.Models ? ValueSelectors.Models : ValueSelectors.Form;
}
