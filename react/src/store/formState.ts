import { ActionCreatorWithPayload, createSlice, Slice } from '@reduxjs/toolkit';

export type FormFieldState<T> = {
    valid: boolean,
    value: T,
    touched: boolean,
    active: boolean
}

export type FormModelState = { 
    [fieldName: string]: FormFieldState<any>
}

export type FormStateUpdate = {
    name: string, // TODO rename to modelName
    value: FormModelState
}

export let formStatesSlice: Slice<{
    [modelName: string]: FormModelState
}> = createSlice({
    name: 'formStates',
    initialState: {},
    reducers: {
        updateFormState: (state, {payload: {name, value}}: {payload: FormStateUpdate}) => {
            state[name] = value;
        }
    }
});

export type FormSelectors = {
    selectFormState: (name: string) => ((state: any) => FormModelState)
}

export let formSelectors: FormSelectors = {
    selectFormState: (name: string) => (state) => state[formStatesSlice.name][name]
}

let { updateFormState } = formStatesSlice.actions;

export type FormActions = {
    updateFormState: ActionCreatorWithPayload<FormStateUpdate>,
}
export let formActions: FormActions = {
    updateFormState
}
