import { ArrayFieldState, makeSlice } from "./common"

export type FormFieldState<T> = {
    valid: boolean,
    value: T | ArrayFieldState<FormModelState>,
    touched: boolean
}

export type FormModelState = { 
    [fieldName: string]: FormFieldState<any>
}

export const {
    slice: formStatesSlice,
    actions: formActions,
    selectors: formSelectors
} = makeSlice<FormModelState>("formState");
