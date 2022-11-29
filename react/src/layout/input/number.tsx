import React, { ChangeEventHandler, FunctionComponent } from "react";
import { Form } from "react-bootstrap";
import { LayoutProps } from "../layout";
import { AlignmentClass, InputComponentProps, InputConfigBase, InputLayout } from "./input";

export type NumberInputConfig = {
    align: AlignmentClass
} & InputConfigBase

export abstract class NumberInputLayout extends InputLayout<NumberInputConfig, string, number> {
    component: FunctionComponent<LayoutProps<InputComponentProps<string>>> = (props) => {
        let onChange: ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = (event) => {
            props.onChange(event.target.value);
        }

        let { valid, touched, ...otherProps } = props;

        return <Form.Control className={this.config.align} type="text" {...otherProps} onChange={onChange} isInvalid={!valid && touched}></Form.Control>
    };
}

export class FloatInputLayout extends NumberInputLayout {
    static REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;
    toModelValue = (value: string) => {
        return Number.parseFloat(value);
    }
    fromModelValue: (value: number) => string = (v) => `${v}`;
    validate = (value: string) => {
        return (!this.config.isRequired) || (this.hasValue(value) && FloatInputLayout.REGEXP.test(value));
    }
}

export class IntegerInputLayout extends NumberInputLayout {
    static REGEXP = /^[-+]?\d+$/;
    toModelValue = (value: string) => {
        return Number.parseInt(value);
    }
    fromModelValue: (value: number) => string = (v) => `${v}`;
    validate = (value: string) => {
        return (!this.config.isRequired) || (this.hasValue(value) && IntegerInputLayout.REGEXP.test(value));
    }
}


