import React, { ChangeEventHandler, FunctionComponent } from "react";
import { Form } from "react-bootstrap";
import { interpolate } from "../../utility/string";
import { LayoutProps } from "../layout";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";

export type NumberConfigBase = {
    valid?: string
} & InputConfigBase

export abstract class NumberInputLayout extends InputLayout<NumberConfigBase, string, number> {
    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        let onChange: ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = (event) => {
            props.onChange(event.target.value);
        }
        return <Form.Control size="sm" className={'text-end'} type="text" {...props} onChange={onChange}></Form.Control>
    };
}

export class FloatInputLayout extends NumberInputLayout {
    static REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;
    toModelValue = (value: string) => {
        return Number.parseFloat(value);
    }
    fromModelValue = (value: number) => {
        if (Math.abs(value) >= 10000 || (value != 0 && Math.abs(value) < 0.001)) {
            return value.toExponential(9).replace(/\.?0+e/, 'e');
        }
        return `${value}`;
    }
    validate = (value: string) => {
        let v = (!this.config.isRequired) || (this.hasValue(value) && FloatInputLayout.REGEXP.test(value));
        if(this.config.valid) {
            return v && interpolate(this.config.valid).withValues({ value }).evaluated();
        }
        return v;
    }
}

export class IntegerInputLayout extends NumberInputLayout {
    static REGEXP = /^[-+]?\d+$/;
    toModelValue = (value: string) => {
        return Number.parseInt(value);
    }
    fromModelValue: (value: number) => string = (v) => `${v}`;
    validate = (value: string) => {
        let v = (!this.config.isRequired) || (this.hasValue(value) && IntegerInputLayout.REGEXP.test(value));
        if(this.config.valid) {
            return v && interpolate(this.config.valid).withValues({ value }).evaluated();
        }
        return v;
    }
}
