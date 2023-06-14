import { range } from "lodash";
import React, { ChangeEventHandler, FunctionComponent } from "react";
import { Form } from "react-bootstrap";
import { InputConfigBase, InputLayout, InputComponentProps } from "./input";

export type ArrayInputConfig = {
    
} & InputConfigBase

// TODO: garsuga, implement
export class ArrayInputLayout extends InputLayout<ArrayInputConfig, any[], any[]> {

    constructor(config: ArrayInputConfig) {
        super(config);
    }

    toModelValue: (value: any[]) => any[] = (value) => {
        return value;
    }

    fromModelValue: (value: any[]) => any[] = (value) => {
        return value;
    };

    validate: (value: any[]) => boolean = (value) => {
        return true;
    };
}


export type ArrayLikeMultiInputConfig = {
    length: number,
    baseType: InputLayout<any, any, any>,
} & InputConfigBase
export class ArrayLikeMultiInputLayout extends InputLayout<ArrayLikeMultiInputConfig, string[], string> {
    toModelValue: (value: string[]) => string = (value) => {
        return (value || []).join(", ");
    };

    fromModelValue: (value: string) => string[] = (value) => {
        return value?.split(",")?.map(s => s.trim());
    };

    validate: (value: string[]) => boolean = (value) => {
        return !(value.map(v => this.config.baseType.validate(v)).includes(false));
    };
    
    component: FunctionComponent<InputComponentProps<string[]>> = (props) => {
        let onChange: (index: number) => (value: any) => void = (index: number) => (value) => {
            let nv = [...props.value];
            nv[index] = this.config.baseType.toModelValue(value);
            props.onChange(nv);
        }

        let Comp = this.config.baseType.component;
        
        return (
            <div className="d-flex flex-column flex-nowrap">
                {
                    range(0, this.config.length).map(idx => {
                        let v = props.value && props.value.length > idx ? props.value[idx] : undefined;
                        return (
                            <Comp value={v} dependency={undefined} onChange={onChange(idx)} isInvalid={this.config.baseType.validate(v)}/>
                        )
                    })
                }
            </div>
        )
    }
}

export type ArrayLikeInputConfig = {
    baseType: InputLayout<any, any, any>
} & InputConfigBase
export class ArrayLikeInputLayout extends InputLayout<ArrayLikeInputConfig, string, string> {
    toModelValue: (value: string) => string = (value) => {
        return value;
    };

    fromModelValue: (value: string) => string = (value) => {
        return value;
    };

    validate: (value: string) => boolean = (value) => {
        let vals = (value || "").split(" ");
        return !(vals.map(e => this.config.baseType.validate(e)).includes(false))
    };

    component: FunctionComponent<InputComponentProps<string>> = (props) => {
        let onChange: ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = (event) => {
            props.onChange(event.target.value);
        }
        return <Form.Control size="sm" type="text" {...props} onChange={onChange}></Form.Control>
    }
}


export function layoutForArrayLike(name: string, typeLookupCallback: (name: string) => InputLayout): InputLayout | undefined {
    let r = (/(\w+?)(\d+)?(String)?(Array)/g).exec(name);
    if(r === null || r === undefined) {
        return undefined;
    }
    let [_, type, count, isString, isArray] = r;
    if(isArray !== undefined) {
        let baseType = typeLookupCallback(type);
        if(!baseType) {
            throw new Error(`could not find base type=${type} for arraylike input`)
        }

        if(count !== undefined) {
            return new ArrayLikeMultiInputLayout({
                baseType,
                length: parseInt(count),
                isRequired: true
            });
        }
        return new ArrayLikeInputLayout({
            baseType,
            isRequired: true
        });
    }
    return undefined;
}
