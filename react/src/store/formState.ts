import { ActionCreatorWithPayload, createSlice, Slice } from '@reduxjs/toolkit';

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

export let formStatesSlice: Slice<{
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

export type FormSelectors = {
    selectFormState: (name: string) => ((state: any) => FormState)
}

export let formSelectors: FormSelectors = {
    selectFormState: (name: string) => (state) => state[formStatesSlice.name][name]
}

let { updateFormState, updateFormFieldState } = formStatesSlice.actions;

export type FormActions = {
    updateFormState: ActionCreatorWithPayload<FormStateUpdate>,
    updateFormFieldState: ActionCreatorWithPayload<FormFieldStateUpdate<unknown>>
}
export let formActions: FormActions = {
    updateFormState,
    updateFormFieldState
}
