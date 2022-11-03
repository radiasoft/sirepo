import { useEvaluatedInterpString } from "./string"

export const ValueSelector = {
    Models: (models, modelName, fieldName) => models[modelName][fieldName],
    Fields: (models, modelName, fieldName) => models[modelName][fieldName].value
}

export function useShown(shownConfig, defaultValue, modelsWrapper, valueSelector) {
    let evalInterpStrFn = useEvaluatedInterpString;
    if(shownConfig) {
        let shown = evalInterpStrFn(modelsWrapper, shownConfig, valueSelector);
        if(typeof(shown) !== 'boolean'){
            throw new Error(`'shown' function did not evaluate to a boolean "${shownConfig}" -> ${shown}`)
        }
        return shown;
    }
    return defaultValue;
}
