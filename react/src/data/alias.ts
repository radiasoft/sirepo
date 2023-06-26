import { Dispatch, AnyAction } from "redux";
import { ArrayFieldElement, ArrayFieldState, StoreState } from "../store/common";
import { Schema } from "../utility/schema";
import { expandDataStructure, getValueSelector, revertDataStructure, StoreType, StoreTypes, ValueSelectors } from "./data";
import { Dependency } from "./dependency";
import { DataHandle, EmptyDataHandle, EmptyModelHandle, HandleFactory, ModelHandle } from "./handle";
import cloneDeep from 'lodash/cloneDeep';
import { ModelState } from "../store/models";
import { FormModelState } from "../store/formState";
import { callNextParentFunction, FormActionFunc, formStateFromSingleValue, initialFormStateFromValue } from "./form";
import { mapProperties } from "../utility/object";
import { useState } from "react";

export type AliasDataLocation = {
    modelName: string,
    fieldName: string,
    index: number
}

export type ArrayAliases = {
    realDataLocation: AliasDataLocation,
    realSchemaName: string,
    fake: string
}[]

export class HandleFactoryWithArrayAliases extends HandleFactory {
    constructor(schema: Schema, private aliases: ArrayAliases, public parent: HandleFactory) {
        super(schema, parent);
    }

    private emptyAliasedHandle = <M, F>(location: AliasDataLocation, type: StoreType<M, F>): EmptyDataHandle<M, F> => {
        return this.parent.createHandle(new Dependency(`${location.modelName}.${location.fieldName}`), type);
    }

    private getArrayElementFromParentHandle = <M, F>(dh: DataHandle<M, F>, index: number, type: StoreType<M, F>): ArrayFieldElement<M> => {
        let mv = getValueSelector(type)(dh.value)[index];
        if(!mv) {
            console.error(`could not find index=${index}`);
            console.error(`was looking in`, getValueSelector(type)(dh.value))
        }
        return mv;
    }

    createHandle = <M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F, DataHandle<M, F>> => {
        let alias = this.aliases.find(a => a.fake === dependency.modelName);
        let getAE = this.getArrayElementFromParentHandle;
        if(alias !== undefined) {
            let edh = this.emptyAliasedHandle(alias.realDataLocation, type);
            return new (class implements EmptyDataHandle<M, F> {
                private createDummyHandle(dh: DataHandle<M, F>): DataHandle<M, F> {
                    let mv = getAE(dh, alias.realDataLocation.index, type);
                    let fv = mv.item[dependency.fieldName];
                    return new (class extends DataHandle<M, F> {
                        write(value: F, state: StoreState<M>, dispatch: Dispatch<AnyAction>) {
                            let v = cloneDeep(dh.value);
                            let av = getValueSelector(type)(v) as ArrayFieldState<M>;
                            av[alias.realDataLocation.index].item[dependency.fieldName] = value;
                            dh.write(v, state, dispatch);
                        }
                    })(fv);
                }

                initialize(state: any): DataHandle<M, F> {
                    return this.createDummyHandle(edh.initialize(state));
                }
                hook(): DataHandle<M, F> {
                    return this.createDummyHandle(edh.hook());
                }
            })();
        }
        return this.parent.createHandle(dependency, type);
    }

    createModelHandle<M, F>(modelName: string, type: StoreType<M, F>): EmptyModelHandle<M, ModelHandle<M>> {
        let alias = this.aliases.find(a => a.fake === modelName);
        if(alias === undefined) {
            return this.parent.createModelHandle(modelName, type);
        }

        let edh = this.emptyAliasedHandle(alias.realDataLocation, type);

        return {
            initialize: (state) => {
                let dh = edh.initialize(state);
                return new ModelHandle(this.getArrayElementFromParentHandle(dh, alias.realDataLocation.index, type).item);
            },
            hook: () => {
                let dh = edh.hook();
                return new ModelHandle(this.getArrayElementFromParentHandle(dh, alias.realDataLocation.index, type).item);
            }
        }
    }
}

export type HandleFactorySimpleAliases = {
    real: string,
    fake: string
}[]

export class HandleFactoryWithSimpleAliases extends HandleFactory {
    constructor(schema: Schema, private aliases: HandleFactorySimpleAliases, parent: HandleFactory) {
        super(schema, parent);
    }

    private findAlias(name: string) {
        return this.aliases.find(a => a.fake === name);
    }

    createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F, DataHandle<M, F>> {
        let alias = this.findAlias(dependency.modelName);
        if(alias) {
            return this.parent.createHandle(new Dependency(`${alias.real}.${dependency.fieldName}`), type);
        }
        return this.parent.createHandle(dependency, type);
    }

    createModelHandle<M, F>(modelName: string, type: StoreType<M, F>): EmptyModelHandle<M, ModelHandle<M>> {
        let alias = this.findAlias(modelName);
        if(alias) {
            return this.parent.createModelHandle(alias.real, type);
        }
        return this.parent.createModelHandle(modelName, type);
    }
    
}

export type HandleFactoryOverrides = {
    fake: string,
    value: ModelState,
    formValue?: FormModelState,
    onSave?: (value: ModelState) => void
}[]

export class HandleFactoryWithOverrides extends HandleFactory {
    constructor(schema: Schema, private overrides: HandleFactoryOverrides, parent: HandleFactory) {
        super(schema, parent);

        overrides.forEach(ov => {
            ov.formValue = mapProperties(ov.value, (n, i) => initialFormStateFromValue(i));
        })
    }

    save: FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => {
        //callNextParentFunction(this, "save", state, dispatch);
        this.overrides.forEach(o => o.onSave && o.onSave(o.value));
    }

    cancel: FormActionFunc = (state: any, dispatch: Dispatch<AnyAction>) => {
        //callNextParentFunction(this, "cancel", state, dispatch);
        
    }

    isDirty = (): boolean => {
        //debugger;
        return this.overrides.flatMap(o => Object.entries(o.formValue).map(([n, v]) => v.touched)).includes(true);
    }

    isValid = (state: any): boolean => {
        return !(this.overrides.flatMap(o => Object.entries(o.formValue).map(([n, v]) => v.valid)).includes(false));
    }

    updateHooks: {[key: string]: (() => void)[]} = {};

    addNotify = (dependency: Dependency, func: () => void) => {
        let k = dependency.getDependencyString();
        if(!(k in this.updateHooks)) {
            this.updateHooks[k] = [];
        }
        this.updateHooks[k].push(func);
    }

    notify = (dependency: Dependency) => {
        let k = dependency.getDependencyString();
        (this.updateHooks[k] || []).forEach(f => f());
    }

    createHandle = <M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F, DataHandle<M, F>> => {
        let override = this.overrides.find(a => a.fake === dependency.modelName);
        let inst = this;
        //console.log(`resolving dependency=${dependency.getDependencyString()}`)
        if(override !== undefined) {
            //console.log(`overriding handle for dependency=${dependency.getDependencyString()}, override=${JSON.stringify(override)}`);
            return new (class implements EmptyDataHandle<M, F> {
                private createDummyHandle(): DataHandle<M, F> {
                    let mv = type === StoreTypes.Models ? override.value : override.formValue;
                    let fv = mv[dependency.fieldName] as F;
                    //console.log(`${dependency.getDependencyString()} = ${JSON.stringify(fv)}`)
                    return new (class extends DataHandle<M, F> {
                        write(value: F, state: any, dispatch: Dispatch<AnyAction>) {
                            inst.notify(dependency);
                            mv[dependency.fieldName] = value;

                            if(type === StoreTypes.FormState) {
                                let type = inst.schema.models[dependency.modelName][dependency.fieldName].type
                                let rawValue = revertDataStructure(value as any, getValueSelector(StoreTypes.FormState));
                                let v = type.toModelValue(rawValue);
                                override.value[dependency.fieldName] = v;
                            }
                        }
                    })(fv);
                }

                initialize(state: any): DataHandle<M, F> {
                    return this.createDummyHandle();
                }
                hook(): DataHandle<M, F> {
                    let [s, us] = useState({});
                    inst.addNotify(dependency, () => us({}))
                    return this.createDummyHandle();
                }
            })();
        }

        return this.parent.createHandle(dependency, type);
    }

    createModelHandle<M, F>(modelName: string, type: StoreType<M, F>): EmptyModelHandle<M, ModelHandle<M>> {
        let override = this.overrides.find(a => a.fake === modelName);
        if(override === undefined) {
            return this.parent.createModelHandle(modelName, type);
        }
        let mv = (type === StoreTypes.Models ? override.value : override.formValue) as M;
        return {
            initialize: (state: any) => {
                return new ModelHandle(mv);
            },
            hook: () => {
                return new ModelHandle(mv);
            }
        }
    }
}
