import React from "react";
import { useSelector } from "react-redux";
import { AnyAction, Dispatch } from "redux";
import { Schema } from "../utility/schema";
import { hashCode } from "../utility/string";
import { getModelReadSelector, getModelWriteActionCreator, getValueSelector, revertDataStructure, StoreType } from "./data";
import { Dependency } from "./dependency";

export const CHandleFactory = React.createContext<HandleFactory>(undefined);

export abstract class DataHandle<M, F> {
    constructor(protected currentValue: F) {
        this.value = currentValue;
    }

    abstract write(value: F, state: any, dispatch: Dispatch<AnyAction>);
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
    constructor(protected schema: Schema, public parent?: HandleFactory) {}
    abstract createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F>;
}

export class BaseHandleFactory extends HandleFactory {
    createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F> {
        let ms = getModelReadSelector(type)(dependency.modelName);
        let mac = getModelWriteActionCreator(type);
        let cdh = (value: F): DataHandle<M, F> => {
            return new (class extends DataHandle<M, F> {
                write = (value: F, state: any, dispatch: Dispatch<AnyAction>) => {
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
                let mv = useSelector(ms);
                //console.log("dependency", dependency.getDependencyString(), mv);
                return cdh(mv[dependency.fieldName]);
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
            return Object.keys(this.schema.models[dependency.modelName]).map(fName => new Dependency(`${dependency.modelName}.${fName}`));
        }
        return [dependency];
    }

    private hashify = <T>(x: T): T | number => {
        if(typeof(x) == "object") {
            return hashCode(JSON.stringify(x));
        }
        return x;
    }

    getData = (su: SelectorUser): F[] => {
        let vs = getValueSelector(this.type);
        let newDeps = this.dependencies.flatMap(d => this.expandWildcard(d));
        return newDeps.map(d => {
            let c = (d: Dependency) => {
                let ms = getModelReadSelector(this.type)(d.modelName);
                return su(ms)[d.fieldName];
            }

            return this.hashify(revertDataStructure(c(d), vs));
        })
    } 

    hook = (): F[] => {
        return this.getData(s => useSelector(s));
    }

    initialize = (state: any): F[] => {
        return this.getData(s => s(state));
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
