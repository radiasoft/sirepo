import { useEvaluatedInterpString } from "./string"

export function useShown(shownConfig, defaultValue, modelsWrapper) {
    let evalInterpStrFn = useEvaluatedInterpString;
    if(shownConfig) {
        let shown = evalInterpStrFn(modelsWrapper, shownConfig);
        if(typeof(shown) !== 'boolean'){
            throw new Error(`'shown' function did not evaluate to a boolean "${shownConfig}" -> ${shown}`)
        }
        return shown;
    }
    return defaultValue;
}
