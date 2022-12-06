import { Dependency } from "./dependency";
import { AbstractModelsWrapper } from "./wrapper";

export class ModelsAccessor<M, F> {
    modelValues: {[key: string]: M};
    modelNames: string[];
    constructor(private modelsWrapper: AbstractModelsWrapper<M, F>, private dependencies: Dependency[]) {
        this.modelNames = [...new Set<string>(dependencies.map(d => d.modelName))];
        this.modelValues = Object.fromEntries(this.modelNames.map(modelName => {
            return [
                modelName,
                modelsWrapper.hookModel(modelName)
            ]
        }))
    }

    getFieldValue = (dependency: Dependency): F => {
        let m =  this.modelValues[dependency.modelName];
        return this.modelsWrapper.getFieldFromModel(dependency.fieldName, m);
    }

    getModelValue = (modelName: string): M => {
        return this.modelValues[modelName];
    }

    getValues = (): { dependency: Dependency, value: F }[] => {
        return this.dependencies.map(d => {
            return {
                dependency: d,
                value: this.getFieldValue(d)
            }
        })
    }

    getModelNames = (): string[] => {
        return this.modelNames;
    }
}
