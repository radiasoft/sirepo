import { AbstractModelsWrapper } from "../data/wrapper";
import { evaluateInterpStringDependencies, ValueSelector } from "../utility/string"

export function useShown<M, F>(shownStr: string, defaultValue: boolean, modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: ValueSelector<F>) {
    if(shownStr) {
        let shown = evaluateInterpStringDependencies(shownStr, modelsWrapper, valueSelector);
        if(typeof(shown) !== 'boolean'){
            throw new Error(`'shown' function did not evaluate to a boolean "${shownStr}" -> ${shown}`)
        }
        return shown;
    }
    return defaultValue;
}
