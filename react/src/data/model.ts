import { useDispatch, useSelector } from "react-redux";
import { Dispatch, AnyAction } from "redux";
import { ModelActions, ModelSelectors } from "../store/models";

export class ModelsWrapper {
    modelActions: ModelActions;
    modelSelectors: ModelSelectors;
    dispatch: Dispatch<AnyAction>;

    constructor({ modelActions, modelSelectors }: { modelActions: ModelActions, modelSelectors: ModelSelectors }) {
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

    saveToServer = (simulationInfo, state) => {
        let models = this.getModels(state);
        simulationInfo.models = models;
        fetch("/save-simulation", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(simulationInfo)
        }).then(resp => {
            // TODO: error handling
            console.log("resp", resp);
        })
    }
}
