import { AbstractModelsWrapper } from "../data/wrapper";
import { interpolate, ValueSelector } from "../utility/string"

export function useShown<M, F>(shownStr: string, defaultValue: boolean, modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: ValueSelector<F>) {
    if(shownStr) {
        let shown = interpolate(shownStr).withDependencies(modelsWrapper, valueSelector).evaluated();
        if(typeof(shown) !== 'boolean'){
            throw new Error(`'shown' function did not evaluate to a boolean "${shownStr}" -> ${shown}`)
        }
        return shown;
    }
    return defaultValue;
}
