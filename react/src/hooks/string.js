export function useInterpolatedString(models, str) {
    let mappingsArr = str.matchAll(/\$\(([^\%]+)\)/g).map(([originalString, mappedGroup]) => {
        return {
            original: originalString,
            dependency: new Dependency(mappedGroup)
        }
    });

    let modelNames = [...new Set(mappingsArr.map(mapping => mapping.modelName))];

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
            value: modelValues[modelName][fieldName]
        }
    }).forEach(({ original, value }) => {
        interpolatedStr = interpolatedStr.replace(original, `${value}`);
    })

    return interpolatedStr;
}
