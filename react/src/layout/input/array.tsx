import { FunctionComponent } from "react";
import { Schema } from "../../utility/schema";
import { InputConfigBase, InputLayout, InputComponentProps } from "./input";

export type ArrayInputConfig = {
    itemType: string,
    itemCount?: number,
    exportAsString: boolean
} & InputConfigBase

// TODO: garsuga, implement
export class ArrayInputLayout<V, M> extends InputLayout<ArrayInputConfig, V, M> {

    constructor(config: ArrayInputConfig, schema: Schema) {
        super(config);

        let baseType = schema.types[config.itemType];
        if(!baseType) {
            throw new Error(`could not find base type=${config.itemType} for arraylike input`)
        }

        
    }

    toModelValue: (value: V) => M = (value) => {
        
    }

    fromModelValue: (value: M) => V = (value) => {
        
    };

    validate: (value: V) => boolean = (value) => {
        return true;
    };

    component: FunctionComponent<InputComponentProps<V>> = (props) => {
        
    }
}


export function LayoutForArrayLike(name: string, schema: Schema) {
    let p = /(\w+?)(\d+)?(String)?(Array)/g;
    let [_, type, count, isString, isArray] = p.exec(name);
    if(isArray !== undefined) {

    }
    return undefined;
}
