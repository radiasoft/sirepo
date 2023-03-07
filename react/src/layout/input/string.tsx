import React, { ChangeEventHandler, FunctionComponent } from 'react';
import { Form } from 'react-bootstrap';
import { interpolate } from '../../utility/string';
import { AlignmentClass, InputComponentProps, InputConfigBase, InputLayout } from './input';

export type StringInputConfig = {
    align: AlignmentClass,
    valid?: string
} & InputConfigBase

export class StringInputLayout extends InputLayout<StringInputConfig, string> {
    component: FunctionComponent<InputComponentProps<string>> = (props) => {
        let onChange: ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = (event) => {
            props.onChange(event.target.value);
        }
        return <Form.Control size="sm" className={this.config.align} type="text" {...props} onChange={onChange}></Form.Control>
    }

    validate = (value: string) => {
        let v = (!this.config.isRequired) || (this.hasValue(value) && value.length > 0);
        if (this.config.valid) {
            return v && interpolate(this.config.valid).withValues({ value }).evaluated();
        }
        return v;
    }

    toModelValue: (value: string) => string = (v) => v;
    fromModelValue: (value: string) => string = (v) => v;
}
