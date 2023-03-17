export class Dependency {
    modelName: string;
    fieldName: string;
    index?: number;
    subFieldName?: string;

    constructor(dependencyString: string) {
        let { modelName, fieldName, index, subFieldName } = this.mapDependencyNameToParts(dependencyString);
        this.modelName = modelName;
        this.fieldName = fieldName;
        this.index = index;
        this.subFieldName = subFieldName;
    }

    mapDependencyNameToParts: (dep: string) => { modelName: string, fieldName: string, index?: number, subFieldName?: string } = (dep) => {
        let [modelName, fieldName, index, subFieldName] = dep.split('.').filter((s: string) => s && s.length > 0);
        return {
            modelName,
            fieldName,
            index: parseInt(index),
            subFieldName
        }
    }

    getDependencyString: () => string = () => {
        return this.modelName + "." + this.fieldName + (this.index ? `@${this.index}` : '');
    }
}
