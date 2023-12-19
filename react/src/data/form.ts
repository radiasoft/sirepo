import { useState } from "react";
import { Dispatch, AnyAction } from "redux";
import { StoreState } from "../store/common";
import { FormFieldState, FormModelState } from "../store/formState";
import { ModelState } from "../store/models";
import { Dictionary, mapProperties } from "../utility/object";
import { Schema } from "../utility/schema";
import { StoreType, StoreTypes, expandDataStructure, revertDataStructure, getValueSelector } from "./data";
import { Dependency } from "./dependency";
import { DataHandle, EmptyDataHandle, EmptyModelHandle, HandleFactory, ModelHandle } from "./handle";

export type FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => void
type FormSelectorFunc<V> = (state: any) => V

type FormActions = {
    save: FormActionFunc,
    cancel: FormActionFunc,
    valid: FormSelectorFunc<boolean>
}

export function formStateFromModelState(modelState: ModelState): FormModelState {
    return mapProperties(modelState, (name, value) => initialFormStateFromValue(value));
}

export function formStateFromSingleValue<T>(value: T): FormFieldState<T> {
    return {
        valid: true,
        value,
        touched: false
    }
}

export function initialFormStateFromValue<T>(value: T): FormFieldState<T> {
    return expandDataStructure(value, formStateFromSingleValue);
}

export const callNextParentFunction = (inst: HandleFactory, fnName: 'save' | 'cancel', state: any, dispatch: Dispatch<AnyAction>) => {
    let p = inst.parent;

    while(p) {
        let fn: FormActionFunc = p[fnName];
        if(fn) {
            fn(state, dispatch);
            return;
        }
        p = p.parent;
    }
}

export class FormStateHandleFactory extends HandleFactory {
    private updated: Dictionary<any, FormActions> = new Dictionary();
    private listeners: Dictionary<any, () => void> = new Dictionary();

    constructor(schema: Schema, public parent: HandleFactory) {
        super(schema, parent);
    }

    private emptyDataHandleFor = <M, F>(parent: EmptyDataHandle<M, F>, updateCallback: (dh: DataHandle<M, F>) => void): EmptyDataHandle<M, F> => {
        return new (class implements EmptyDataHandle<M, F> {
            private dataHandleFor(parent: DataHandle<M, F>): DataHandle<M, F> {
                let dh: DataHandle<M, F> = new (class extends DataHandle<M, F> {
                    write = (value: F, state: StoreState<M>, dispatch: Dispatch<AnyAction>) => {
                        parent.write(value, state, dispatch);
                        updateCallback(dh);
                    }
                })(parent.value);
                return dh;
            }

            initialize(state: any): DataHandle<M, F> {
                return this.dataHandleFor(parent.initialize(state));
            }
            hook(): DataHandle<M, F> {
                return this.dataHandleFor(parent.hook());
            }
            
        })();
    }

    private addToUpdated = (key: any, value: FormActions) => {
        this.updated.put(key, value);
        this.notifyListeners();
    }

    private notifyListeners = () => {
        this.listeners.items().forEach(l => l.value());
    }

    save: FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => {
        this.updated.items().forEach(u => u.value.save(state, dispatch));
        this.updated = new Dictionary();
        this.notifyListeners();
        callNextParentFunction(this, "save", state, dispatch);
    }

    cancel: FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => {
        this.updated.items().forEach(u => u.value.cancel(state, dispatch));
        this.updated = new Dictionary();
        this.notifyListeners();
        callNextParentFunction(this, "cancel", state, dispatch);
    }

    isDirty = (): boolean => {
        //debugger;
        return this.updated.items().length > 0;
    }

    isValid = (state: any): boolean => {
        return !this.updated.items().map(u => !!u.value.valid(state)).includes(false);
    }

    useUpdates = (key: any) => {
        let [v, u] = useState({});
        this.listeners.put(key, () => u({}));
    }

    createHandle = <M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F> => {
        let edh = this.parent.createHandle<M, F>(dependency, type);
        if(type === StoreTypes.FormState) {
            return this.emptyDataHandleFor<M, F>(edh, (dh: DataHandle<M, F>) => {
                let f = (state: any) => this.parent.createHandle(dependency, StoreTypes.FormState).initialize(state);
                let m = (state: any) => this.parent.createHandle(dependency, StoreTypes.Models).initialize(state);
                this.addToUpdated(dh,
                {
                    save: (state: StoreState<any>, dispatch: Dispatch<AnyAction>) => {
                        console.log(`SAVING ${dependency.getDependencyString()}`);
                        /*if(dependency.getDependencyString() === "beamline.elements") {
                            debugger;
                        }*/
                        let fr = f(state);
                        let type = this.schema.models[dependency.modelName][dependency.fieldName].type
                        console.log("type", type);
                        let rawValue = revertDataStructure(fr.value, getValueSelector(StoreTypes.FormState));
                        console.log("rawValue", rawValue);
                        let v = type.toModelValue(rawValue);
                        console.log("value", v);
                        m(state).write(v, state, dispatch);
                    },
                    cancel: (state: StoreState<any>, dispatch: Dispatch<AnyAction>) => {
                        f(state).write(initialFormStateFromValue(m(state).value), state, dispatch);
                    },
                    valid: (state: any): boolean => {
                        return f(state).value.valid;
                    }
                });
            })
        }
        return edh;
    }

    createModelHandle<M, F>(modelName: string, type: StoreType<M, F>): EmptyModelHandle<M, ModelHandle<M>> {
        return this.parent.createModelHandle(modelName, type);
    }
}
