import { useSelector, useDispatch, useStore } from 'react-redux';

let mapDependencyNameToParts = (dep) => {
    let [modelName, fieldName] = dep.split('.').filter(s => s && s.length > 0);
    return {
        modelName,
        fieldName
    }
}

export class DependencyCollector {
    constructor({ modelActions, modelSelectors, schema }) {
        this.models = {};
        this.modelActions = modelActions;
        this.modelSelectors = modelSelectors;
        this.schema = schema
    }

    getModel = (modelName) => {
        let selectFn = useSelector;
        let dispatchFn = useDispatch;
        let storeFn = useStore;

        let dispatch = dispatchFn();
        let store = storeFn();

        let { updateModel } = this.modelActions;
        let { selectModel } = this.modelSelectors;

        if (!(modelName in this.models)) {
            let model = {
                schema: this.schema.models[modelName],
                value: {...selectFn(selectModel(modelName))}, // TODO evaluate this clone, it feels like its needed to be safe
                updateValue: (v) => {
                    dispatch(updateModel({ name: modelName, value: v }));
                    model.value = {...selectModel(modelName)(store.getState())} // TODO this is janky
                }
            }
            this.models[modelName] = model;
        }

        return this.models[modelName];
    }

    hookModelDependency = (depString) => {
        let { modelName, fieldName } = mapDependencyNameToParts(depString);
    
        let model = this.getModel(modelName);
        let fieldSchema = model.schema[fieldName];

        return {
            modelName,
            fieldName,
            model,
            displayName: fieldSchema.name,
            type: fieldSchema.type,
            defaultValue: fieldSchema.defaultValue,
            description: fieldSchema.description,
            value: model.value[fieldName]
        }
    }
}
