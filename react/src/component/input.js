import { useRenderCount } from "../hook/debug";
import { FormField } from "./form";

export function FieldInput(props) {
    let { field } = props;

    useRenderCount("FieldInput");

    const onChange = (event) => {
        console.log("field input onChange");
        let nextValue = event.target.value;
        console.log("field.value.value", field.value.value);
        console.log("nextValue", nextValue);
        if (field.value.value !== nextValue) { // TODO fix field.value.value naming
            console.log("field value mismatch, updating");
            field.updateValue(nextValue);
        }
    }
    let InputComponent = field.dependency.type.component;
    return (
         <InputComponent
            dependency={field.dependency}
            valid={field.value.valid}
            touched={field.value.touched}
            value={field.value.value}
            onChange={onChange}
            />
    )
}

export function LabeledFieldInput(props) {
    let { field, ...passedProps } = props;

    useRenderCount("LabeledFieldInput");

    return (
        <FormField {...passedProps} label={field.dependency.displayName} tooltip={field.dependency.description} key={field.dependency.fieldName}>
            <FieldInput field={field}></FieldInput>
        </FormField>
    )
}
