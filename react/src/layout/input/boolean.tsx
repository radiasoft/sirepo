import React, { FunctionComponent } from "react";
import { Form } from "react-bootstrap";
import { LayoutProps } from "../layout";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";

export type BooleanModelType = "0" | "1";

export class BooleanInputLayout extends InputLayout<InputConfigBase, boolean, BooleanModelType> {
    constructor(config: InputConfigBase) {
        super(config);
    }

    toModelValue: (value: boolean) => BooleanModelType = (value) => {
        return (value === true) ? "1" : "0"; // TODO ???????? why arent these just booleans?
    }

    fromModelValue: (value: BooleanModelType) => boolean = (value) => {
        return value === "1";
    }

    validate = (value) => {
        return (!this.config.isRequired) || this.hasValue(value);
    }

    component: FunctionComponent<LayoutProps<InputComponentProps<BooleanModelType>>> = (props) => {
        let { value, onChange: _, ...otherProps } = props;

        let onChange = (event) => {
            let v: boolean = event.target.checked as boolean;
            props.onChange(this.toModelValue(v));
        }
        
        return <Form.Check {...otherProps} onChange={onChange} checked={this.fromModelValue(value)}></Form.Check>
    };
}
