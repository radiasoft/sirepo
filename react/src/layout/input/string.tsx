import React, { ChangeEventHandler, FunctionComponent } from 'react';
import { Form } from 'react-bootstrap';
import { AlignmentClass, InputComponentProps, InputConfigBase, InputLayout } from './input';

export type StringInputConfig = {
    align: AlignmentClass
} & InputConfigBase

export class StringInputLayout extends InputLayout<StringInputConfig, string> { 
    component: FunctionComponent<InputComponentProps<string>> = (props) => {
        let onChange: ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = (event) => {
            props.onChange(this.toModelValue(event.target.value));
        }

        let newProps = {
            ...props,
            onChange,
            value: this.fromModelValue(props.value)
        }
        
        return <Form.Control className={this.config.align} type="text" {...newProps}></Form.Control>
    }

    validate = (value: string) => {
        return (!this.config.isRequired) || (this.hasValue(value) && value.length > 0);
    }

    toModelValue: (value: string) => string = (v) => v;
    fromModelValue: (value: string) => string = (v) => v;   
}
