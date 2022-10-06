import { Dependency } from "../data/dependency";

const defaultValueSelector = (models, modelName, fieldName) => models[modelName][fieldName];

export function useInterpolatedString(models, str, valueSelector) {
    // need to convert values to strings
    return interpolateString(models, str, v => `${v}`, valueSelector);
}

function interpolateString(models, str, conversionFn, valueSelector) {
    let matches = [...str.matchAll(/\$\(([^\%]+?)\)/g)];
    let mappingsArr = matches.map(([originalString, mappedGroup]) => {
        return {
            original: originalString,
            dependency: new Dependency(mappedGroup)
        }
    });

    let modelNames = [...new Set(mappingsArr.map(mapping => mapping.dependency.modelName))];

    let modelValues = Object.fromEntries(modelNames.map(modelName => {
        return [
            modelName,
            models.hookModel(modelName)
        ]
    }));

    let interpolatedStr = str;

    mappingsArr.map(mapping => {
        let { modelName, fieldName } = mapping.dependency; 
        return {
            ...mapping,
            value: (valueSelector || defaultValueSelector)(modelValues, modelName, fieldName)
        }
    }).forEach(({ original, value }) => {
        interpolatedStr = interpolatedStr.replace(original, `${conversionFn(value)}`);
    })

    return interpolatedStr;
}

export function useEvaluatedInterpString(models, str, valueSelector) {
    // need to JSON stringify values, strings must be quoted and arrays must be recursively stringified
    let interpStr = interpolateString(models, str, v => JSON.stringify(v), valueSelector);
    return eval(interpStr);
}
