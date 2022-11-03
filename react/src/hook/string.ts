import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";
import { AbstractModelsWrapper } from "../data/wrapper";
import { FormFieldState } from "../store/formState";

export type ValueSelector<T> = (v: T) => any;

export const ValueSelectors = {
    Models: (v: any) => v,
    Fields: (v: FormFieldState<unknown>) => v.value
}

export function useInterpolatedString<M, F>(modelsWrapper: AbstractModelsWrapper<M, F>, str: string, valueSelector: ValueSelector<F>) {
    // need to convert values to strings
    return interpolateString(modelsWrapper, str, v => `${v}`, valueSelector);
}

function interpolateString<M, F>(modelsWrapper: AbstractModelsWrapper<M, F>, str: string, conversionFn: (v: F) => any, valueSelector: ValueSelector<F>) {
    let matches = [...str.matchAll(/\$\(([^\%]+?)\)/g)];
    let mappingsArr = matches.map(([originalString, mappedGroup]) => {
        return {
            original: originalString,
            dependency: new Dependency(mappedGroup)
        }
    });

    let modelAccessor = new ModelsAccessor(modelsWrapper, mappingsArr.map(v => v.dependency));

    let interpolatedStr = str;

    mappingsArr.map(mapping => {
        return {
            ...mapping,
            value: (valueSelector)(modelAccessor.getFieldValue(mapping.dependency))
        }
    }).forEach(({ original, value }) => {
        interpolatedStr = interpolatedStr.replace(original, `${conversionFn(value)}`);
    })

    return interpolatedStr;
}

export function useEvaluatedInterpString<M, F>(modelsWrapper: AbstractModelsWrapper<M, F>, str: string, valueSelector: ValueSelector<F>) {
    // need to JSON stringify values, strings must be quoted and arrays must be recursively stringified
    let interpStr = interpolateString(modelsWrapper, str, v => JSON.stringify(v), valueSelector);
    return eval(interpStr);
}
