import React from "react";
import { useSelector } from "react-redux";
import { AnyAction, Dispatch } from "redux";
import { StoreState } from "../store/common";
import { Schema } from "../utility/schema";
import { getModelReadSelector, getModelWriteActionCreator, getValueSelector, StoreType } from "./data";
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

    hook = (): any[] => {
        let vs = getValueSelector(this.type);
        return this.dependencies.flatMap(d => {
            let c = (d: Dependency) => {
                let ms = getModelReadSelector(this.type)(d.modelName);
                return useSelector(ms)[d.fieldName];
            }

            return this.expandWildcard(d).map(d => vs(c(d)));
        })
    }

    initialize = (state: any): any[] => {
        let vs = getValueSelector(this.type);
        return this.dependencies.flatMap(d => {
            let c = (d: Dependency) => {
                let ms = getModelReadSelector(this.type)(d.modelName);
                return ms(state)[d.fieldName];
            }

            return this.expandWildcard(d).map(d => vs(c(d)));
        })
    }
}
