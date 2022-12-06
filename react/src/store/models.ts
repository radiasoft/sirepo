import { ActionCreatorWithPayload, createSlice, Slice } from '@reduxjs/toolkit';

export type ModelState = {
    [fieldName: string]: unknown
}

export type ModelStateUpdate = {
    name: string, // TODO rename to modelName
    value: ModelState
}

export type ModelStates = {[modelName: string]: ModelState}

export const modelsSlice: Slice<ModelStates> = createSlice({
    name: 'modelsSlice',
    initialState: {},
    reducers: {
        updateModel: (state, {payload: {name, value}}: { payload: ModelStateUpdate }) => {
            state[name] = value;
        },
    }
});

let { updateModel } = modelsSlice.actions;

export type ModelActions = {
    updateModel: ActionCreatorWithPayload<ModelStateUpdate>
}
export let modelActions: ModelActions = {
    updateModel
}

export type ModelSelectors = {
    selectModel: (name: string) => ((state: any) => ModelState)
}
export let modelSelectors: ModelSelectors = {
    selectModel: (name: string) => {
        return (state: any) => state[modelsSlice.name][name];
    }
}
