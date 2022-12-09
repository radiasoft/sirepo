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

        // expand wildcard
        this.dependencies = this.dependencies.flatMap(d => {
            if(d.fieldName === '*') {
                let fieldNames = Object.keys(this.modelValues[d.modelName]);
                return fieldNames.map(fn => new Dependency(`${d.modelName}.${fn}`));
            } else {
                return [d];
            }
        })
    }

    getFieldValue = (dependency: Dependency): F => {
        return this.modelsWrapper.getFieldFromModel(dependency.fieldName, this.modelValues[dependency.modelName]);
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
