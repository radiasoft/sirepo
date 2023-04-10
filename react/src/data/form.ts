import { useState } from "react";
import { Dispatch, AnyAction, Store } from "redux";
import { StoreState } from "../store/common";
import { FormModelState, initialFormStateFromValue } from "../store/formState";
import { ModelState } from "../store/models";
import { Schema } from "../utility/schema";
import { StoreType, StoreTypes } from "./data";
import { BaseHandleFactory, DataHandle, EmptyDataHandle, HandleFactory } from "./handle";

type FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => void
type FormSelectorFunc<V> = (state: any) => V

type FormActionsKeyPair = {
    key: any,
    save: FormActionFunc,
    cancel: FormActionFunc,
    valid: FormSelectorFunc<boolean>
}

export function formStateFromModelState(modelState: ModelState): FormModelState {
    return mapProperties(modelState, (name, value) => initialFormStateFromValue(value));
}

export class FormStateHandleFactory extends HandleFactory {
    private updated: FormActionsKeyPair[] = []
    private listeners: (() => void)[] = [];

    constructor(schema: Schema, private parent: HandleFactory) {
        super(schema);
    }

    private emptyDataHandleFor<M, F>(parent: EmptyDataHandle<M, F>, updateCallback: (dh: DataHandle<M, F>) => void): EmptyDataHandle<M, F> {
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

    private addToUpdated = (kp: FormActionsKeyPair) => {
        let idx = this.updated.findIndex(u => u.key === kp.key);
        if(idx >= 0) {
            this.updated.splice(idx, 1);
        }
        this.updated.push(kp)
    }

    private notifyListeners() {
        this.listeners.forEach(l => l());
    }

    save(state: any, dispatch: Dispatch<AnyAction>) {
        this.updated.forEach(u => u.save(state, dispatch));
        this.updated = [];
        this.notifyListeners();
    }

    cancel(state: any, dispatch: Dispatch<AnyAction>) {
        this.updated.forEach(u => u.cancel(state, dispatch));
        this.updated = [];
        this.notifyListeners();
    }

    isDirty(): boolean {
        return this.updated.length > 0;
    }

    isValid(state: any): boolean {
        return !this.updated.map(u => !!u.valid(state)).includes(false);
    }

    useUpdates() {
        let [v, u] = useState({});
        this.listeners.push(() => u({}));
    }

    createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F> {
        let edh = this.parent.createHandle<M, F>(dependency, type);
        if(type === StoreTypes.FormState) {
            return this.emptyDataHandleFor<M, F>(edh, (dh: DataHandle<M, F>) => {
                let f = (state: any) => this.parent.createHandle(dependency, StoreTypes.FormState).initialize(state);
                let m = (state: any) => this.parent.createHandle(dependency, StoreTypes.Models).initialize(state);
                this.addToUpdated({
                    key: dh,
                    save: (state: StoreState<any>, dispatch: Dispatch<AnyAction>) => {
                        let v = this.schema.models[dependency.modelName][dependency.fieldName].type.toModelValue(f(state).value);
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
}
