import React, { FunctionComponent } from "react";
import { Dependency } from "../../data/dependency";
import { useRenderCount } from "../../hook/debug";
import { InputComponentProps } from "../../layout/input/input";
import { FormFieldState } from "../../store/formState";
import { FormField } from "./form";

export type FieldProps<T> = {
    value: FormFieldState<T>,
    updateField: (value: T) => void,
    dependency: Dependency,
    inputComponent: FunctionComponent<InputComponentProps<T>>
}

export type LabeledFieldProps<T> = {
    displayName: string,
    description: string
} & FieldProps<T>

export function FieldInput<T>(props: FieldProps<T>) {
    let { value, updateField, inputComponent, dependency } = props;

    const onChange = (nextValue: T) => {
        console.log("field input onChange");
        console.log("field.value.value", value.value);
        console.log("nextValue", nextValue);
        if (value.value !== nextValue) { // TODO fix field.value.value naming
            console.log("field value mismatch, updating");
            updateField(nextValue);
        }
    }
    let InputComponent = inputComponent;
    return (
         <InputComponent
            dependency={dependency}
            valid={value.valid}
            touched={value.touched}
            value={value.value}
            onChange={onChange}
            />
    )
}

export function LabeledFieldInput(props: LabeledFieldProps<unknown>) {
    let { value, updateField, dependency, inputComponent, displayName, description, ...passedProps } = props;

    return (
        <FormField {...passedProps} label={displayName} tooltip={description} key={dependency.fieldName}>
            <FieldInput value={value} dependency={dependency} inputComponent={inputComponent} updateField={updateField}></FieldInput>
        </FormField>
    )
}
