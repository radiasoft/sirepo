import { Dispatch, AnyAction } from "redux";
import { ArrayFieldState, StoreState } from "../store/common";
import { Schema } from "../utility/schema";
import { getValueSelector, StoreType } from "./data";
import { Dependency } from "./dependency";
import { DataHandle, EmptyDataHandle, HandleFactory } from "./handle";
import cloneDeep from 'lodash/cloneDeep';

export type ArrayAliases = {
    realDataLocation: {
        modelName: string,
        fieldName: string,
        index: number
    },
    realSchemaName: string,
    fake: string
}[]

export class HandleFactoryWithArrayAliases extends HandleFactory {
    constructor(schema: Schema, private aliases: ArrayAliases, public parent: HandleFactory) {
        super(schema, parent);
    }

    createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F, DataHandle<M, F>> {
        console.log("creating aliased handle");
        let alias = this.aliases.find(a => a.fake === dependency.modelName);
        console.log("alias", alias);
        if(alias !== undefined) {
            let edh = this.parent.createHandle(new Dependency(`${alias.realDataLocation.modelName}.${alias.realDataLocation.fieldName}`), type);
            return new (class implements EmptyDataHandle<M, F> {
                private createDummyHandle(dh: DataHandle<M, F>): DataHandle<M, F> {
                    let mv = getValueSelector(type)(dh.value)[alias.realDataLocation.index];
                    console.log("array element value", mv);
                    let fv = mv.item[dependency.fieldName];
                    console.log("array element field value", fv);
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
}
