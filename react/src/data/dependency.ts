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
