import { Dispatch, AnyAction } from "redux";
import { ArrayFieldElement, ArrayFieldState } from "../store/common";
import { Schema } from "../utility/schema";
import { StoreType } from "./data";
import { ArrayDataHandle, BaseHandleFactory, DataHandle, EmptyDataHandle } from "./handle";

type SaveFunc = (state: any, dispatch: Dispatch<AnyAction>) => void

type SaveFuncKeyPair = {
    key: any,
    saveFn: SaveFunc
}

export class FormStateHandleFactory extends BaseHandleFactory {
    private updated: SaveFuncKeyPair[] = []

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

    private addToUpdated = (key: any, saveFn: SaveFunc) => {
        let idx = this.updated.findIndex(u => u.key === key);
        if(idx >= 0) {
            this.updated.splice(idx, 1);
        }
        this.updated.push({
            key,
            saveFn
        })
    }

    save(state: any, dispatch: Dispatch<AnyAction>) {
        this.updated.forEach(u => u.saveFn(state, dispatch));
        this.updated = [];
    }

    createHandle<V>(dependency: Dependency, type: StoreType): EmptyDataHandle<V> {
        let edh = super.createHandle<V>(dependency, type);
        if(type === StoreType.FormState) {
            return this.emptyDataHandleFor<V, DataHandle<V>>(edh, (dh: DataHandle<V>) => {
                this.addToUpdated(
                    dh, 
                    (state: any, dispatch: Dispatch<AnyAction>) => {
                        let f = super.createHandle<V>(dependency, StoreType.FormState).initialize(state);
                        let m = super.createHandle<any>(dependency, StoreType.Models).initialize(state);
                        let v = this.schema.models[dependency.modelName][dependency.fieldName].type.toModelValue(f.value);
                        m.write(v, dispatch);
                    }
                );
            })
        }
        return edh;
    }

    createArrayHandle<V extends ArrayFieldState<V>>(dependency: Dependency, type: StoreType): EmptyDataHandle<V, ArrayDataHandle<V>> {
        let edh = super.createArrayHandle<V>(dependency, type);
        if(type === StoreType.FormState) {
            return this.emptyDataHandleFor<V, ArrayDataHandle<V>>(edh, (dh: ArrayDataHandle<V>) => {
                this.addToUpdated(
                    dh, 
                    (state: any, dispatch: Dispatch<AnyAction>) => {
                        let f = super.createArrayHandle<V>(dependency, StoreType.FormState).initialize(state);
                        let m = super.createArrayHandle<any>(dependency, StoreType.Models).initialize(state);
                        let v = this.schema.models[dependency.modelName][dependency.fieldName].type.toModelValue(f.value);
                        m.write(v, dispatch);
                    }
                );
            })
        }
        return edh;
    }
}
