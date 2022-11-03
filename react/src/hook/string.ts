import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";
import { AbstractModelsWrapper } from "../data/wrapper";

export function useInterpolatedString(models, str) {
    // need to convert values to strings
    return interpolateString(models, str, v => `${v}`);
}

function interpolateString<M, F>(models: AbstractModelsWrapper<M, F>, str: string, conversionFn?: (v: F) => any): string {
    let matches = [...str.matchAll(/\$\(([^\%]+?)\)/g)];
    let mappingsArr = matches.map(([originalString, mappedGroup]) => {
        return {
            original: originalString,
            dependency: new Dependency(mappedGroup)
        }
    });

    let dependencies = mappingsArr.map(v => v.dependency);
    let accessor = new ModelsAccessor(models, dependencies);

    let interpolatedStr = str;

    mappingsArr.map(mapping => {
        return {
            ...mapping,
            value: accessor.getFieldValue(mapping.dependency)
        }
    }).forEach(({ original, value }) => {
        interpolatedStr = interpolatedStr.replace(original, `${conversionFn ? conversionFn(value) : value}`);
    })

    return interpolatedStr;
}

export function useEvaluatedInterpString(models, str) {
    // need to JSON stringify values, strings must be quoted and arrays must be recursively stringified
    let interpStr = interpolateString(models, str, v => JSON.stringify(v));
    return eval(interpStr);
}
