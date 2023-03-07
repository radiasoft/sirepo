import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";
import { AbstractModelsWrapper } from "../data/wrapper";
import { FormFieldState } from "../store/formState";

export type ValueSelector<T> = (v: T) => any;

export const ValueSelectors = {
    Models: (v: any) => v,
    Fields: (v: FormFieldState<unknown>) => v.value
}

export function interpolateStringDependencies<M, F>(str: string, modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: ValueSelector<F>) {
    // need to convert values to strings
    return _interpolateStringDependencies(str, modelsWrapper, valueSelector, v => `${v}`);
}

function getStringReplacementPatterns(str: string): RegExpMatchArray[] {
    return [...str.matchAll(/\$\(([^\%]+?)\)/g)];
}

function _interpolateString<F>(str: string, mappingFunction: (v: string) => F, valueSerializer: (v: F) => string): string {
    let matches = getStringReplacementPatterns(str);
    let mappingsArr = matches.map(([originalString, mappedGroup]) => {
        return {
            original: originalString,
            value: mappingFunction(mappedGroup)
        }
    });

    let interpolatedStr = str;

    mappingsArr.forEach(({ original, value }) => {
        interpolatedStr = interpolatedStr.replace(original, `${valueSerializer(value)}`);
    })

    return interpolatedStr;
}

function _interpolateStringDependencies<M, F>(str: string, modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: ValueSelector<F>, valueSerializer: (v: F) => string) {
    let matches = getStringReplacementPatterns(str);

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
        interpolatedStr = interpolatedStr.replace(original, `${valueSerializer(value)}`);
    })

    return interpolatedStr;
}

export function evaluateInterpStringDependencies<M, F> (str: string, modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: ValueSelector<F>) {
    // need to JSON stringify values, strings must be quoted and arrays must be recursively stringified
    let interpStr = _interpolateStringDependencies(str, modelsWrapper, valueSelector, v => JSON.stringify(v));
    return eval(interpStr);
}

export function evaluateInterpString<M, F> (str: string, values: {[key: string]: any}) {
    let valueSelector = (v: string) => values[v];
    // need to JSON stringify values, strings must be quoted and arrays must be recursively stringified
    let interpStr = _interpolateString(str, valueSelector, v => JSON.stringify(v));
    return eval(interpStr);
}

export function titleCaseString(str: string): string {
    return str.split(" ").map(word => {
        return word.substring(0,1).toUpperCase() + (word.length > 1 ? word.substring(1) : "");
    }).join(" ");
}
