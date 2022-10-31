import { createSlice } from '@reduxjs/toolkit';

export const formStatesSlice = createSlice({
    name: 'formStates',
    initialState: {},
    reducers: {
        updateFormState: (state, {payload: {name, value}}) => {
            state[name] = value;
        },
        updateFormFieldState: (state, {payload: {name, value, field}}) => {
            state[name] = {...state[name]};
            state[name][field] = value;
        }
    }
});

export const selectFormState = (name) => (state) => state[formStatesSlice.name][name] || null;

export const { updateFormState, updateFormFieldState } = formStatesSlice.actions;
