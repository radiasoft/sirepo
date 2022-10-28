export function useDependentValues(models, dependencies) {
    let modelNames = [...new Set(dependencies.map(dependency => dependency.modelName))];

    let modelValues = Object.fromEntries(modelNames.map(modelName => {
        return [
            modelName,
            models.hookModel(modelName)
        ]
    }))

    let dependentValues = dependencies.map(dependency => {
        let { modelName, fieldName } = dependency;
        let modelValue = modelValues[modelName];

        if(fieldName === '*') {
            return [
                ...Object.values(modelValue)
            ]
        }
        return [modelValue[fieldName]];
    }).flat();

    return dependentValues;
}
