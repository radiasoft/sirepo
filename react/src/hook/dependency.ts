import { Dependency } from "../data/dependency";
import { ModelsWrapper } from "../data/model";

export function useDependentValues(modelsWrapper: ModelsWrapper, dependencies: Dependency[]) {
    let modelNames = [...new Set(dependencies.map(dependency => dependency.modelName))];

    let modelValues = Object.fromEntries(modelNames.map(modelName => {
        return [
            modelName,
            modelsWrapper.hookModel(modelName)
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
