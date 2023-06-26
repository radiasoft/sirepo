import { ActionCreatorWithPayload, createSlice, Slice } from "@reduxjs/toolkit";

export type ModelStateUpdate<V> = {
    name: string,
    value: V
}

export type ModelSelector<V> = (name: string) => (state: any) => V;

export type ModelWriteActionCreator<V> = ActionCreatorWithPayload<ModelStateUpdate<V>, string>;

export type ArrayFieldElement<V> = {
    model: string,
    item: V
}

export type ArrayFieldState<V> = ArrayFieldElement<V>[]

export type StoreActions<M> = {
    updateModel: ModelWriteActionCreator<M>;
}

export type StoreSelectors<M> = {
    selectModel: ModelSelector<M>,
    selectModelNames: () => ((state: any) => string[])
}

export type StoreState<M> = {
    [key: string]: M
}

export const makeSlice = <M>(sliceName: string): {
    slice: Slice<StoreState<M>>,
    actions: StoreActions<M>,
    selectors: StoreSelectors<M>
} => {
    let slice: Slice<StoreState<M>> = createSlice({
        name: sliceName,
        initialState: {},
        reducers: {
            updateModel: (state, {payload: {name, value}}: {payload: ModelStateUpdate<M>}) => {
                (state[name] as any) = value;
            }
        }
    });
    
    let selectors: StoreSelectors<M> = {
        selectModel: (name: string) => (state) => state[slice.name][name],
        selectModelNames: () => {
            return (state: any) => Object.keys(state[slice.name]);
        }
    }
    
    let { updateModel } = slice.actions;
    let actions: StoreActions<M> = {
        updateModel
    }

    return {
        slice,
        actions,
        selectors
    }
}
