import { ModelState } from "../store/models";
import { SchemaField, SchemaModel } from "../utility/schema";
import { ModelsWrapper, ModelWrapper } from "./model";

export class Dependency {
    modelName: string;
    fieldName: string;

    constructor(dependencyString: string) {
        let { modelName, fieldName } = this.mapDependencyNameToParts(dependencyString);
        this.modelName = modelName;
        this.fieldName = fieldName;
    }

    mapDependencyNameToParts: (dep: string) => { modelName: string, fieldName: string } = (dep) => {
        let [modelName, fieldName] = dep.split('.').filter((s: string) => s && s.length > 0);
        return {
            modelName,
            fieldName
        }
    }

    getDependencyString: () => string = () => {
        return this.modelName + "." + this.fieldName;
    }
}

export type HookedModel = { 
    schema: SchemaModel,
    value: ModelState
} & ModelWrapper

export type HookedDependency<T> = {
    modelName: string,
    fieldName: string,
    model: HookedModel,
    value: T
} & SchemaField<T>

export class HookedDependencyGroup {
    modelsWrapper: ModelsWrapper;
    dependencies: Dependency[];
    hookedModels: {[modelName: string]: HookedModel}
    hookedDependencies: HookedDependency<unknown>[]

    constructor({ dependencies, modelsWrapper, schemaModels }: { dependencies: Dependency[], modelsWrapper: ModelsWrapper, schemaModels: {[modelName: string]: SchemaModel}}) {
        this.modelsWrapper = modelsWrapper;
        this.dependencies = dependencies;

        let modelNames: string[] = [... new Set<string>(dependencies.map((dep: Dependency) => dep.modelName))];
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
