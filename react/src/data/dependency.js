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

export class HookedDependencyGroup {
    constructor({ dependencies, modelsWrapper, schemaModels }) {
        this.modelsWrapper = modelsWrapper;
        this.dependencies = dependencies;

        let modelNames = [... new Set(dependencies.map(dep => dep.modelName))];
        this.hookedModels = Object.fromEntries(
            modelNames.map(modelName => {
                let model = this.modelsWrapper.forModel(modelName);
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
            if(!fieldName || !hookedModel || !hookedModel.schema) {
                debugger;
            }
            let fieldSchema = hookedModel.schema[fieldName];
            if(!fieldSchema) {
                throw new Error(`missing field schema for field "${fieldName}" in model "${modelName}"`)
            }
            // TODO needs abstraction
            //let { type, displayName, description, defaultValue, min, max, shown } = fieldSchema;
            return {
                modelName,
                fieldName,
                model: hookedModel,
                value: hookedModel.value[fieldName],
                ...fieldSchema
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
