import { createSlice, Slice } from '@reduxjs/toolkit';

export type FormFieldState<T> = {
    valid: boolean,
    value: T,
    touched: boolean,
    active: boolean
}

export type FormState = { 
    [fieldName: string]: FormFieldState<any>
}

export type FormStateUpdate = {
    name: string, // TODO rename to modelName
    value: FormState
}

export type FormFieldStateUpdate<T> = {
    name: string, // TODO rename to modelName
    field: string, // TODO rename to fieldName
    value: FormFieldState<T>
}

export const formStatesSlice: Slice<{
    [modelName: string]: FormState
}> = createSlice({
    name: 'formStates',
    initialState: {},
    reducers: {
        updateFormState: (state, {payload: {name, value}}: {payload: FormStateUpdate}) => {
            state[name] = value;
        },
        updateFormFieldState: (state, {payload: {name, value, field}}: {payload: FormFieldStateUpdate<any>}) => {
            state[name] = {...state[name]};
            state[name][field] = value;
        }
    }
});

export type SelectFormState = (name: string) => ((state: any) => FormState);
export const selectFormState: SelectFormState = (name: string) => (state) => state[formStatesSlice.name][name];

export const { updateFormState, updateFormFieldState } = formStatesSlice.actions;
