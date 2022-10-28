import { createSlice, Slice } from '@reduxjs/toolkit';

export type ModelState = {
    [fieldName: string]: any
}

export type ModelStateUpdate = {
    name: string, // TODO rename to modelName
    value: ModelState
}

export type ModelStates = {[modelName: string]: ModelState}

export type ModelsStoreState = {
    isLoaded: boolean,
    models: ModelStates
}

export const modelsSlice: Slice<ModelsStoreState> = createSlice({
    name: 'modelsSlice',
    initialState: {
        isLoaded: false,
        models: {},
    },
    reducers: {
        updateModel: (state, {payload: {name, value}}: { payload: ModelStateUpdate }) => {
            state.models[name] = value;
        },
    }
});

export const { updateModel } = modelsSlice.actions;

export const selectIsLoaded: (state: any) => boolean = (state: any) => {
    return state[modelsSlice.name].isLoaded;
}

export const selectModels: (state: any) => ModelStates = (state: any) => {
    return state[modelsSlice.name].models;
}

export const selectModel: (state: any) => ModelState = (name: string) => {
    return (state: ModelsStoreState) => state[modelsSlice.name].models[name];
}
