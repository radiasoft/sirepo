import { Dispatch, AnyAction } from "redux";
import { ArrayFieldState, StoreState } from "../store/common";
import { Schema } from "../utility/schema";
import { getValueSelector, StoreType } from "./data";
import { Dependency } from "./dependency";
import { DataHandle, EmptyDataHandle, HandleFactory } from "./handle";

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
    constructor(schema: Schema, private aliases: ArrayAliases, private parent: HandleFactory) {
        super(schema);
    }

    createHandle<M, F>(dependency: Dependency, type: StoreType<M, F>): EmptyDataHandle<M, F, DataHandle<M, F>> {
        let alias = this.aliases.find(a => a.fake === dependency.modelName);
        if(alias !== undefined) {
            let edh = this.parent.createHandle(new Dependency(`${alias.realDataLocation.modelName}.${alias.realDataLocation.fieldName}`), type);
            return new (class implements EmptyDataHandle<M, F> {
                private createDummyHandle(dh: DataHandle<M, F>): DataHandle<M, F> {
                    let mv = getValueSelector(type)(dh.value)[alias.realDataLocation.index];
                    let fv = mv[dependency.fieldName];
                    return new (class extends DataHandle<M, F> {
                        write(value: F, state: StoreState<M>, dispatch: Dispatch<AnyAction>) {
                            let av = getValueSelector(type)(dh.value) as ArrayFieldState<M>;
                            av[alias.realDataLocation.index][dependency.fieldName] = value;
                            dh.write(dh.value, state, dispatch);
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
