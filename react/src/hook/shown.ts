import { AbstractModelsWrapper } from "../data/wrapper";
import { FormFieldState } from "../store/formState";
import { useEvaluatedInterpString } from "./string"

export function useShown<M, F>(shownStr: string, defaultValue: boolean, modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: (v: F) => any) {
    let evalInterpStrFn = useEvaluatedInterpString;
    if(shownStr) {
        let shown = evalInterpStrFn(modelsWrapper, shownStr, valueSelector);
        if(typeof(shown) !== 'boolean'){
            throw new Error(`'shown' function did not evaluate to a boolean "${shownStr}" -> ${shown}`)
        }
        return shown;
    }
    return defaultValue;
}
