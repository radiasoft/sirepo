import { useState } from "react";
import { Dispatch, AnyAction } from "redux";
import { ArrayFieldElement, ArrayFieldState } from "../store/common";
import { initialFormStateFromValue } from "../store/formState";
import { Schema } from "../utility/schema";
import { StoreType, StoreTypes } from "./data";
import { ArrayDataHandle, BaseHandleFactory, DataHandle, EmptyDataHandle } from "./handle";

type FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => void
type FormSelectorFunc<V> = (state: any) => V

type FormActionsKeyPair = {
    key: any,
    save: FormActionFunc,
    cancel: FormActionFunc,
    valid: FormSelectorFunc<boolean>
}

export class FormStateHandleFactory extends BaseHandleFactory {
    private updated: FormActionsKeyPair[] = []
    private listeners: (() => void)[] = [];

    constructor(private schema: Schema) {
        super();
    }

    private emptyDataHandleFor<V, D extends DataHandle<V>>(parent: EmptyDataHandle<V>, updateCallback: (dh: D) => void): EmptyDataHandle<V, D> {
        return new (class implements EmptyDataHandle<V, D> {
            private dataHandleFor<V>(parent: DataHandle<V>): D {
                let dh = new (class extends ArrayDataHandle<any> {
                    append(element: ArrayFieldElement<V>, dispatch: Dispatch<AnyAction>) {
                        (parent as ArrayDataHandle<any>).append(element, dispatch);
                        updateCallback(dh);
                    }
                    appendAt(index: number, element: ArrayFieldElement<V>, dispatch: Dispatch<AnyAction>) {
                        (parent as ArrayDataHandle<any>).appendAt(index, element, dispatch);
                        updateCallback(dh);
                    }
                    removeAt(index: number, dispatch: Dispatch<AnyAction>) {
                        (parent as ArrayDataHandle<any>).removeAt(index, dispatch);
                        updateCallback(dh);
                    }
                    write = (value: V, dispatch: Dispatch<AnyAction>) => {
                        parent.write(value, dispatch);
                        updateCallback(dh);
                    }
                })(parent.value) as any as D;
                return dh;
            }

            initialize(state: any): D {
                return this.dataHandleFor(parent.initialize(state));
            }
            hook(): D {
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

    createHandle<V>(dependency: Dependency, type: StoreType<any, V>): EmptyDataHandle<V> {
        let edh = super.createHandle<V>(dependency, type);
        if(type === StoreTypes.FormState) {
            return this.emptyDataHandleFor<V, DataHandle<V>>(edh, (dh: DataHandle<V>) => {
                let f = (state: any) => super.createHandle<any>(dependency, StoreTypes.FormState).initialize(state);
                let m = (state: any) => super.createHandle<any>(dependency, StoreTypes.Models).initialize(state);
                this.addToUpdated({
                    key: dh,
                    save: (state: any, dispatch: Dispatch<AnyAction>) => {
                        let v = this.schema.models[dependency.modelName][dependency.fieldName].type.toModelValue(f(state).value);
                        m(state).write(v, dispatch);
                    },
                    cancel: (state: any, dispatch: Dispatch<AnyAction>) => {
                        f(state).write(initialFormStateFromValue(m(state).value), dispatch);
                    },
                    valid: (state: any): boolean => {
                        return f(state).value.valid;
                    }
                });
            })
        }
        return edh;
    }

    createArrayHandle<V extends ArrayFieldState<V>>(dependency: Dependency, type: StoreType<any, V>): EmptyDataHandle<V, ArrayDataHandle<V>> {
        let edh = super.createArrayHandle<V>(dependency, type);
        if(type === StoreTypes.FormState) {
            return this.emptyDataHandleFor<V, ArrayDataHandle<V>>(edh, (dh: ArrayDataHandle<V>) => {
                let f = (state) => super.createArrayHandle<any>(dependency, StoreTypes.FormState).initialize(state);
                let m = (state) => super.createArrayHandle<any>(dependency, StoreTypes.Models).initialize(state);
                this.addToUpdated({
                    key: dh,
                    save: (state: any, dispatch: Dispatch<AnyAction>) => {
                        let v = this.schema.models[dependency.modelName][dependency.fieldName].type.toModelValue(f(state).value);
                        m(state).write(v, dispatch);
                    },
                    cancel: (state: any, dispatch: Dispatch<AnyAction>) => {
                        f(state).write(initialFormStateFromValue(m(state).value), dispatch);
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
