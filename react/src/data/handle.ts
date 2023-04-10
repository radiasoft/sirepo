import React from "react";
import { useSelector, useStore } from "react-redux";
import { AnyAction, Dispatch } from "redux";
import { StoreState } from "../store/common";
import { ModelState } from "../store/models";
import { Schema } from "../utility/schema";
import { getModelReadSelector, getModelWriteActionCreator, getValueSelector, StoreType, StoreTypes } from "./data";
import { Dependency } from "./dependency";

export const CHandleFactory = React.createContext<HandleFactory>(undefined);

export abstract class DataHandle<M, F> {
    constructor(protected currentValue: F) {
        this.value = currentValue;
    }

    abstract write(value: F, state: StoreState<M>, dispatch: Dispatch<AnyAction>);
    readonly value: F; 
}

export interface EmptyDataHandle<M, F, D extends DataHandle<M, F> = DataHandle<M, F>> {
    /**
     * use the current state to populate the data in the handle without subscribing to updates
     * @param state current state
     */
    initialize(state: any): D;
    /**
     * create handle using selector hooks, subscribes to data updates where these hooks are called
     */
    hook(): D;
}

export type SelectorUser = <M>(selector: (state: any) => M) => M;

export abstract class HandleFactory {
    constructor(protected schema: Schema) {}
    abstract createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F>;
    //abstract createArrayHandle<F>(dependency: Dependency, type: StoreType<any, F>): EmptyDataHandle<F>;
}

export class BaseHandleFactory extends HandleFactory {
    createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F> {
        let ms = getModelReadSelector(type)(dependency.modelName);
        let mac = getModelWriteActionCreator(type);
        let cdh = (value: F): DataHandle<M, F> => {
            return new (class extends DataHandle<M, F> {
                write = (value: F, state: StoreState<M>, dispatch: Dispatch<AnyAction>) => {
                    let mv = {...state[type.name][dependency.modelName]};
                    mv[dependency.fieldName] = value;
                    dispatch(mac(dependency.modelName, mv));
                }
            })(value);
        }
        return {
            initialize: (state: any) => {
                return cdh(ms(state)[dependency.fieldName]);
            },
            hook: () => {
                return cdh(useSelector(ms)[dependency.fieldName]);
            }
        }
    }
}

export type DependencyValuePair<V> = {
    dependency: Dependency,
    value: V
};

/**
 * Read-only alternative to handles that supports wildcards
 */
export class DependencyReader<F> {
    constructor(private dependencies: Dependency[], private type: StoreType<any, F>, private schema: Schema) {
        
    }

    private expandWildcard(dependency: Dependency): Dependency[] {
        if(dependency.fieldName === `*`) {
            return Object.keys(this.schema.models[dependency.fieldName]).map(fName => new Dependency(`${dependency.modelName}.${fName}`));
        }
        return [dependency];
    }

    hook = (): DependencyValuePair<F>[] => {
        let vs = getValueSelector(this.type);
        let newDeps = this.dependencies.flatMap(d => this.expandWildcard(d));

        return newDeps.map(d => {
            let c = (d: Dependency) => {
                let ms = getModelReadSelector(this.type)(d.modelName);
                return useSelector(ms)[d.fieldName];
            }

            return {
                value: vs(c(d)),
                dependency: d
            }
        })
    }

    initialize = (state: any): DependencyValuePair<F>[] => {
        let vs = getValueSelector(this.type);
        let newDeps = this.dependencies.flatMap(d => this.expandWildcard(d));

        return newDeps.map(d => {
            let c = (d: Dependency) => {
                let ms = getModelReadSelector(this.type)(d.modelName);
                return ms(state)[d.fieldName];
            }

            return {
                value: vs(c(d)),
                dependency: d
            }
        })
    }
}


export function useModelValue<M, F>(modelName: string, type: StoreType<M, F>): M {
    let ms = getModelReadSelector(type);
    return useSelector(ms(modelName))

    /*return Object.fromEntries(new DependencyReader([new Dependency(`${modelName}.*`)], StoreTypes.Models, schema).hook().map(pair => {
        return [
            pair.dependency.fieldName,
            pair.value
        ]
    }));*/


}
