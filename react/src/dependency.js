import { useSelector, useDispatch, useStore } from 'react-redux';

export class Dependency {
    constructor(dependencyString) {
        let { modelName, fieldName } = this.mapDependencyNameToParts(dependencyString);
        this.modelName = modelName;
        this.fieldName = fieldName;
    }

    mapDependencyNameToParts = (dep) => {
        let [modelName, fieldName] = dep.split('.').filter(s => s && s.length > 0);
        return {
            modelName,
            fieldName
        }
    }

    getDependencyString = () => {
        return this.modelName + "." + this.fieldName;
    }
}

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

export function useCompiledReplacementString(models, str) {
    let regexp = /\%([^\%]+)\%/g;
    let mappingsArr = str.matchAll(regexp).map(([originalString, mappedGroup]) => {
        let dependency = new Dependency(mappedGroup);
        return {
            original: originalString,
            dependency
        }
    });

    let modelNames = [...new Set(mappingsArr.map(mapping => mapping.modelName))];

    let modelValues = Object.fromEntries(modelNames.map(modelName => {
        return [
            modelName,
            models.hookModel(modelName)
        ]
    }));

    mappingsArr.map(mapping => {
        let { modelName, fieldName } = mapping.dependency; 
        return {
            ...mapping,
            value: modelValues[modelName][fieldName]
        }
    }).forEach(({ original, value }) => {
        str = str.replace(original, `${value}`);
    })

    return str;
}

export class Models {
    constructor({ modelActions, modelSelectors }) {
        this.modelActions = modelActions;
        this.modelSelectors = modelSelectors;


        let dispatchFn = useDispatch;
        this.dispatch = dispatchFn();
    }

    getModel = (modelName, state) => {
        return this.modelSelectors.selectModel(modelName)(state);
    }

    getModels = (state) => {
        return this.modelSelectors.selectModels(state);
    }

    getIsLoaded = (state) => {
        return this.modelSelectors.selectIsLoaded(state);
    }

    forModel = (modelName) => {
        return {
            updateModel: (value) => {
                return this.updateModel(modelName, value);
            },
            hookModel: () => {
                return this.hookModel(modelName);
            }
        }
    }

    updateModel = (modelName, value) => {
        console.log("dispatching update to ", modelName, " changing to value ", value);
        this.dispatch(this.modelActions.updateModel({
            name: modelName,
            value
        }))
    }

    hookModel = (modelName) => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectModel(modelName));
    }

    hookModels = () => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectModels);
    }

    hookIsLoaded = () => {
        let selectFn = useSelector;
        return selectFn(this.modelSelectors.selectIsLoaded);
    }
}

export class HookedDependencyGroup {
    constructor({ dependencies, models, schemaModels }) {
        this.models = models;
        this.dependencies = dependencies;

        let modelNames = [... new Set(dependencies.map(dep => dep.modelName))];
        this.hookedModels = Object.fromEntries(
            modelNames.map(modelName => {
                let model = this.models.forModel(modelName);
                let modelValue = model.hookModel();
                let modelSchema = schemaModels[modelName];
                return [modelName, {
                    ...model,
                    schema: modelSchema,
                    value: modelValue
                }]
            })
        );

        this.hookedDependencies = this.dependencies.map(dependency => {
            let { modelName, fieldName } = dependency;
            let hookedModel = this.hookedModels[modelName];
            let fieldSchema = hookedModel.schema[fieldName];
            if(!fieldSchema) {
                throw new Error(`missing field schema for field "${fieldName}" in model "${modelName}"`)
            }
            let { type, displayName, description, defaultValue } = fieldSchema;
            return {
                modelName,
                fieldName,
                model: hookedModel,
                displayName,
                type,
                description,
                defaultValue,
                value: hookedModel.value[fieldName]
            }
        })
    }

    getHookedDependency = (dependency) => {
        return this.hookedDependencies.find(hookedDependency => {
            return (dependency.modelName === hookedDependency.modelName &&
                dependency.fieldName === hookedDependency.fieldName);
        })
    }
}
