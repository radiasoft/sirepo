import { createSlice } from '@reduxjs/toolkit';


export const modelsSlice = createSlice({
    name: 'modelsSlice',
    initialState: {
        isLoaded: false,
        models: {},
    },
    reducers: {
        updateModel: (state, {payload: {name, value}}) => {
            //state.models[action.payload.name] = cloneDeep(action.payload.value);
            state.models[name] = value;
        },
    },
    /*extraReducers: (builder) => {
        builder
            .addCase(loadModelData.fulfilled, (state, {payload}) => {
                state.models = payload;
                state.isLoaded = true;
            });
    },*/
});

//export const { cancelChanges, saveChanges, updateField } = modelsSlice.actions;
export const { updateModel } = modelsSlice.actions;

export const selectIsLoaded = (state) => {
    return state[modelsSlice.name].isLoaded;
}

export const selectModels = state => {
    return state[modelsSlice.name].models;
}

export const selectModel = name => {
    return state => state[modelsSlice.name].models[name];
}
