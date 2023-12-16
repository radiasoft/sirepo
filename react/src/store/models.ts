import { ArrayFieldState, makeSlice } from './common';

export type ModelState = {
    [fieldName: string]: unknown | ArrayFieldState<ModelState>
}

export const {
    slice: modelsSlice,
    actions: modelActions,
    selectors: modelSelectors
} = makeSlice<ModelState>("models");
